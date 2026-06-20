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

from trainingdata_reader import read_records, reconstruct_planes


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
    if os.path.isdir(data):
        return sorted(glob.glob(os.path.join(data, "*.gz")) +
                      glob.glob(os.path.join(data, "*.bin")))
    return sorted(glob.glob(data))


class FairyDataset(Dataset):
    def __init__(self, data, q_ratio=0.2, downsample_keep=1.0, cache=True, seed=0):
        rng = random.Random(seed)
        files = _resolve_files(data)
        if not files:
            raise FileNotFoundError(f"no training files matched: {data}")
        records = []
        for f in files:
            records.extend(read_records(f))
        if downsample_keep < 1.0:
            records = [r for r in records if rng.random() < downsample_keep]
        if not records:
            raise ValueError("no records after down-sampling")

        self.q_ratio = q_ratio
        self.cache = cache
        self._records = records
        self._cached = None
        if cache:
            self._cached = [self._build(r) for r in records]
        print(f"[dataset] {len(files)} files -> {len(records)} records "
              f"(q_ratio={q_ratio}, downsample={downsample_keep}, cached={cache})")

    def _build(self, r):
        x = torch.from_numpy(reconstruct_planes(r))                       # [226,10,10] f32
        pi = torch.from_numpy(np.ascontiguousarray(r["probabilities"], dtype=np.float32))
        z_wdl = wdl_from_qd(r["result_q"], r["result_d"])
        q_wdl = wdl_from_qd(r["best_q"], r["best_d"])
        v = self.q_ratio * q_wdl + (1.0 - self.q_ratio) * z_wdl
        value = torch.from_numpy(v.astype(np.float32))                    # [3]
        return x, pi, value

    def __len__(self):
        return len(self._records)

    def __getitem__(self, i):
        if self.cache:
            return self._cached[i]
        return self._build(self._records[i])
