#include "app/cli.h"
#include <cerrno>
#include <cmath>
#include <cstdlib>
#include <string>
#include <type_traits>

// Every flag is checked: an unknown flag, a missing value or a malformed number
// is an error (main() prints it and exits 2). Before, they were skipped without
// a word, so a typo silently changed what self-play generated -- `--visit 800`
// ran at the default 200 visits, `--max-move 400` adjudicated every game at the
// default 200 plies, `--visits 8OO` (letter O) ran 8 visits.
EngineOptions parse_cli(int argc, char* argv[]) {
    EngineOptions o;
    auto error = [&](const std::string& msg) { o.errors.push_back(msg); };

    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        // Value of flag `a` (the next argument), or nullptr after reporting it missing.
        auto value = [&]() -> const char* {
            if (i + 1 >= argc) {
                error(a + " needs a value");
                return nullptr;
            }
            return argv[++i];
        };
        auto int_value = [&](int* out, long lo, long hi) {
            const char* v = value();
            if (!v) return;
            errno = 0;
            char* end = nullptr;
            const long x = std::strtol(v, &end, 10);
            if (end == v || *end != '\0' || errno == ERANGE || x < lo || x > hi) {
                error(a + " " + v + ": expected an integer in [" + std::to_string(lo) + ", " +
                      std::to_string(hi) + "]");
                return;
            }
            *out = static_cast<int>(x);
        };
        auto real_value = [&](auto* out, double lo, double hi) {
            const char* v = value();
            if (!v) return;
            char* end = nullptr;
            const double x = std::strtod(v, &end);
            if (end == v || *end != '\0' || !std::isfinite(x) || x < lo || x > hi) {
                error(a + " " + v + ": expected a number in [" + std::to_string(lo) + ", " +
                      std::to_string(hi) + "]");
                return;
            }
            *out = static_cast<std::remove_pointer_t<decltype(out)>>(x);
        };
        auto string_value = [&](std::string* out) {
            if (const char* v = value()) *out = v;
        };
        constexpr long kBig = 1000000000L;

        // --- modes ---
        if      (a == "--selfplay")           o.selfplay_mode = true;
        else if (a == "--arena")              o.arena_mode = true;
        else if (a == "--uci-nn")             o.uci_nn_mode = true;
        else if (a == "--play")               o.play_mode = true;
        else if (a == "--play-black")         { o.play_mode = true; o.play_human_white = false; }
        else if (a == "--bench-cpu")          o.bench_cpu_mode = true;
        else if (a == "--bench-nn")           o.bench_nn_mode = true;
        else if (a == "--audit-generation")   o.audit_generation_mode = true;
        else if (a == "--audit-rules")        o.audit_rules_mode = true;
        else if (a == "--test-ep")            o.test_ep_mode = true;
        else if (a == "--test-board")         o.test_board_mode = true;
        else if (a == "--test-policy")        o.test_policy_mode = true;
        else if (a == "--test-trainingdata")  o.test_trainingdata_mode = true;
        else if (a == "--test-extract")       o.test_extract_mode = true;
        else if (a == "--test-selfplay")      o.test_selfplay_mode = true;
        else if (a == "--test-perft")         o.test_perft_mode = true;
        else if (a == "--test-bits")          o.test_bits_mode = true;
        else if (a == "--test-rules")         o.test_rules_mode = true;
        else if (a == "--test-adapter")       o.test_adapter_mode = true;
        else if (a == "--test-nn")            o.test_nn_mode = true;
        else if (a == "--test-uci")           o.test_uci_mode = true;
        else if (a == "--test-encoder")       o.test_encoder_mode = true;
        else if (a == "--test-search-logic")  o.test_search_logic_mode = true;
        else if (a == "--test-history")       o.test_history_mode = true;
        else if (a == "--test-neural")        o.test_neural_mode = true;
        else if (a == "--test-cli")           o.test_cli_mode = true;
        else if (a == "--test-mcts") {         // optional value: the weights file
            o.test_mcts_mode = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') o.weights_file = argv[++i];
        } else if (a == "--emit-roundtrip") {  // optional value: the output prefix
            o.emit_roundtrip_mode = true;
            if (i + 1 < argc && argv[i + 1][0] != '-') o.rt_prefix = argv[++i];
        }
        // --- self-play / arena / play / bench parameters ---
        else if (a == "--games")              { int_value(&o.sp_games, 0, kBig); o.games_given = true; }
        else if (a == "--visits")             int_value(&o.sp_visits, 1, kBig);
        else if (a == "--parallel")           int_value(&o.sp_parallel, 1, 4096);
        else if (a == "--threads-per-game")   int_value(&o.sp_threads_per_game, 1, 256);
        else if (a == "--max-moves")          int_value(&o.sp_max_moves, 1, kBig);
        else if (a == "--max-seconds")        real_value(&o.sp_max_seconds, 0.0, 1e9);
        else if (a == "--temp-cutoff")        int_value(&o.sp_temp_cutoff, 0, kBig);
        else if (a == "--backend-threads")    int_value(&o.sp_backend_threads, 1, 256);
        else if (a == "--fixed-batch")        int_value(&o.sp_fixed_batch, 1, 64);
        else if (a == "--noise-epsilon")      real_value(&o.sp_noise_eps, 0.0, 1.0);
        else if (a == "--noise-alpha")        real_value(&o.sp_noise_alpha, 1e-6, 1e6);
        else if (a == "--policy-temp")        real_value(&o.sp_policy_temp, 1e-3, 1e3);
        else if (a == "--cpuct")              real_value(&o.sp_cpuct, 0.0, 1e6);
        else if (a == "--resign-threshold")   real_value(&o.sp_resign_threshold, -2.0, 1.0);
        else if (a == "--resign-consecutive") int_value(&o.sp_resign_consecutive, 1, kBig);
        else if (a == "--resign-earliest-move") int_value(&o.sp_resign_earliest, 0, kBig);
        else if (a == "--no-resign-frac")     real_value(&o.sp_no_resign_frac, 0.0, 1.0);
        else if (a == "--batch-timeout-us")   int_value(&o.sp_batch_timeout_us, 0, kBig);
        else if (a == "--provider")           string_value(&o.sp_provider);
        else if (a == "--out")                string_value(&o.sp_out);
        else if (a == "--start-fen")          string_value(&o.sp_start_fen);
        else if (a == "--weights")            { string_value(&o.weights_file); o.weights_given = true; }
        else if (a == "--model-a")            string_value(&o.arena_a);
        else if (a == "--model-b")            string_value(&o.arena_b);
        else if (a == "--show-nps")           o.sp_show_nps = true;
        else if (a == "--cuda-graph")         o.sp_cuda_graph = true;
        else if (a == "--batch-aggregate")    o.sp_batch_aggregate = true;
        else if (a == "--arena-moves")        o.arena_show_moves = true;
        else if (a == "--search-opt") {        // "name=value"
            std::string kv;
            const size_t errors_before = o.errors.size();
            string_value(&kv);
            const auto eq = kv.find('=');
            if (o.errors.size() != errors_before) {
                // missing value, already reported
            } else if (eq == std::string::npos || eq == 0) {
                error("--search-opt '" + kv + "': expected name=value");
            } else {
                o.sp_search_opts.emplace_back(kv.substr(0, eq), kv.substr(eq + 1));
            }
        } else {
            error(a.rfind("-", 0) == 0 ? "unknown flag " + a : "unexpected argument " + a);
        }
    }
    if (o.sp_provider != "cpu" && o.sp_provider != "cuda" && o.sp_provider != "dml")
        error("--provider " + o.sp_provider + ": expected cpu, cuda or dml");
    return o;
}
