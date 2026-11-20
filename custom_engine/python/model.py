"""FairyZero network -- a transformer over the 100 squares of the 10x10 board, with three heads.

  input   [batch, 204, 10, 10]  "input"   (the planes of nn_layout.py; token = square, rank * 10 + file)
  policy  [batch, 11500]        "policy"  raw logits, index = type * 100 + from square (= MoveToNNIndex)
  value   [batch, 3]            "value"   WDL probabilities (the softmax is added by ExportNet)
  mlh     [batch, 1]            "mlh"     moves left, in plies (linear; lc0 clamps it at 0 where it is used)

Body (pre-LayerNorm, FP32):
  tokens   [B, 100, 204] -> Linear -> d_model, plus a learned embedding of the square
  layers x [ x += MHA(LN(x)) ;  x += FFN(LN(x)) ]    heads of d_model / heads dimensions, FFN d_model -> 4 d_model -> d_model
  MHA adds to each head's attention scores a learned bias that depends only on the RELATIVE offset
  (rank difference, file difference) of the two squares: a 19 x 19 table per head.
  final LayerNorm
Heads (all read the final tokens):
  policy: every token -> Linear(d_model, 115 move types); [B,100,115] -> [B,115,100] -> flatten
  value : every token -> Linear(d_model, 32) -> flatten 3200 -> FC 128 -> FC 3
  mlh   : every token -> Linear(d_model, 8)  -> flatten 800  -> FC 128 -> FC 1

Attention is written with MatMul / Softmax (not scaled_dot_product_attention) so the exported graph is plain
and predictable for ONNX Runtime. See the Walkthrough (2026-11-20) and the plan, section 3.4 and 3.7.
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from nn_layout import BOARD, MOVE_TYPES as POLICY_TYPES, NUM_PLANES, POLICY_SIZE, SQUARES  # noqa: E402,F401

VALUE_TOKEN_DIM = 32     # per-token features the value head keeps (flattened: 32 * 100)
MLH_TOKEN_DIM = 8        # same for the moves-left head
HEAD_HIDDEN = 128
MLH_BIAS_INIT = 50.0     # the moves-left output starts near a typical number of plies left, not at 0


def _relative_index():
    """[100, 100] int64: for the pair (query square i, key square j) the row of the 19 x 19 table that holds
    the bias for the offset (rank_j - rank_i, file_j - file_i)."""
    r = torch.arange(SQUARES) // BOARD
    f = torch.arange(SQUARES) % BOARD
    dr = r[None, :] - r[:, None] + (BOARD - 1)
    df = f[None, :] - f[:, None] + (BOARD - 1)
    return dr * (2 * BOARD - 1) + df


class RelativeAttention(nn.Module):
    """Multi-head self-attention with a learned per-head bias on the relative offset of two squares."""

    def __init__(self, d_model, heads):
        super().__init__()
        assert d_model % heads == 0, "d_model must be a multiple of heads"
        self.heads = heads
        self.dh = d_model // heads
        self.scale = 1.0 / math.sqrt(self.dh)
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.proj = nn.Linear(d_model, d_model)
        self.rel_bias = nn.Parameter(torch.zeros(heads, (2 * BOARD - 1) ** 2))
        self.register_buffer("rel_index", _relative_index(), persistent=False)

    def forward(self, x):
        b, t, d = x.shape
        qkv = self.qkv(x).reshape(b, t, 3, self.heads, self.dh).permute(2, 0, 3, 1, 4)   # [3,B,H,T,dh]
        q, k, v = qkv[0], qkv[1], qkv[2]
        bias = self.rel_bias[:, self.rel_index]                                          # [H,T,T]
        # The 1 / sqrt(dh) goes on q BEFORE the product (as in scaled_dot_product_attention): the same numbers in
        # exact arithmetic, but the raw q.k sums stay small enough not to overflow in FP16 (max 65504), and the
        # multiplication touches [B,H,T,dh] instead of [B,H,T,T].
        att = torch.matmul(q * self.scale, k.transpose(-2, -1)) + bias.unsqueeze(0)      # [B,H,T,T]
        att = torch.softmax(att, dim=-1)
        out = torch.matmul(att, v).transpose(1, 2).reshape(b, t, d)                     # [B,T,d]
        return self.proj(out)


class Block(nn.Module):
    def __init__(self, d_model, heads, ffn_mult):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = RelativeAttention(d_model, heads)
        self.ln2 = nn.LayerNorm(d_model)
        self.ff1 = nn.Linear(d_model, ffn_mult * d_model)
        self.ff2 = nn.Linear(ffn_mult * d_model, d_model)

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        return x + self.ff2(F.gelu(self.ff1(self.ln2(x))))


class FairyNet(nn.Module):
    """forward returns (policy_logits[B,POLICY_SIZE], value_logits[B,3], mlh[B,1])."""

    def __init__(self, d_model=192, layers=10, heads=6, ffn_mult=4, dropout=0.0):
        super().__init__()
        self.dropout_p = dropout   # functional dropout (no params) -> warm-start safe
        self.embed = nn.Linear(NUM_PLANES, d_model)
        self.pos_embed = nn.Parameter(torch.zeros(1, SQUARES, d_model))
        self.blocks = nn.ModuleList([Block(d_model, heads, ffn_mult) for _ in range(layers)])
        self.final_ln = nn.LayerNorm(d_model)

        self.pol_head = nn.Linear(d_model, POLICY_TYPES)
        self.val_proj = nn.Linear(d_model, VALUE_TOKEN_DIM)
        self.val_fc1 = nn.Linear(VALUE_TOKEN_DIM * SQUARES, HEAD_HIDDEN)
        self.val_fc2 = nn.Linear(HEAD_HIDDEN, 3)
        self.mlh_proj = nn.Linear(d_model, MLH_TOKEN_DIM)
        self.mlh_fc1 = nn.Linear(MLH_TOKEN_DIM * SQUARES, HEAD_HIDDEN)
        self.mlh_fc2 = nn.Linear(HEAD_HIDDEN, 1)
        self._init_weights(layers)

    def _init_weights(self, layers):
        # GPT-style: weights N(0, 0.02), biases 0; the two matrices that write into the residual stream of every
        # block (attention output, FFN output) are scaled by 1 / sqrt(2 * layers) so the stream does not grow
        # with depth.
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, std=0.02)
                nn.init.zeros_(m.bias)
        residual_std = 0.02 / math.sqrt(2 * layers)
        for blk in self.blocks:
            nn.init.normal_(blk.attn.proj.weight, std=residual_std)
            nn.init.normal_(blk.ff2.weight, std=residual_std)
        nn.init.normal_(self.pos_embed, std=0.02)
        nn.init.constant_(self.mlh_fc2.bias, MLH_BIAS_INIT)

    def forward(self, x):
        b = x.shape[0]
        h = x.flatten(2).transpose(1, 2)                         # [B,100,204]: token = square = rank * 10 + file
        h = self.embed(h) + self.pos_embed
        for blk in self.blocks:
            h = blk(h)
        h = self.final_ln(h)

        policy = self.pol_head(h).transpose(1, 2).reshape(b, POLICY_SIZE)   # [B,115,100] -> type * 100 + square

        v = F.gelu(self.val_proj(h)).reshape(b, VALUE_TOKEN_DIM * SQUARES)
        v = F.gelu(self.val_fc1(v))
        if self.dropout_p > 0:
            v = F.dropout(v, self.dropout_p, self.training)
        value = self.val_fc2(v)                                  # [B,3] logits (W,D,L)

        m = F.gelu(self.mlh_proj(h)).reshape(b, MLH_TOKEN_DIM * SQUARES)
        m = F.gelu(self.mlh_fc1(m))
        mlh = self.mlh_fc2(m)                                    # [B,1] plies, linear
        return policy, value, mlh


class ExportNet(nn.Module):
    """Export wrapper: policy stays raw logits; value gets in-graph softmax (WDL); mlh is the plain number."""

    def __init__(self, net):
        super().__init__()
        self.net = net

    def forward(self, x):
        policy, value, mlh = self.net(x)
        return policy, torch.softmax(value, dim=1), mlh
