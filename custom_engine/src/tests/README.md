# Built-in self-tests (`src/tests/`)

Every test is compiled into `custom_engine` and started with a command-line flag.
A suite prints `[PASS]` lines and exits 0, or prints `[FAIL] ...` and exits 1.

```
custom_engine --test-<name> [--weights <net.onnx>]
```

| File | Flag(s) | What it guards |
|---|---|---|
| `test_ep.cc` | `--test-ep` | En passant, including en passant that lands on a promotion square, for Pawn and Sergeant, straight and diagonal, and own-king safety (rank, file, diagonal). |
| `test_rules.cc` | `--test-rules`, `--test-bits`, `--test-perft`, `--audit-generation` | Game rules (n-checks, stalemate = loss, promotions), bitboards, perft of the adapter vs raw Fairy-Stockfish, and a random-game differential fuzzer (`--audit-generation --games N --max-moves M`). |
| `test_board.cc` | `--test-board`, `--test-adapter`, `--test-uci` | The `ChessBoard` adapter between lczero and Fairy-Stockfish (canonical flip, apply/undo, copies) and UCI move I/O. |
| `test_nn_io.cc` | `--test-policy`, `--test-nn`, `--test-encoder` | Move <-> policy-index mapping (a bijection) and the NN input planes. |
| `test_trainingdata.cc` | `--test-trainingdata`, `--emit-roundtrip <prefix>` | The training-record layout and the gzip writer/reader; `--emit-roundtrip` feeds `python/test_roundtrip.py`. |
| `test_search.cc` | `--test-mcts`, `--test-extract`, `--test-selfplay` | Search / extraction / one-game self-play integration. `--test-mcts` is a smoke test only (it asserts nothing). |
| `test_search_logic.cc` | `--test-search-logic [--weights net.onnx]` | **Strict** search checks: search values in training records are side-to-move; Dirichlet noise at the root of every self-play move; tree bookkeeping (visit sums, virtual loss, exact value averages, sorted priors) under threads, task workers, out-of-order evals, prefetch and tree reuse; thread-safe `AddInput` for every backend; the 384-moves capacity; UCI `ReuseTree`; a search start-up/tear-down stress test. With `--weights`, the ONNX backend and the UCI engine are included. |
| `test_history.cc` | `--test-history` | Position history and hashing: the 200 -> 100 ply history trim is invisible, Zobrist keys (incremental == from FEN, e.p. rights count), the NN-cache key separates repetitions, game-end precedence matches Fairy-Stockfish, n-check results for both colours. |
| `test_common.h` | | Shared includes, `MockBackend` (uniform priors), `fztest::DetBackend` (deterministic, thread-safe, non-uniform), and small search helpers. |

`MockBackend` and `fztest::DetBackend` need no network. Without `--weights`, the
tests that would load one either fall back to `MockBackend` or print `[SKIP]`.

## Running everything

Run each flag in turn; all must exit 0. `--test-search-logic --weights <net>`
is the slowest (a few minutes on CPU). Python-side checks live in
`python/test_extreme.py` and `python/test_roundtrip.py`.

## Adding a test

Put it in the file for its area, or in a new `test_<area>.cc` that includes
`tests/test_common.h`. Declare the entry point in `engine_tests.h`, add a flag
in `app/cli.{h,cc}` and a dispatch line in `main.cc`, and list the file in
`meson.build` (`engine_sources`). Prefer checks that fail loudly on a silent
error: compare against an independent reference (raw Fairy-Stockfish, lc0's
own reporting, a deterministic backend) rather than printing values.
