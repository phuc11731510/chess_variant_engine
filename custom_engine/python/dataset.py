"""Dataset for FairyZero training: .gz training records -> (input, pi, value_wdl).

Applies the qMix value target (8.2.1): target = q_ratio*q_wdl + (1-q_ratio)*z_wdl,
and optional position down-sampling (8.2.3). For small datasets the dense tensors
are cached in RAM (fast epochs); for large-scale training use a streaming reader.
"""

import glob
import os
import random

import numpy as np
import torch
from torch.utils.data import Dataset

from trainingdata_reader import (read_records, read_records_from_zip,
                                 reconstruct_planes, POLICY_SIZE)


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


def _resolve_files(data):
    """`data` may be a comma-separated list of dirs, globs, and/or .zip bundles
    (the rolling window passes several generation dirs; a .zip is an archive.py
    transfer bundle that is read in place)."""
    files = []
    for part in str(data).split(","):
        part = part.strip()
        if not part:
            continue
        if os.path.isdir(part):
            for ext in ("*.gz", "*.bin", "*.zip"):
                files += glob.glob(os.path.join(part, ext))
        else:
            files += glob.glob(part)
    return sorted(set(files))


def _diff_focus_keep(rec, slope, kld_w, pmin):
    """diff_focus (8.2.6): keep prob rises with how 'surprising' a position is,
    measured by |orig_q - best_q| (search disagreed with the static net eval) and
    policy_kld (visit distribution diverged from the raw prior)."""
    surprise = abs(rec["orig_q"] - rec["best_q"]) + kld_w * max(0.0, rec["policy_kld"])
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

    def __init__(self, data, q_ratio=0.2, downsample_keep=1.0, cache=True, seed=0,
                 diff_focus=False, df_slope=1.0, df_kld_w=0.5, df_min=0.2, sparse=True,
                 max_records=0):
        rng = random.Random(seed)
        files = _resolve_files(data)
        if not files:
            raise FileNotFoundError(f"no training files matched: {data}")
        records = []
        for f in files:
            records.extend(read_records_from_zip(f) if f.endswith(".zip")
                           else read_records(f))
            if max_records and len(records) >= max_records:
                records = records[:max_records]
                break
        if downsample_keep < 1.0:
            records = [r for r in records if rng.random() < downsample_keep]
        if diff_focus:
            records = [r for r in records
                       if rng.random() < _diff_focus_keep(r, df_slope, df_kld_w, df_min)]
        if not records:
            raise ValueError("no records after down-sampling / diff_focus")

        self.q_ratio = q_ratio
        self.cache = cache
        self.sparse = sparse
        self._cached = None
        self._records = None
        if cache and sparse:
            # Compact each record, then DROP the raw dicts (and their dense 42KB
            # probabilities[10600]) so only the ~4KB compact form stays resident.
            self._cached = [self._compact(r) for r in records]
        elif cache:
            self._cached = [self._build(r) for r in records]
        else:
            self._records = records  # stream: rebuild on demand (keeps raw dicts).
        print(f"[dataset] {len(files)} files -> {len(records)} records "
              f"(q_ratio={q_ratio}, downsample={downsample_keep}, cached={cache}, "
              f"sparse={sparse and cache})")

    def _value(self, r):
        z_wdl = wdl_from_qd(r["result_q"], r["result_d"])
        q_wdl = wdl_from_qd(r["best_q"], r["best_d"])
        v = self.q_ratio * q_wdl + (1.0 - self.q_ratio) * z_wdl
        return v.astype(np.float32)

    def _build(self, r):
        """Dense tensors (used by sparse=False cache and by streaming)."""
        x = torch.from_numpy(reconstruct_planes(r))                       # [226,10,10] f32
        pi = torch.from_numpy(np.ascontiguousarray(r["probabilities"], dtype=np.float32))
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
            "piece_planes": np.asarray(r["piece_planes"], dtype=np.uint64),
            "ep_mask": np.asarray(r["ep_mask"], dtype=np.uint64),
            "castling_us_ooo_file": r["castling_us_ooo_file"],
            "castling_us_oo_file": r["castling_us_oo_file"],
            "castling_them_ooo_file": r["castling_them_ooo_file"],
            "castling_them_oo_file": r["castling_them_oo_file"],
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
            return self._build_from_compact(self._cached[i]) if self.sparse else self._cached[i]
        return self._build(self._records[i])
