"""Dataset for FairyZero training: game files (.xz v6, .gz, .bin) -> (input, pi, value_wdl).

Value target: by default the qMix (8.2.1), target = q_ratio*q_wdl + (1-q_ratio)*z_wdl; with td_lambda the
mix of the game result and a TD(lambda) return over the later search values of the game (td_value_targets).
Optional position down-sampling (8.2.3). For small datasets the dense tensors are cached in RAM (fast
epochs); for large-scale training use a streaming reader. mirror_batch flips a batch left-right (the rules
have no castling, so a position and its a<->j mirror image are equivalent).
"""

import glob
import os
import random
import re
import time
import zipfile

import numpy as np
import torch
from torch.utils.data import Dataset

from nn_layout import (AUX_BASE, AUX_CHECKS_THEM, AUX_CHECKS_US, AUX_EN_PASSANT, AUX_RULE50, BOARD, CAMEL_BASE,
                       HISTORY_PLANES, KNIGHT_BASE, MOVE_TYPES, NUM_PLANES, POLICY_SIZE, PROMOTION_BASE,
                       PROMOTION_DIRECTIONS, SLIDE_TYPES, SQUARES)
from trainingdata_reader import is_game_member, iter_games, iter_games_grouped, reconstruct_planes


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


def wdl_from_qd_many(q, d):
    """wdl_from_qd for arrays: (q[N], d[N]) -> [N, 3] float64, the same clamping and normalization (a row with
    nothing left after clamping is a draw)."""
    q = np.asarray(q, dtype=np.float64)
    d = np.clip(np.asarray(d, dtype=np.float64), 0.0, 1.0)
    w = np.clip((q + 1.0 - d) / 2.0, 0.0, 1.0)
    l = np.clip((1.0 - d - q) / 2.0, 0.0, 1.0)
    out = np.stack([w, d, l], axis=1)
    tot = out.sum(axis=1, keepdims=True)
    empty = tot[:, 0] <= 1e-8
    out = out / np.where(tot > 1e-8, tot, 1.0)
    out[empty] = (0.0, 1.0, 0.0)
    return out


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
            for ext in ("*.xz", "*.gz", "*.bin", "*.zip"):
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
    a .xz/.gz/.bin file -- self-play writes one game per file -- and (zip, member) for
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


_GEN_DIR = re.compile(r"(?:^|[/\\])games_gen(\d+)(?:[/\\]|\.zip$|_\d+\.zip$)")


def newest_generation(games):
    """(g, games of generation g) for the highest g named by a `games_gen<g>` folder
    in a game's path (bundle member `games_gen11/...`, a directory, or a per-generation
    zip `games_gen11.zip` / `games_gen11_<N>.zip`): the generation just played, whatever
    its size. (None, []) when no game carries a generation."""
    gen = {}
    for g in games:
        path, member = g
        m = None
        if member is not None:
            m = _GEN_DIR.search("/" + member)
        if m is None:
            m = _GEN_DIR.search(path.replace("\\", "/"))
        if m:
            gen[g] = int(m.group(1))
    if not gen:
        return None, []
    top = max(gen.values())
    return top, [g for g in games if gen.get(g) == top]


def newest_n_games(games, mtimes, n):
    """The `n` NEWEST games of `games` by modification time (ties by load order: the same order split_games
    holds out from), in load order; all of them when there are fewer than `n`, none for n <= 0. Whatever generation
    they belong to: in the continuous loop that is the games played since the starting net began its last training."""
    if n <= 0 or not games:
        return []
    order = sorted(range(len(games)), key=lambda i: (mtimes[i], i))
    keep = set(order[max(0, len(order) - n):])
    return [g for i, g in enumerate(games) if i in keep]


_TD_KERNELS = {}      # lambda -> the TD weight matrix of the longest game seen so far (td_value_targets)


def _td_kernel(lam, n):
    """K[t, j] = (1 - lam) * lam ** (j - t - 1) for j > t, else 0: the weight of the search value of position j
    in the TD(lam) return of position t (top-left n x n block of one matrix per lambda, grown when needed)."""
    k = _TD_KERNELS.get(lam)
    if k is None or k.shape[0] < n:
        size = max(n, 512 if k is None else 2 * k.shape[0])
        gap = np.arange(size)[None, :] - np.arange(size)[:, None] - 1          # j - t - 1
        k = np.where(gap >= 0, (1.0 - lam) * np.power(lam, np.maximum(gap, 0)), 0.0)
        _TD_KERNELS[lam] = k
    return k[:n, :n]


def td_value_targets(recs, lam, z_weight):
    """W/D/L value targets [len(recs), 3] (float32) of ONE game's records, in game order, each from its own side to
    move: z_weight * the game result + (1 - z_weight) * the TD(lam) return

        G_t = sum_{j > t} (1 - lam) * lam^(j - t - 1) * s_j  +  lam^(L - 1 - t) * z

    s_j = the search value of position j (best_q / best_d, as the qMix uses) and z = the game result, both seen
    from the side to move at t (W and L swap at every position whose side to move differs from t's). The last
    position's return is z; lam = 1 gives z everywhere, lam = 0 the next position's search value. Computed in the
    frame of the first position (one matrix product), then turned back to each position's own side."""
    n = len(recs)
    s = wdl_from_qd_many([search_q(r) for r in recs], [r["best_d"] for r in recs])
    z = wdl_from_qd_many([r["result_q"] for r in recs], [r["result_d"] for r in recs])
    other = np.fromiter((r["side_to_move"] != recs[0]["side_to_move"] for r in recs), dtype=bool, count=n)[:, None]

    def to_first(a):                      # swaps W and L where the side to move differs: its own inverse
        return np.where(other, a[:, ::-1], a)

    tail = np.power(lam, np.arange(n - 1, -1, -1, dtype=np.float64))[:, None]
    g = _td_kernel(lam, n) @ to_first(s) + tail * to_first(z)[-1]
    return (z_weight * z + (1.0 - z_weight) * to_first(g)).astype(np.float32)


def iter_games_targets(games, rng, sparse=False, value_per_game=0, td=None):
    """iter_games with the per-GAME work of the value target done on each whole game:

      * td = (lam, z_weight): every record gets r["td_wdl"] = its td_value_targets row (the value target the
        dataset then uses instead of the qMix);
      * value_per_game = k > 0: only k positions drawn at random keep their value target (a game of k positions or
        fewer: all of them); the others are marked r["no_value"] = True, FairyDataset gives them an all-zero W/D/L
        row that train.value_loss leaves out. The policy and moves-left targets of every position are kept.

    Why value_per_game (owner's decision 2026-11-26, cell 07: 21): the value head memorized whole games -- every
    game starts from its own random position and all its positions share one result -- so it meets each game
    through fewer positions. Why td (2026-11-27): a target made of later search values carries less of the luck of
    the rest of the game, the part of the result that only a memorized game can tell."""
    grouped = iter_games_grouped(games, sparse)
    try:
        for recs in grouped:
            if td is not None:
                for r, v in zip(recs, td_value_targets(recs, *td)):
                    r["td_wdl"] = v
            if value_per_game > 0:
                keep = set(rng.sample(range(len(recs)), min(value_per_game, len(recs))))
                for i, r in enumerate(recs):
                    if i not in keep:
                        r["no_value"] = True
            yield from recs
    finally:
        grouped.close()          # closes an open .zip at once, also when the caller stops early


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
    """Yields (input[NUM_PLANES,10,10], pi[POLICY_SIZE], value[5]).

    value = [W, D, L target (the qMix of the search value and the game result), plies_left (the moves-left
    target; 0 = not filled in), has_policy (1 = full search; 0 = fast_search, the policy target is not to
    be trained on)].

    Two in-RAM cache representations (both produce identical training tensors):
      * sparse=True  (default, 8.2.2): per record keep only the compact bitboard
        words (~3.5KB), scalars, and the LEGAL policy entries as (idx, val) pairs
        (~0.6-0.9KB). Dense [NUM_PLANES,10,10] planes and the dense [POLICY_SIZE] policy are
        rebuilt lazily in __getitem__. ~4KB/record -> a 100k buffer fits in ~400MB,
        avoiding the Colab OOM the dense path would hit (~13GB).
      * sparse=False: cache the fully-dense tensors (faster per-item, much more RAM).
    """

    packed = False   # test subclasses skip __init__

    def __init__(self, data, q_ratio=0.25, downsample_keep=1.0, cache=True, seed=0,
                 diff_focus=False, df_slope=1.0, df_kld_w=0.5, df_min=0.2, sparse=True,
                 max_records=0, games=None, label="", packed=False, value_per_game=0,
                 td_lambda=None, td_z_weight=0.5):
        """`games` (from list_games / split_games) loads only those games; by
        default every game in `data`. `label` names the set in the log line.
        `packed` (sparse cache only): items are pack_compact() samples, to batch
        with collate_packed and rebuild on the device with unpack_batch.
        `td_lambda` (0..1, None = off): value target = td_z_weight * the game result + (1 - td_z_weight) *
        the TD(td_lambda) return (td_value_targets) instead of the qMix; q_ratio is then unused."""
        if td_lambda is not None and not (0.0 <= td_lambda <= 1.0 and 0.0 <= td_z_weight <= 1.0):
            raise ValueError(f"td_lambda and td_z_weight must be in [0, 1], got {td_lambda} and {td_z_weight}")
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
        # each immediately — the raw dict (with its dense 42KB probabilities[POLICY_SIZE])
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
        # The compact cache only needs the legal policy slots: v6 games then skip
        # building the dense probabilities[POLICY_SIZE] of every position.
        if value_per_game > 0 or td_lambda is not None:
            records = iter_games_targets(games, rng, sparse=compact_cache is not None, value_per_game=value_per_game,
                                         td=None if td_lambda is None else (float(td_lambda), float(td_z_weight)))
        else:
            records = iter_games(games, sparse=compact_cache is not None)
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
        target = (f"value target {td_z_weight:g} x result + {1 - td_z_weight:g} x TD({td_lambda:g})"
                  if td_lambda is not None else f"q_ratio={q_ratio}")
        print(f"[dataset] {label + ': ' if label else ''}{len(games)} games -> {kept} records "
              f"({target}, downsample={downsample_keep}, cached={cache}, "
              f"sparse={sparse and cache}"
              + (f", value target on {value_per_game} positions per game" if value_per_game > 0 else "") + ")")

    def _value(self, r):
        """[W, D, L, plies_left, has_policy] (float32[5]); the WDL part is the TD target of iter_games_targets
        (td_lambda) or else q_ratio * the search value (best_q / best_d: the average value of the most-visited
        move) + (1 - q_ratio) * the game result."""
        v = r.get("td_wdl")
        if v is None:
            z_wdl = wdl_from_qd(r["result_q"], r["result_d"])
            q_wdl = wdl_from_qd(search_q(r), r["best_d"])
            v = self.q_ratio * q_wdl + (1.0 - self.q_ratio) * z_wdl
        if r.get("no_value"):            # iter_games_targets: no value target (train.value_loss skips the row)
            v = np.zeros(3, dtype=np.float32)
        extra = np.array([float(r.get("plies_left", 0)), 0.0 if r.get("fast_search", 0) else 1.0])
        return np.concatenate([v, extra]).astype(np.float32)

    def _build(self, r):
        """Dense tensors (used by sparse=False cache and by streaming)."""
        x = torch.from_numpy(reconstruct_planes(r))                       # [NUM_PLANES,10,10] f32
        pi = torch.from_numpy(np.array(r["probabilities"], dtype=np.float32))  # own copy:
        # the reader's array is a read-only view into the record buffer
        value = torch.from_numpy(self._value(r))                          # [3]
        return x, pi, value

    def _compact(self, r):
        """Memory-thin form: bitboard words + scalars + sparse legal policy.

        Policy convention preserved exactly: illegal = -1, legal = (0 or fraction).
        We store only legal slots (pi >= 0, i.e. pi > -0.5) as (uint16 idx, f32 val);
        __getitem__ refills a -1 dense vector and writes them back."""
        if "legal_idx" in r:               # v6 game: the sparse policy is stored as is
            legal, legal_pi = r["legal_idx"], r["legal_pi"]
        else:
            pi = r["probabilities"]
            legal = np.nonzero(pi > -0.5)[0].astype(np.uint16)
            legal_pi = pi[legal].astype(np.float32)
        return {
            "piece_planes": np.asarray(r["piece_planes"], dtype=np.uint64),  # no copy (reader)
            "ep_mask": np.asarray(r["ep_mask"], dtype=np.uint64),
            "rule50_count": r["rule50_count"],
            "checks_remaining_us": r["checks_remaining_us"],
            "checks_remaining_them": r["checks_remaining_them"],
            "pi_idx": legal,
            "pi_val": legal_pi,
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
N_MASKS = HISTORY_PLANES + 1           # history planes + the e.p. plane (the first aux plane, so it follows them)
assert AUX_EN_PASSANT == 0


def pack_compact(c):
    """One compact record -> (masks int64[N_MASKS,2], scalars f32[3], pi_idx, pi_val, value f32[5]).
    The scalars are computed exactly as reconstruct_planes does (float64 division
    rounded to float32), so the planes rebuilt from them are bit-identical."""
    masks = np.empty((N_MASKS, 2), dtype=np.uint64)
    masks[:HISTORY_PLANES] = np.asarray(c["piece_planes"], dtype=np.uint64).reshape(HISTORY_PLANES, 2)
    masks[HISTORY_PLANES] = np.asarray(c["ep_mask"], dtype=np.uint64)
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
    """collate_packed batch -> (x f32[B,NUM_PLANES,10,10], pi f32[B,POLICY_SIZE], value f32[B,5])
    on `device`; x in channels_last memory format when asked (same values)."""
    masks, scal, idx, val, value = (t.to(device, non_blocking=True) for t in batch)
    b = masks.size(0)
    word, bit = _WORD_T.to(device), _BIT_T.to(device)
    fmt = torch.channels_last if channels_last else torch.contiguous_format
    x = torch.empty((b, NUM_PLANES, BOARD, BOARD), dtype=torch.float32, device=device,
                    memory_format=fmt)
    # masks[:, :, word] -> [B,N_MASKS,10,10] = the word holding each cell's bit; the
    # arithmetic shift of a negative int64 is harmless: only bit 0 is kept.
    x[:, :N_MASKS] = torch.bitwise_and(torch.bitwise_right_shift(masks[:, :, word], bit), 1)
    x[:, AUX_BASE + AUX_RULE50] = scal[:, 0, None, None]         # rule50 / 100
    x[:, AUX_BASE + AUX_CHECKS_US] = scal[:, 1, None, None]      # checks us / 10
    x[:, AUX_BASE + AUX_CHECKS_THEM] = scal[:, 2, None, None]     # checks them / 10
    pi = torch.full((b, POLICY_SIZE + 1), -1.0, dtype=torch.float32, device=device)
    pi.scatter_(1, idx, val)
    return x, pi[:, :POLICY_SIZE], value


# --------------------------------------------------------------------------- #
# Left-right mirror (train.py --mirror). The variant has no castling and every piece moves left-right
# symmetrically, so the position mirrored a<->j has the mirrored legal moves and the same value. The planes are
# seen from the side to move with the ranks flipped for Black (Move::Flip(RANK_10)), never the files, so the
# mirror is the same for both sides: reverse the file axis of every plane, and send each policy slot
# (type * 100 + from square, encoder.cc MoveToNNIndex) to the slot of the mirrored move.
# --------------------------------------------------------------------------- #
def _mirror_move_type(t):
    """Policy move type of the a<->j mirror image (dx -> -dx) of a move of type `t` (encoder.cc MoveToNNIndex)."""
    if t < SLIDE_TYPES:                    # 8 directions clockwise from north (N NE E SE S SW W NW) x distance 1..9
        d, k = divmod(t, 9)
        return ((8 - d) % 8) * 9 + k
    if t < CAMEL_BASE:                     # knight jumps, clockwise from (1, 2): i <-> 7 - i flips dx
        return KNIGHT_BASE + 7 - (t - KNIGHT_BASE)
    if t < PROMOTION_BASE:                 # camel jumps, the same order
        return CAMEL_BASE + 7 - (t - CAMEL_BASE)
    piece, d = divmod(t - PROMOTION_BASE, PROMOTION_DIRECTIONS)   # d = dx + 1: capture left / straight / right
    return PROMOTION_BASE + piece * PROMOTION_DIRECTIONS + (PROMOTION_DIRECTIONS - 1 - d)


def mirror_policy_permutation():
    """int64[POLICY_SIZE]: slot i of a position is slot perm[i] of its mirror image. An involution (perm[perm] is
    the identity), so the mirrored policy is original[:, perm]."""
    sq = np.arange(SQUARES)
    sq_m = (sq // BOARD) * BOARD + (BOARD - 1 - sq % BOARD)
    types_m = np.array([_mirror_move_type(t) for t in range(MOVE_TYPES)], dtype=np.int64)
    return (types_m[:, None] * SQUARES + sq_m[None, :]).reshape(-1)


MIRROR_POLICY = mirror_policy_permutation()
assert np.array_equal(MIRROR_POLICY[MIRROR_POLICY], np.arange(POLICY_SIZE))
_MIRROR_POLICY_T = {}    # device -> MIRROR_POLICY as a tensor there


def mirror_batch(x, pi, flip):
    """(x [B, NUM_PLANES, 10, 10], pi [B, POLICY_SIZE]) with the rows where `flip` [B] (bool, same device) is True
    replaced by their mirror images; the value target does not change. The legal-move mask moves with the policy
    (illegal slots are -1 and stay -1)."""
    perm = _MIRROR_POLICY_T.get(x.device)
    if perm is None:
        perm = _MIRROR_POLICY_T[x.device] = torch.from_numpy(MIRROR_POLICY).to(x.device)
    x = torch.where(flip[:, None, None, None], x.flip(-1), x)
    pi = torch.where(flip[:, None], pi.index_select(1, perm), pi)
    return x, pi
