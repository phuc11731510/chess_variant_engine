"""Dataset for FairyZero training: .gz training records -> (input, pi, value_wdl).

Applies the qMix value target (8.2.1): target = q_ratio*q_wdl + (1-q_ratio)*z_wdl,
and optional position down-sampling (8.2.3). For small datasets the dense tensors
are cached in RAM (fast epochs); for large-scale training use a streaming reader.
"""

import glob
import os
import random
import time
import zipfile

import numpy as np
import torch
from torch.utils.data import Dataset

from trainingdata_reader import (is_game_member, iter_games, reconstruct_planes,
                                 AUX_BASE, BOARD, CASTLING_KEYS, HISTORY_PLANES,
                                 NO_CASTLING_SQ, NUM_PLANES, POLICY_SIZE)


def wdl_from_qd(q, d):
    """(q = win - loss, d = draw) -> normalized [W, D, L] distribution."""
    w = (q + 1.0 - d) / 2.0
    l = (1.0 - d - q) / 2.0
    w = min(1.0, max(0.0, w))
    l = min(1.0, max(0.0, l))
    d = min(1.0, max(0.0, d))
    s = w + d + l
    if s <= 1e-8:
        return np.array([0.0, 1.0, 0.0], dtype=np.float32)
    return np.array([w / s, d / s, l / s], dtype=np.float32)


# Records before training-data version 2 stored the search values root_q /
# best_q / played_q from the OPPONENT's perspective (sign error in the C++
# FillSearchTargets, fixed 2026-09-23; result_q was always right). From version 2
# on every value is side-to-move. search_q() / orig_q() below return the
# side-to-move value for either version, so old and new data can be mixed.
# Version 3 (same layout and signs) marks data from the engine that detects
# repetitions at every rule-50 count; versions 1-2 missed most of them
# (trainingdata_v1.h). Nothing to convert, so it is read like version 2.
# Version 4 has an exact raw eval in every record (see orig_is_unknown below).
FIRST_STM_SEARCH_Q_VERSION = 2


def _is_legacy(rec):
    # Synthetic records built in tests carry no "version": treat as current.
    return rec.get("version", FIRST_STM_SEARCH_Q_VERSION) < FIRST_STM_SEARCH_Q_VERSION


def search_q(rec, key="best_q"):
    """Search value `key` (root_q / best_q / played_q), side-to-move perspective."""
    q = rec[key]
    return -q if _is_legacy(rec) else q


def orig_q(rec):
    """Raw net value of the root, side-to-move perspective. In version-1 records
    it was already correct, except where the cache missed and the writer copied
    the (sign-flipped) best_q into it -- recognizable as an exact copy."""
    q = rec["orig_q"]
    if _is_legacy(rec) and q == rec["best_q"] and rec["orig_d"] == rec["best_d"]:
        return -q
    return q


def _resolve_files(data):
    """`data` may be a comma-separated list of dirs, globs, and/or .zip bundles
    (the rolling window passes several generation dirs; a .zip is an archive.py
    transfer bundle that is read in place).

    Every part must match at least one file. A part that matched nothing used to
    be skipped without a word, so a typo in one generation of the window
    ("gen1.zip, gen2.zpi") trained on the others only."""
    files, empty = [], []
    for part in str(data).split(","):
        part = part.strip()
        if not part:
            continue
        found = []
        if os.path.isdir(part):
            for ext in ("*.gz", "*.bin", "*.zip"):
                found += glob.glob(os.path.join(part, ext))
        else:
            found = glob.glob(part)
        if not found:
            empty.append(part)
        files += found
    if empty:
        raise FileNotFoundError("no training files matched: " + ", ".join(repr(p) for p in empty))
    return sorted(set(files))


def list_games(data):
    """Every game in `data` (see _resolve_files), in load order: (path, None) for
    a .gz/.bin file -- self-play writes one game per file -- and (zip, member) for
    each game inside a .zip bundle, in the bundle's order."""
    games = []
    for f in _resolve_files(data):
        if f.endswith(".zip"):
            with zipfile.ZipFile(f) as zf:
                games += [(f, name) for name in zf.namelist() if is_game_member(name)]
        else:
            games.append((f, None))
    return games


def game_mtimes(games):
    """Modification time (seconds) of every game of list_games: the file's, or the
    one a .zip keeps for the member (2 s resolution). Renaming a file keeps it."""
    out, stamps = [], {}
    for path, member in games:
        if member is None:
            out.append(os.path.getmtime(path))
            continue
        if path not in stamps:
            with zipfile.ZipFile(path) as zf:
                stamps[path] = {i.filename: time.mktime(i.date_time + (0, 0, -1)) for i in zf.infolist()}
        out.append(stamps[path][member])
    return out


def split_games(games, val_frac, mtimes):
    """Hold out the round(val_frac * #games) NEWEST games (by modification time,
    ties by load order) as a validation set: the latest self-play, which the
    net being warm-started from never trained on (older games in the window it
    did). No shuffling here; the training games are shuffled by the DataLoader.

    Whole games, not positions: the positions of one game share its result z and
    look alike, so with a game on both sides a net that memorized it would look
    good on validation too. Returns (train_games, val_games), each in load order;
    val_games is empty when val_frac * #games rounds to 0."""
    n_val = int(round(val_frac * len(games))) if val_frac > 0 else 0
    if n_val <= 0:
        return list(games), []
    if n_val >= len(games):
        raise ValueError(f"--val-frac {val_frac} would hold out all {len(games)} games")
    order = sorted(range(len(games)), key=lambda i: (mtimes[i], i))
    held = set(order[len(games) - n_val:])
    return ([g for i, g in enumerate(games) if i not in held],
            [g for i, g in enumerate(games) if i in held])


# From data version 4 orig_q/orig_d/policy_kld are always the root's real raw
# NN eval. Before, when the root had already fallen out of the NN cache (8.5% of
# the gen-0 records), the engine wrote orig = best and policy_kld = 0 instead.
FIRST_EXACT_ORIG_VERSION = 4


def orig_is_unknown(rec):
    """True for a pre-version-4 record whose raw-eval fields are that copy."""
    return (rec.get("version", FIRST_EXACT_ORIG_VERSION) < FIRST_EXACT_ORIG_VERSION
            and rec["policy_kld"] == 0.0 and rec["orig_q"] == rec["best_q"]
            and rec["orig_d"] == rec["best_d"])


def _diff_focus_keep(rec, slope, kld_w, pmin):
    """diff_focus (8.2.6): keep prob rises with how 'surprising' a position is,
    measured by |orig_q - best_q| (search disagreed with the static net eval) and
    policy_kld (visit distribution diverged from the raw prior)."""
    surprise = abs(orig_q(rec) - search_q(rec)) + kld_w * max(0.0, rec["policy_kld"])
    return min(1.0, max(pmin, pmin + slope * surprise))


class FairyDataset(Dataset):
    """Yields (input[226,10,10], pi[10600], value[3]).

    Two in-RAM cache representations (both produce identical training tensors):
      * sparse=True  (default, 8.2.2): per record keep only the compact bitboard
        words (~3.5KB), scalars, and the LEGAL policy entries as (idx, val) pairs
        (~0.6-0.9KB). Dense [226,10,10] planes and the dense [10600] policy are
        rebuilt lazily in __getitem__. ~4KB/record -> a 100k buffer fits in ~400MB,
        avoiding the Colab OOM the dense path would hit (~13GB).
      * sparse=False: cache the fully-dense tensors (faster per-item, much more RAM).
    """

    packed = False   # test subclasses skip __init__

    def __init__(self, data, q_ratio=0.2, downsample_keep=1.0, cache=True, seed=0,
                 diff_focus=False, df_slope=1.0, df_kld_w=0.5, df_min=0.2, sparse=True,
                 max_records=0, games=None, label="", packed=False):
        """`games` (from list_games / split_games) loads only those games; by
        default every game in `data`. `label` names the set in the log line.
        `packed` (sparse cache only): items are pack_compact() samples, to batch
        with collate_packed and rebuild on the device with unpack_batch."""
        rng = random.Random(seed)
        games = list_games(data) if games is None else list(games)
        if not games:
            raise FileNotFoundError(f"no training games in: {data}")

        self.q_ratio = q_ratio   # set before _compact/_build (they call self._value)
        self.cache = cache
        self.sparse = sparse
        self.packed = packed and cache and sparse
        self._cached = None
        self._records = None

        # Stream records one at a time and, for the default sparse cache, compact
        # each immediately — the raw dict (with its dense 42KB probabilities[10600])
        # is freed right away instead of accumulating. Peak RAM ~= compact form
        # (~4KB/rec) rather than raw (~45KB/rec). The old eager path materialized
        # EVERY raw record before compacting, which exhausted Colab's RAM at load
        # time (before the first training step) on a few-thousand-game dataset.
        compact_cache = [] if (cache and sparse) else None
        dense_cache = [] if (cache and not sparse) else None
        raw_records = [] if not cache else None

        # diff_focus on a record without a raw eval (orig_is_unknown): its surprise
        # is unknown, not zero -- read as zero it was kept with the minimum
        # probability like the dullest position. Such records are set aside and
        # kept at the end with the AVERAGE keep rate of all the other records,
        # which leaves the mix unbiased whatever order the files come in.
        df_seen = [0.0, 0]
        deferred = []

        def _keep(r):
            """True / False, or None for 'decide at the end' (unknown surprise)."""
            if downsample_keep < 1.0 and rng.random() >= downsample_keep:
                return False
            if diff_focus:
                if orig_is_unknown(r):
                    return None
                keep_p = _diff_focus_keep(r, df_slope, df_kld_w, df_min)
                df_seen[0] += keep_p
                df_seen[1] += 1
                if rng.random() >= keep_p:
                    return False
            return True

        def _form(r):
            if compact_cache is not None:
                return self._compact(r)
            if dense_cache is not None:
                return self._build(r)
            # cache=False keeps the raw dict (51 KB) -- far MORE RAM than the
            # sparse cache (4.8 KB). Debug only; see train.py --no-cache.
            return r

        store = compact_cache if compact_cache is not None else (
            dense_cache if dense_cache is not None else raw_records)
        kept = 0
        records = iter_games(games)
        for r in records:
            k = _keep(r)
            if k is False:
                continue
            if k is None:
                deferred.append(_form(r))
                continue
            store.append(_form(r))
            kept += 1
            if max_records and kept >= max_records:
                break
        records.close()                        # closes an open .zip at once
        if deferred:
            keep_p = df_seen[0] / df_seen[1] if df_seen[1] else 1.0
            for form in deferred:
                if max_records and kept >= max_records:
                    break
                if rng.random() < keep_p:
                    store.append(form)
                    kept += 1
            print(f"[dataset] diff_focus: {len(deferred)} records without a raw eval (data < v4) "
                  f"kept at the average rate {keep_p:.3f}")
        if kept == 0:
            raise ValueError("no records after down-sampling / diff_focus")

        self._cached = compact_cache if compact_cache is not None else dense_cache
        self._records = raw_records
        self.num_games = len(games)
        print(f"[dataset] {label + ': ' if label else ''}{len(games)} games -> {kept} records "
              f"(q_ratio={q_ratio}, downsample={downsample_keep}, cached={cache}, "
              f"sparse={sparse and cache})")

    def _value(self, r):
        z_wdl = wdl_from_qd(r["result_q"], r["result_d"])
        q_wdl = wdl_from_qd(search_q(r), r["best_d"])
        v = self.q_ratio * q_wdl + (1.0 - self.q_ratio) * z_wdl
        return v.astype(np.float32)

    def _build(self, r):
        """Dense tensors (used by sparse=False cache and by streaming)."""
        x = torch.from_numpy(reconstruct_planes(r))                       # [226,10,10] f32
        pi = torch.from_numpy(np.array(r["probabilities"], dtype=np.float32))  # own copy:
        # the reader's array is a read-only view into the record buffer
        value = torch.from_numpy(self._value(r))                          # [3]
        return x, pi, value

    def _compact(self, r):
        """Memory-thin form: bitboard words + scalars + sparse legal policy.

        Policy convention preserved exactly: illegal = -1, legal = (0 or fraction).
        We store only legal slots (pi >= 0, i.e. pi > -0.5) as (uint16 idx, f32 val);
        __getitem__ refills a -1 dense vector and writes them back."""
        pi = r["probabilities"]
        legal = np.nonzero(pi > -0.5)[0].astype(np.uint16)
        return {
            "piece_planes": np.asarray(r["piece_planes"], dtype=np.uint64),  # no copy (reader)
            "ep_mask": np.asarray(r["ep_mask"], dtype=np.uint64),
            "castling_us_ooo_sq": r["castling_us_ooo_sq"],
            "castling_us_oo_sq": r["castling_us_oo_sq"],
            "castling_them_ooo_sq": r["castling_them_ooo_sq"],
            "castling_them_oo_sq": r["castling_them_oo_sq"],
            "rule50_count": r["rule50_count"],
            "checks_remaining_us": r["checks_remaining_us"],
            "checks_remaining_them": r["checks_remaining_them"],
            "pi_idx": legal,
            "pi_val": pi[legal].astype(np.float32),
            "value": self._value(r),
        }

    def _build_from_compact(self, c):
        x = torch.from_numpy(reconstruct_planes(c))                       # planes rebuilt
        pi = np.full(POLICY_SIZE, -1.0, dtype=np.float32)                 # all illegal...
        pi[c["pi_idx"]] = c["pi_val"]                                     # ...then legal slots
        return x, torch.from_numpy(pi), torch.from_numpy(c["value"])

    def __len__(self):
        return len(self._cached) if self._cached is not None else len(self._records)

    def __getitem__(self, i):
        if self._cached is not None:
            if self.sparse:
                c = self._cached[i]
                return pack_compact(c) if self.packed else self._build_from_compact(c)
            return self._cached[i]
        return self._build(self._records[i])


# --------------------------------------------------------------------------- #
# Packed samples (train.py, sparse cache): the DataLoader workers hand over the
# bitboards and the legal policy slots only (~4 KB/position instead of 132 KB of
# dense float planes + policy), and unpack_batch() rebuilds the dense tensors of
# the whole batch on the training device (GPU). On Colab's 2 vCPUs the workers
# building dense planes competed with the process driving the GPU (T4: 405 ms per
# step vs 351 ms of GPU work). The tensors are bit-identical to __getitem__ with
# packed=False (test_extreme.py 11 checks every plane and policy slot).
# --------------------------------------------------------------------------- #
N_MASKS = HISTORY_PLANES + 5           # 216 history + 4 castling (aux 0-3) + e.p. (aux 4)

# Castling right on square s (rank*10+file) -> the 128-bit mask (lo, hi) with bit
# rank*12+file set, as the reader's planes; row 100 = NO_CASTLING_SQ (no bit).
_CASTLE_MASK = np.zeros((BOARD * BOARD + 1, 2), dtype=np.uint64)
for _s in range(BOARD * BOARD):
    _b = (_s // BOARD) * 12 + _s % BOARD
    _CASTLE_MASK[_s, _b // 64] = np.uint64(1) << np.uint64(_b % 64)


def _castle_row(sq):
    return BOARD * BOARD if sq == NO_CASTLING_SQ else sq


def pack_compact(c):
    """One compact record -> (masks int64[221,2], scalars f32[3], pi_idx, pi_val, value).
    The scalars are computed exactly as reconstruct_planes does (float64 division
    rounded to float32), so the planes rebuilt from them are bit-identical."""
    masks = np.empty((N_MASKS, 2), dtype=np.uint64)
    masks[:HISTORY_PLANES] = np.asarray(c["piece_planes"], dtype=np.uint64).reshape(HISTORY_PLANES, 2)
    masks[HISTORY_PLANES:HISTORY_PLANES + 4] = _CASTLE_MASK[[_castle_row(c[k]) for k in CASTLING_KEYS]]
    masks[HISTORY_PLANES + 4] = np.asarray(c["ep_mask"], dtype=np.uint64)
    scal = np.array([c["rule50_count"] / 100.0, c["checks_remaining_us"] / 10.0,
                     c["checks_remaining_them"] / 10.0], dtype=np.float32)
    return masks.view(np.int64), scal, c["pi_idx"], c["pi_val"], c["value"]


def collate_packed(items):
    """DataLoader collate_fn for packed samples: stack, pad the legal policy slots
    to the batch's longest list with index POLICY_SIZE (a spare column that
    unpack_batch drops) and value 0."""
    masks = torch.from_numpy(np.stack([it[0] for it in items]))
    scal = torch.from_numpy(np.stack([it[1] for it in items]))
    value = torch.from_numpy(np.stack([it[4] for it in items]))
    n = max(len(it[2]) for it in items)
    idx = np.full((len(items), n), POLICY_SIZE, dtype=np.int64)
    val = np.zeros((len(items), n), dtype=np.float32)
    for b, it in enumerate(items):
        k = len(it[2])
        idx[b, :k] = it[2]
        val[b, :k] = it[3]
    return masks, scal, torch.from_numpy(idx), torch.from_numpy(val), value


_WORD_T = torch.from_numpy(
    ((np.arange(BOARD)[:, None] * 12 + np.arange(BOARD)[None, :]) // 64).astype(np.int64))
_BIT_T = torch.from_numpy(
    ((np.arange(BOARD)[:, None] * 12 + np.arange(BOARD)[None, :]) % 64).astype(np.int64))


def unpack_batch(batch, device, channels_last=False):
    """collate_packed batch -> (x f32[B,226,10,10], pi f32[B,10600], value f32[B,3])
    on `device`; x in channels_last memory format when asked (same values)."""
    masks, scal, idx, val, value = (t.to(device, non_blocking=True) for t in batch)
    b = masks.size(0)
    word, bit = _WORD_T.to(device), _BIT_T.to(device)
    fmt = torch.channels_last if channels_last else torch.contiguous_format
    x = torch.empty((b, NUM_PLANES, BOARD, BOARD), dtype=torch.float32, device=device,
                    memory_format=fmt)
    # masks[:, :, word] -> [B,221,10,10] = the word holding each cell's bit; the
    # arithmetic shift of a negative int64 is harmless: only bit 0 is kept.
    x[:, :N_MASKS] = torch.bitwise_and(torch.bitwise_right_shift(masks[:, :, word], bit), 1)
    x[:, AUX_BASE + 5] = scal[:, 0, None, None]          # rule50 / 100
    x[:, AUX_BASE + 6] = 0.0                              # unused
    x[:, AUX_BASE + 7] = 1.0                              # board edge
    x[:, AUX_BASE + 8] = scal[:, 1, None, None]          # checks us / 10
    x[:, AUX_BASE + 9] = scal[:, 2, None, None]          # checks them / 10
    pi = torch.full((b, POLICY_SIZE + 1), -1.0, dtype=torch.float32, device=device)
    pi.scatter_(1, idx, val)
    return x, pi[:, :POLICY_SIZE], value
