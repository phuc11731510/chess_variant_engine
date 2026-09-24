# Built-in self-tests (`src/tests/`)

Every test is compiled into `custom_engine` and started with a command-line flag.
A suite prints `[PASS]` lines and exits 0, or prints `[FAIL] ...` and exits 1.

```
custom_engine --test-<name> [--weights <net.onnx>]
```

| File | Flag(s) | What it guards |
|---|---|---|
| `test_ep.cc` | `--test-ep` | En passant, including en passant that lands on a promotion square, for Pawn and Sergeant, straight and diagonal, and own-king safety (rank, file, diagonal). |
| `test_rules.cc` | `--test-rules`, `--test-bits`, `--test-perft`, `--audit-generation` | Game rules (threefold repetition, rule 50, n-checks -- each must end the game on exactly the right ply), bitboards, perft of the adapter vs raw Fairy-Stockfish, and a random-game differential fuzzer (`--audit-generation --games N --max-moves M`). |
| `test_rules_oracle.cc` | `--audit-rules [--games N --max-moves M]` | **An independent re-implementation of the variant rules** (no code shared with Fairy-Stockfish), compared with the engine over random games: the legal move set, the result of every legal move (board, castling, e.p., checks, rule 50, check flag, `gives_check`), `undo_move`, Zobrist key vs key from FEN, game result and repetition count, the 226 NN input planes, the record fields and `MoveToNNIndex`. Castling on any rank (shuffled starts on ranks 2/3/6/9, a discovered check by the rook leaving, king or rook landing on the other's square). Fails if any rule (e.p. of each kind, e.p.+promotion, castling each side and off the first rank, castling giving check, stalemate, mate, last check, repetition and rule-50 draws, ...) was never exercised. Default 5 games per start position (120, ~4 s); use `--games 1000 --max-moves 300` for a deep run (~30 s). |
| `test_board.cc` | `--test-board`, `--test-adapter`, `--test-uci` | The `ChessBoard` adapter between lczero and Fairy-Stockfish (canonical flip, apply/undo, copies) and UCI move I/O. TEST 8: castling on any rank (landing squares, rook shield, discovered check, a king that does not move written king -> rook), the castling rook's square in the Zobrist key, `fen()` reading back to the same rooks, record castling squares. |
| `test_nn_io.cc` | `--test-policy`, `--test-nn`, `--test-encoder` | Move <-> policy-index mapping (a bijection) and the NN input planes. |
| `test_trainingdata.cc` | `--test-trainingdata`, `--emit-roundtrip <prefix>` | The training-record layout and the gzip writer/reader; `--emit-roundtrip` feeds `python/test_roundtrip.py` (195 positions: random games, castling incl. rooks on ranks 2-9, Sergeant e.p., repetitions). |
| `test_search.cc` | `--test-mcts`, `--test-extract`, `--test-selfplay` | Search / extraction / one-game self-play integration. `--test-mcts` is a smoke test only (it asserts nothing). |
| `test_search_logic.cc` | `--test-search-logic [--weights net.onnx]` | **Strict** search checks: search values in training records are side-to-move; Dirichlet noise at the root of every self-play move; tree bookkeeping (visit sums, virtual loss, exact value averages, sorted priors) under threads, task workers, out-of-order evals, prefetch and tree reuse; thread-safe `AddInput` for every backend; the 384-moves capacity; UCI `ReuseTree` (always with `DetBackend`, and also through the ONNX backend with `--weights`); a search start-up/tear-down stress test; a self-play game file written by `PlayOneGame` replays exactly (planes, pi mask, best/played index, game end, z of every record). With `--weights`, the ONNX backend is included (AddInput concurrency, the UCI engine on the real network; slow on a CPU). |
| `test_history.cc` | `--test-history` | Position history and hashing: the 200 -> 100 ply history trim is invisible, Zobrist keys (incremental == from FEN, e.p. rights count), the NN-cache key separates repetitions, game-end precedence matches Fairy-Stockfish, n-check results for both colours, repetitions and threefold draws at every rule-50 count (checked against Fairy-Stockfish's own n-fold rule). |
| `test_neural.cc` | `--test-neural [--weights net.onnx]` | **The NN layer** (`src/lczero_chess/neural/`): the engine's softmax against an exact one in double (every move count to 384, temperatures 0.25-4, logit spreads to 60, very negative logits, NaN/inf); the value-output check; the fixed-batch buffer sizing; with `--weights`, `OnnxBackend` against an independent ONNX Runtime session run one position at a time (dynamic batch and fixed batches 1/7/16/24/48/64, batch sizes 1, f-1, f, f+1, 37, 64, temperatures 1 and 0.25); the NN cache (hit == miss, the prefetch existence probe, move-count mismatch, clearing on a weights change, a torn-read stress test of the seqlock); `BatchingBackend` exactness with 6 producers; `orig_q`/`policy_kld` stay the root's raw eval when its cache entry is evicted. ~70 s with a 12x144 net on a CPU; any net with the engine's I/O will do, e.g. a tiny one (`python python/make_seed.py --channels 8 --blocks 1 --out tiny.onnx`): ~4 s. |
| `test_app.cc` | `--test-cli` | **Run-mode input checks** (`src/app/`): every command line of the docs/scripts/notebooks parses and sets what it says; typos, missing values, malformed or out-of-range numbers and stray words are errors; `--search-opt` types/ranges/choices; `CheckStartFen` (missing `N+N`, bad board, royals, a side not to move in check, castling rights that FSF would drop or re-assign -- `K` read as a queen-side right, a rook on another rank than its royal piece). |
| `test_common.h` | | Shared includes, `MockBackend` (uniform priors), `fztest::DetBackend` (deterministic, thread-safe, non-uniform), and small search helpers. |

`MockBackend` and `fztest::DetBackend` need no network. Without `--weights`, the
tests that would load one either fall back to `MockBackend` or print `[SKIP]`.

## Running everything

Run each flag in turn; all must exit 0. `--test-search-logic --weights <net>`
is the slowest (a few minutes on CPU).

Python side (`python/`):

| Script | What it guards |
|---|---|
| `test_extreme.py` | record layout (and refusal of unknown versions), W/D/L targets, qMix, legacy Q signs, sparse == dense cache, masked policy loss, aux planes, bitboard decode, archive round-trip, and `audit_generation.py` catching each kind of corrupted game. |
| `test_roundtrip.py <prefix>` | after `custom_engine --emit-roundtrip <prefix>`: the Python planes are exactly the engine's (118 positions). |
| `test_engine_parity.py <prefix> net.pt --onnx net.onnx` | after `custom_engine --emit-roundtrip <prefix> --weights net.onnx`: the engine's priors and W/D/L for every position equal PyTorch's on the record's planes, and the .onnx computes what the .pt does. The whole C++ <-> Python contract in one check. |
| `test_train_pipeline.py` | runs the real `make_seed.py` / `train.py` on a tiny net: `--max-steps` exports trained weights, SWA averages the right epochs, a `--data` part that matches nothing stops the run, the exported .onnx equals the .pt. |
| `test_bits.py` | the 128-bit mask decoder, square by square. |

## Adding a test

Put it in the file for its area, or in a new `test_<area>.cc` that includes
`tests/test_common.h`. Load the variant with `setup_custom_variant()` -- never
with a copy of its INI (such copies drifted from the real definition twice).
Declare the entry point in `engine_tests.h`, add a flag
in `app/cli.{h,cc}` and a dispatch line in `main.cc`, and list the file in
`meson.build` (`engine_sources`). Prefer checks that fail loudly on a silent
error: compare against an independent reference (raw Fairy-Stockfish, lc0's
own reporting, a deterministic backend) rather than printing values.
