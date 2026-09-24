"""Seed of a run (train.py, make_seed.py): random for every run unless --seed
repeats one.

The seed is drawn from the operating system's cryptographic generator
(`secrets`), uniform over the ten-digit numbers [1e9, 1e10 - 1], and printed so
that --seed can repeat the run. It seeds torch (weights, DataLoader shuffling)
and Python's `random` (down-sampling, the validation split).
"""

import secrets

SEED_MIN, SEED_MAX = 10**9, 10**10 - 1


def resolve_seed(seed, tag):
    """`seed` as given with --seed, or a random one when None. Prints it."""
    if seed is None:
        seed = SEED_MIN + secrets.randbelow(SEED_MAX - SEED_MIN + 1)
        print(f"[{tag}] seed {seed} (random for this run; --seed {seed} repeats it)")
    else:
        if seed < 0:
            raise SystemExit(f"--seed must be >= 0, got {seed}")
        print(f"[{tag}] seed {seed} (--seed)")
    return seed
