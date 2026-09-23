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
| `test_rules_oracle.cc` | `--audit-rules [--games N --max-moves M]` | **An independent re-implementation of the variant rules** (no code shared with Fairy-Stockfish), compared with the engine over random games: the legal move set, the result of every legal move (board, castling, e.p., checks, rule 50, check flag, `gives_check`), `undo_move`, Zobrist key vs key from FEN, game result and repetition count, the 226 NN input planes, the record fields and `MoveToNNIndex`. Fails if any rule (e.p. of each kind, e.p.+promotion, castling each side, stalemate, mate, last check, repetition and rule-50 draws, ...) was never exercised. Default 100 games (~5 s); use `--games 1000 --max-moves 300` for a deep run (~70 s). |
| `test_board.cc` | `--test-board`, `--test-adapter`, `--test-uci` | The `ChessBoard` adapter between lczero and Fairy-Stockfish (canonical flip, apply/undo, copies) and UCI move I/O. |
| `test_nn_io.cc` | `--test-policy`, `--test-nn`, `--test-encoder` | Move <-> policy-index mapping (a bijection) and the NN input planes. |
| `test_trainingdata.cc` | `--test-trainingdata`, `--emit-roundtrip <prefix>` | The training-record layout and the gzip writer/reader; `--emit-roundtrip` feeds `python/test_roundtrip.py` (118 positions: random games, castling, Sergeant e.p., repetitions). |
| `test_search.cc` | `--test-mcts`, `--test-extract`, `--test-selfplay` | Search / extraction / one-game self-play integration. `--test-mcts` is a smoke test only (it asserts nothing). |
| `test_search_logic.cc` | `--test-search-logic [--weights net.onnx]` | **Strict** search checks: search values in training records are side-to-move; Dirichlet noise at the root of every self-play move; tree bookkeeping (visit sums, virtual loss, exact value averages, sorted priors) under threads, task workers, out-of-order evals, prefetch and tree reuse; thread-safe `AddInput` for every backend; the 384-moves capacity; UCI `ReuseTree` (always with `DetBackend`, and also through the ONNX backend with `--weights`); a search start-up/tear-down stress test; a self-play game file written by `PlayOneGame` replays exactly (planes, pi mask, best/played index, game end, z of every record). With `--weights`, the ONNX backend is included (AddInput concurrency, the UCI engine on the real network; slow on a CPU). |
| `test_history.cc` | `--test-history` | Position history and hashing: the 200 -> 100 ply history trim is invisible, Zobrist keys (incremental == from FEN, e.p. rights count), the NN-cache key separates repetitions, game-end precedence matches Fairy-Stockfish, n-check results for both colours, repetitions and threefold draws at every rule-50 count (checked against Fairy-Stockfish's own n-fold rule). |
| `test_common.h` | | Shared includes, `MockBackend` (uniform priors), `fztest::DetBackend` (deterministic, thread-safe, non-uniform), and small search helpers. |

`MockBackend` and `fztest::DetBackend` need no network. Without `--weights`, the
tests that would load one either fall back to `MockBackend` or print `[SKIP]`.

## Running everything

Run each flag in turn; all must exit 0. `--test-search-logic --weights <net>`
is the slowest (a few minutes on CPU). Python-side checks live in
`python/test_extreme.py` and `python/test_roundtrip.py`.

## Adding a test

Put it in the file for its area, or in a new `test_<area>.cc` that includes
`tests/test_common.h`. Load the variant with `setup_custom_variant()` -- never
with a copy of its INI (such copies drifted from the real definition twice).
Declare the entry point in `engine_tests.h`, add a flag
in `app/cli.{h,cc}` and a dispatch line in `main.cc`, and list the file in
`meson.build` (`engine_sources`). Prefer checks that fail loudly on a silent
error: compare against an independent reference (raw Fairy-Stockfish, lc0's
own reporting, a deterministic backend) rather than printing values.
