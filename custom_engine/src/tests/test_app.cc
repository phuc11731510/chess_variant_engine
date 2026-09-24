// --test-cli : the run modes' input checks (src/app/).
//
//   1. parse_cli: every command line the docs, scripts and notebooks use parses
//      without an error and sets what it says; typos, missing values, malformed
//      or out-of-range numbers and stray words are errors (they used to be
//      skipped silently, running with defaults the user did not ask for).
//   2. ApplySearchOptChecked: lc0's types, ranges and choices are enforced.
//   3. CheckStartFen: start positions for --start-fen / an opening book.

#include "tests/test_common.h"
#include "app/cli.h"

namespace {

int g_fail = 0;

#define EXPECT(cond, msg)                                         \
    do {                                                          \
        if (!(cond)) {                                            \
            ++g_fail;                                             \
            std::cerr << "  [FAIL] " << msg << std::endl;         \
        }                                                         \
    } while (0)

EngineOptions Parse(const std::vector<std::string>& args) {
    std::vector<std::string> all = {"custom_engine"};
    all.insert(all.end(), args.begin(), args.end());
    std::vector<char*> argv;
    for (auto& a : all) argv.push_back(a.data());
    return parse_cli(static_cast<int>(argv.size()), argv.data());
}

std::string Join(const std::vector<std::string>& v) {
    std::string s;
    for (const auto& x : v) s += (s.empty() ? "" : " ") + x;
    return s;
}

void TestParseCli() {
    std::cout << "--- 1. parse_cli ---" << std::endl;
    // The self-play command of the operating notebook (FairyZero_vanhanh.ipynb).
    {
        const auto o = Parse({"--selfplay", "--games", "100000", "--max-seconds", "19080",
                              "--visits", "800", "--max-moves", "400", "--temp-cutoff", "32",
                              "--parallel", "4", "--provider", "cuda", "--fixed-batch", "16",
                              "--noise-alpha", "0.15", "--show-nps", "--weights", "/content/seed_gen0.onnx",
                              "--out", "/content/games_gen0"});
        EXPECT(o.errors.empty(), "notebook self-play command: " << (o.errors.empty() ? "" : o.errors[0]));
        EXPECT(o.selfplay_mode && o.sp_games == 100000 && o.sp_max_seconds == 19080.0 &&
                   o.sp_visits == 800 && o.sp_max_moves == 400 && o.sp_temp_cutoff == 32 &&
                   o.sp_parallel == 4 && o.sp_provider == "cuda" && o.sp_fixed_batch == 16 &&
                   std::fabs(o.sp_noise_alpha - 0.15f) < 1e-7 && o.sp_show_nps &&
                   o.weights_file == "/content/seed_gen0.onnx" && o.sp_out == "/content/games_gen0",
               "notebook self-play command: a value was not taken");
    }
    // The arena command of the notebook.
    {
        const auto o = Parse({"--arena", "--model-a", "a.onnx", "--model-b", "b.onnx", "--games", "400",
                              "--visits", "200", "--temp-cutoff", "32", "--provider", "cuda",
                              "--fixed-batch", "16", "--max-moves", "400", "--show-nps"});
        EXPECT(o.errors.empty() && o.arena_mode && o.arena_a == "a.onnx" && o.arena_b == "b.onnx" &&
                   o.sp_games == 400 && o.sp_visits == 200,
               "notebook arena command");
    }
    // Other documented forms.
    for (const auto& args : std::vector<std::vector<std::string>>{
             {"--selfplay", "--resign-threshold", "-0.90", "--resign-consecutive", "3",
              "--no-resign-frac", "0.10", "--search-opt", "max-prefetch=0", "--search-opt", "cpuct=2.5",
              "--batch-aggregate", "--batch-timeout-us", "500", "--cuda-graph", "--threads-per-game", "2",
              "--backend-threads", "4", "--policy-temp", "1.0", "--cpuct", "1.745", "--noise-epsilon",
              "0.25", "--start-fen", "book.txt", "--resign-earliest-move", "20"},
             {"--emit-roundtrip", "python/rt"},
             {"--emit-roundtrip"},
             {"--test-mcts", "w.onnx"},
             {"--test-search-logic", "--weights", "net.onnx"},
             {"--audit-rules", "--games", "1000", "--max-moves", "300"},
             {"--play-black", "--weights", "net.onnx", "--visits", "400"},
             {"--uci-nn", "--weights", "net.onnx", "--provider", "dml"},
             {"--bench-nn", "--weights", "net.onnx", "--provider", "cuda", "--cuda-graph"},
             {"--arena", "--model-a", "a", "--model-b", "b", "--arena-moves"},
         }) {
        const auto o = Parse(args);
        EXPECT(o.errors.empty(), "'" << Join(args) << "' rejected: " << (o.errors.empty() ? "" : o.errors[0]));
    }
    {
        const auto o = Parse({"--emit-roundtrip", "python/rt"});
        EXPECT(o.emit_roundtrip_mode && o.rt_prefix == "python/rt", "--emit-roundtrip prefix");
        const auto s = Parse({"--selfplay", "--search-opt", "max-prefetch=0", "--search-opt", "cpuct=2.5"});
        EXPECT(s.sp_search_opts.size() == 2 && s.sp_search_opts[1].first == "cpuct" &&
                   s.sp_search_opts[1].second == "2.5",
               "--search-opt pairs");
        // --zobrist-seed takes the 10-digit seeds the engine prints (past a 32-bit long).
        const auto z = Parse({"--selfplay", "--zobrist-seed", "9999999999"});
        EXPECT(z.errors.empty() && z.zobrist_seed == 9999999999ULL, "--zobrist-seed 9999999999");
        EXPECT(Parse({"--selfplay", "--zobrist-seed", "1000000000"}).zobrist_seed == 1000000000ULL &&
                   Parse({"--selfplay"}).zobrist_seed == 0,
               "--zobrist-seed 1000000000, and 0 (random) without the flag");
    }
    // Every one of these must be an error, not a default.
    for (const auto& args : std::vector<std::vector<std::string>>{
             {"--selfplay", "--visit", "800"},           // typo'd flag
             {"--selfplay", "--max-move", "400"},        // typo'd flag
             {"--selfplay", "--visits"},                 // missing value
             {"--selfplay", "--visits", "8OO"},          // letter O
             {"--selfplay", "--visits", "800x"},
             {"--selfplay", "--visits", "0"},
             {"--selfplay", "--games", "-1"},
             {"--selfplay", "--max-moves", "-5"},
             {"--selfplay", "--noise-alpha", "abc"},
             {"--selfplay", "--noise-alpha", "0"},
             {"--selfplay", "--noise-epsilon", "1.5"},
             {"--selfplay", "--policy-temp", "nan"},
             {"--selfplay", "--fixed-batch", "65"},
             {"--selfplay", "--parallel", "0"},
             {"--selfplay", "--max-seconds", "-3"},
             {"--selfplay", "--search-opt", "cpuct"},    // no '='
             {"--selfplay", "--search-opt", "=2"},
             {"--selfplay", "--provider", "gpu"},
             {"--selfplay", "800"},                      // stray word
             {"--selfplay", "--weights"},
             {"--selfplay", "--zobrist-seed", "999999999"},     // 9 digits
             {"--selfplay", "--zobrist-seed", "10000000000"},   // 11 digits
             {"--selfplay", "--zobrist-seed", "-1234567890"},
             {"--selfplay", "--zobrist-seed", "12345678901234567890123"},
             {"--selfplay", "--zobrist-seed", "12345x7890"},
         }) {
        const auto o = Parse(args);
        EXPECT(!o.errors.empty(), "'" << Join(args) << "' was accepted");
    }
}

void TestSearchOpts() {
    std::cout << "--- 2. ApplySearchOptChecked ---" << std::endl;
    fztest::TestSearchOptions so;
    auto* d = so.parser.GetMutableDefaultsOptions();
    using BP = lczero::classic::BaseSearchParams;
    struct Ok { const char* name; const char* value; };
    for (const Ok& ok : {Ok{"cpuct", "2.5"}, Ok{"max-prefetch", "0"}, Ok{"minibatch-size", "64"},
                         Ok{"task-workers", "-1"}, Ok{"two-fold-draws", "false"},
                         Ok{"fpu-strategy", "absolute"}, Ok{"score-type", "W-L"},
                         Ok{"policy-softmax-temp", "1.359"}, Ok{"draw-score", "-1"}}) {
        const std::string err = ApplySearchOptChecked(d, ok.name, ok.value);
        EXPECT(err.empty(), ok.name << "=" << ok.value << " rejected: " << err);
    }
    EXPECT(d->Get<float>(BP::kCpuctId) == 2.5f, "cpuct not set to 2.5");
    EXPECT(d->Get<int>(lczero::classic::SearchParams::kMaxPrefetchBatchId) == 0, "max-prefetch not 0");
    EXPECT(!d->Get<bool>(BP::kTwoFoldDrawsId), "two-fold-draws not false");
    EXPECT(d->Get<std::string>(BP::kFpuStrategyId) == "absolute", "fpu-strategy not absolute");

    for (const Ok& bad : {Ok{"cpuct", "abc"}, Ok{"cpuct", "101"}, Ok{"cpuct", ""}, Ok{"draw-score", "5"},
                          Ok{"minibatch-size", "100"}, Ok{"max-prefetch", "x"}, Ok{"max-prefetch", "65"},
                          Ok{"task-workers", "-2"}, Ok{"fpu-strategy", "absolut"},
                          Ok{"two-fold-draws", "yes"}, Ok{"cpuct-at-rot", "2"}, Ok{"minibatch-size", "3.5"}}) {
        const float before = d->Get<float>(BP::kCpuctId);
        const std::string err = ApplySearchOptChecked(d, bad.name, bad.value);
        EXPECT(!err.empty(), bad.name << "=" << bad.value << " was accepted");
        EXPECT(d->Get<float>(BP::kCpuctId) == before, bad.name << "=" << bad.value << " changed cpuct");
    }
    EXPECT(d->Get<int>(lczero::classic::SearchParams::kMaxPrefetchBatchId) == 0,
           "a rejected max-prefetch value still changed it");
    EXPECT(d->Get<std::string>(BP::kFpuStrategyId) == "absolute", "a rejected choice changed fpu-strategy");
}

void TestStartFen() {
    std::cout << "--- 3. CheckStartFen ---" << std::endl;
    for (const char* ok : {lczero::ChessBoard::kStartposFen,
                           "1r3k2r1/2p4p2/10/4n5/10/10/5B4/10/2P4P2/1R3K2R1 w BIbi - 8+8 0 1",
                           "4k5/3s1s4/10/2P1S1P3/10/10/10/10/10/4K5 b - - 8+8 0 1",
                           "k9/10/10/3pP5/10/10/10/10/10/K9 w - d8 8+8 0 1",
                           "n3k5/10/10/10/10/10/10/10/10/4K4N w - - 3+5 30 20",
                           // KQkq means the same rooks as BIbi in the start position.
                           "vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w KQkq - 8+8 0 1",
                           // Shuffled rooks, written with their files: unambiguous.
                           "4k5/10/10/10/10/10/10/10/10/R4K3R w J - 8+8 0 1",
                           "4k5/10/10/10/10/10/10/10/10/R4K3R w AJ - 8+8 0 1",
                           // Castling on any rank: the royal piece and its rooks on
                           // ranks 2/9 (K/Q look on the royal piece's rank too), 3/6.
                           "10/1r3k2r1/10/10/10/10/10/10/1R3K2R1/10 w BIbi - 8+8 0 1",
                           "10/1r3k2r1/10/10/10/10/10/10/1R3K2R1/10 w KQkq - 8+8 0 1",
                           "10/10/10/10/1r3k3r/10/10/R3K2R2/10/10 b AHbj - 8+8 0 1"}) {
        const std::string why = CheckStartFen(ok);
        EXPECT(why.empty(), "valid FEN rejected (" << why << "): " << ok);
    }
    struct Bad { const char* fen; const char* what; };
    for (const Bad& bad : {
             Bad{"vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi - 0 1",
                 "no checks field (read as 1+1)"},
             Bad{"vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi -",
                 "only 4 fields"},
             Bad{"4k5/10/10/10/10/10/10/10/10/4K5 w - - 0+8 0 1", "0 checks left"},
             Bad{"4k5/10/10/10/10/10/10/10/10/4K5 w - - 10+10 0 1", "two-digit checks"},
             Bad{"4k5/10/10/10/10/10/10/10/4K5 w - - 8+8 0 1", "9 ranks"},
             Bad{"4k6/10/10/10/10/10/10/10/10/4K5 w - - 8+8 0 1", "11 squares in a rank"},
             Bad{"4k5/10/10/10/10/10/10/10/10/4K4 w - - 8+8 0 1", "9 squares in a rank"},
             Bad{"4k5/10/10/10/10/10/10/10/10/4X5 w - - 8+8 0 1", "unknown piece letter"},
             Bad{"4k5/10/10/10/10/10/10/10/10/10 w - - 8+8 0 1", "no white royal"},
             Bad{"4k5/10/10/10/10/10/10/10/10/3KK5 w - - 8+8 0 1", "two white royals"},
             Bad{"4k5/10/10/10/10/10/10/10/10/4K5 w BIbi - 8+8 0 1", "castling rights without rooks"},
             Bad{"4k5/10/10/10/10/10/10/10/5K4/8R1 w I - 8+8 0 1", "castling rook on another rank than the royal piece"},
             // Rooks on a1/j1: Fairy-Stockfish reads a lone "K" as the first rook
             // from the i-file towards a -- the a1 rook, i.e. a QUEEN-side right.
             Bad{"4k5/10/10/10/10/10/10/10/10/R4K3R w K - 8+8 0 1", "'K' turned into a queen-side right"},
             Bad{"vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BBbi - 8+8 0 1",
                 "a castling letter written twice"},
             Bad{"k9/10/10/10/10/R9/10/10/10/K9 w - - 8+8 0 1", "side not to move in check"},
             Bad{"4k5/10/10/10/10/10/10/10/10/4K5 x - - 8+8 0 1", "side to move x"},
         }) {
        const std::string why = CheckStartFen(bad.fen);
        EXPECT(!why.empty(), bad.what << ": accepted " << bad.fen);
        if (!why.empty()) std::cout << "  [ok] " << bad.what << " -> " << why << std::endl;
    }
}

}  // namespace

void run_cli_tests() {
    std::cout << "=== --test-cli: run-mode input checks ===" << std::endl;
    setup_custom_variant();
    TestParseCli();
    TestSearchOpts();
    TestStartFen();
    if (g_fail) {
        std::cerr << "[FAIL] --test-cli: " << g_fail << " check(s) failed" << std::endl;
        std::exit(1);
    }
    std::cout << "[PASS] --test-cli" << std::endl;
}
