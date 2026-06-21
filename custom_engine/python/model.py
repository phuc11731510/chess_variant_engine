"""FairyZero network — lc0-style SE-ResNet 10x128 for the 10x10 variant.

Architecture faithful to lc0 (lczero-training tfprocess.py):
  - stem: conv 226->128 (3x3, no bias) + BN + ReLU
  - 10 residual blocks: conv-BN-ReLU -> conv-BN -> SE -> +skip -> ReLU
  - SE block (scale + bias, lc0 hallmark):
        GAP -> FC(c/ratio) + ReLU -> FC(2c) -> split(gamma, beta)
        out = sigmoid(gamma) * x + beta
  - policy head: conv 1x1 to 106 type-planes -> flatten = type*100+rank*10+file = MoveToNNIndex
  - value head : conv 1x1 -> FC -> FC(3) WDL logits

I/O contract (matches C++ OnnxComputation):
  input  [batch,226,10,10] "input"
  policy [batch,10600]     "policy"  -> raw logits (engine softmaxes legal moves)
  value  [batch,3]         "value"   -> WDL probs (softmax added by ExportNet)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

NUM_PLANES = 226
POLICY_SIZE = 10600
POLICY_TYPES = 106          # 106 * 100 (squares) = 10600
BOARD = 10


class SqueezeExcitation(nn.Module):
    """lc0-style SE: out = sigmoid(gamma) * x + beta  (scale AND bias)."""

    def __init__(self, channels, ratio=8):
        super().__init__()
        assert channels % ratio == 0
        self.channels = channels
        self.fc1 = nn.Linear(channels, channels // ratio)
        self.fc2 = nn.Linear(channels // ratio, 2 * channels)

    def forward(self, x):
        b, c, _, _ = x.shape
        pooled = x.mean(dim=(2, 3))             # global average pool -> [b,c]
        s = F.relu(self.fc1(pooled))
        s = self.fc2(s)                         # [b, 2c]
        gamma = torch.sigmoid(s[:, :c]).view(b, c, 1, 1)
        beta = s[:, c:].view(b, c, 1, 1)
        return gamma * x + beta


class ResidualBlock(nn.Module):
    def __init__(self, c, se_ratio=8):
        super().__init__()
        self.conv1 = nn.Conv2d(c, c, 3, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(c)
        self.conv2 = nn.Conv2d(c, c, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(c)
        self.se = SqueezeExcitation(c, se_ratio)

    def forward(self, x):
        h = F.relu(self.bn1(self.conv1(x)))
        h = self.bn2(self.conv2(h))
        h = self.se(h)
        return F.relu(x + h)


class FairyNet(nn.Module):
    """forward returns (policy_logits[B,10600], value_logits[B,3])."""

    def __init__(self, channels=128, blocks=10, se_ratio=8, dropout=0.0):
        super().__init__()
        self.dropout_p = dropout   # functional dropout (no params) -> warm-start safe
        self.stem_conv = nn.Conv2d(NUM_PLANES, channels, 3, padding=1, bias=False)
        self.stem_bn = nn.BatchNorm2d(channels)
        self.tower = nn.Sequential(*[ResidualBlock(channels, se_ratio) for _ in range(blocks)])

        # Policy head: 3x3 conv -> 1x1 conv to 106 type-planes.
        self.pol_conv = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
        self.pol_bn = nn.BatchNorm2d(channels)
        self.pol_head = nn.Conv2d(channels, POLICY_TYPES, 1)  # [B,106,10,10]

        # Value head: 1x1 conv -> FC -> FC(3) logits.
        self.val_conv = nn.Conv2d(channels, 32, 1, bias=False)
        self.val_bn = nn.BatchNorm2d(32)
        self.val_fc1 = nn.Linear(32 * BOARD * BOARD, 128)
        self.val_fc2 = nn.Linear(128, 3)

    def forward(self, x):
        h = F.relu(self.stem_bn(self.stem_conv(x)))
        h = self.tower(h)

        p = F.relu(self.pol_bn(self.pol_conv(h)))
        p = self.pol_head(p)                  # [B,106,10,10]
        policy = p.flatten(1)                 # [B,10600] = type*100 + rank*10 + file

        v = F.relu(self.val_bn(self.val_conv(h)))
        v = v.flatten(1)
        v = F.relu(self.val_fc1(v))
        if self.dropout_p > 0:
            v = F.dropout(v, self.dropout_p, self.training)
        value = self.val_fc2(v)               # [B,3] logits (W,D,L)
        return policy, value


class ExportNet(nn.Module):
    """Export wrapper: policy stays raw logits; value gets in-graph softmax (WDL)."""

    def __init__(self, net):
        super().__init__()
        self.net = net

    def forward(self, x):
        policy, value = self.net(x)
        return policy, torch.softmax(value, dim=1)
