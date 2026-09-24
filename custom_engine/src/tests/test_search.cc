// MCTS search integration and self-play extraction tests:
//   --test-mcts, --test-extract, --test-selfplay.

#include "tests/test_common.h"

void run_mcts_tests(const std::string& weights_path) {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING MCTS INTEGRATION TESTS..." << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "Weights path: " << weights_path << std::endl;

    // Load custom variant
    setup_custom_variant();   // the real definition, not a copy

    // 1. Dựng thế cờ 10x10 variant
    std::string fen = "vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi - 8+8 0 1";
    lczero::ChessBoard board(fen);
    
    // 2. Setup options
    lczero::OptionsParser parser;
    lczero::classic::SearchParams::Populate(&parser);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
    
    // Kích hoạt Nhiễu Dirichlet và Nhiệt độ cực đại để tạo ngẫu nhiên tuyệt đối
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 1.0f);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, 0.3f);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kTemperatureId, 10.0f);
    parser.GetMutableDefaultsOptions()->Set<int>(lczero::classic::BaseSearchParams::kTempDecayMovesId, 15);
    
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_path);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "threads=4,inter_op_threads=2");
    const lczero::OptionsDict& options = parser.GetOptionsDict();
    
    std::unique_ptr<lczero::Backend> backend;
    try {
        auto raw_backend = std::make_unique<lczero::OnnxBackend>();
        raw_backend->UpdateConfiguration(options);
        backend = lczero::CreateMemCache(std::move(raw_backend), options);
        std::cout << "[MCTS TEST] Loaded OnnxBackend successfully." << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[MCTS TEST] Error loading OnnxBackend: " << e.what() << std::endl;
        std::cerr << "[MCTS TEST] Falling back to MockBackend!" << std::endl;
        backend = std::make_unique<MockBackend>();
    }

    std::cout << "Starting 5 MCTS test runs (800 playouts) with 100% Noise & Temp=10.0..." << std::endl;
    std::cout << "RNG Test: " << lczero::Random::Get().GetFloat(1.0f) << ", " 
              << lczero::Random::Get().GetFloat(1.0f) << ", " 
              << lczero::Random::Get().GetFloat(1.0f) << std::endl;
    
    std::vector<std::string> best_moves;
    for (int run = 1; run <= 5; ++run) {
        auto tree = std::make_unique<lczero::classic::NodeTree>();
        tree->ResetToPosition(fen, {}); // set to FEN
        
        auto uci_responder = std::make_unique<TestUciResponder>();
        auto stopper = std::make_unique<NodeLimitStopper>(800); // Stop after 800 nodes
        auto start_time = std::chrono::steady_clock::now();
        
        auto search = std::make_unique<lczero::classic::Search>(
            *tree,
            backend.get(),
            std::move(uci_responder),
            lczero::MoveList{},
            start_time,
            std::move(stopper),
            false, // infinite
            false, // ponder
            options,
            nullptr // syzygy_tb
        );
        
        search->RunBlocking(4); // Run search on 4 threads
        
        auto result = search->GetBestMove();
        best_moves.push_back(result.first.ToString());
        std::cout << "[RUN " << run << "] Finished playouts: " << search->GetTotalPlayouts() 
                  << " | Best move: " << result.first.ToString() << " (RNG: " << lczero::Random::Get().GetFloat(1.0f) << ")" << std::endl;
    }

    std::cout << "\n=== MCTS RANDOMNESS TEST RESULTS ===" << std::endl;
    for (size_t i = 0; i < best_moves.size(); ++i) {
        std::cout << "Run " << (i + 1) << ": " << best_moves[i] << std::endl;
    }
    std::cout << "====================================" << std::endl;
}

// T2: extract pi (from visits) + policy_kld (from raw NN prior) + z (parity).
// Plays a short game and verifies: sum(pi) == 1.0, policy_kld finite & >= 0,
// and z assigned with correct side-to-move parity.
void run_extract_tests(const std::string& weights_path) {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING T2 (EXTRACT pi / policy_kld / z) TESTS..." << std::endl;
    std::cout << "========================================\n" << std::endl;

    setup_custom_variant();   // the real definition, not a copy

    std::string fen = "vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi - 8+8 0 1";

    lczero::OptionsParser parser;
    lczero::classic::SearchParams::Populate(&parser);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.25f);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, 0.3f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_path);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "threads=2");
    const lczero::OptionsDict& options = parser.GetOptionsDict();

    std::unique_ptr<lczero::Backend> backend;
    bool has_cache = true;
    try {
        auto raw_backend = std::make_unique<lczero::OnnxBackend>();
        raw_backend->UpdateConfiguration(options);
        backend = lczero::CreateMemCache(std::move(raw_backend), options);
        std::cout << "[T2] OnnxBackend + MemCache loaded." << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[T2] OnnxBackend failed (" << e.what()
                  << "); using MockBackend (no cache, kld=0)." << std::endl;
        backend = std::make_unique<MockBackend>();
        has_cache = false;
    }

    auto tree = std::make_unique<lczero::classic::NodeTree>();
    tree->ResetToPosition(fen, {});

    std::vector<lczero::TrainingDataV1> records;
    std::vector<bool> stm_black;
    const int kMaxMoves = 6;
    const int kVisits = 64;
    lczero::GameResult final_result = lczero::GameResult::UNDECIDED;

    for (int m = 0; m < kMaxMoves; ++m) {
        auto responder = std::make_unique<SilentUciResponder>();
        auto stopper = std::make_unique<NodeLimitStopper>(kVisits);
        auto start = std::chrono::steady_clock::now();
        auto search = std::make_unique<lczero::classic::Search>(
            *tree, backend.get(), std::move(responder), lczero::MoveList{},
            start, std::move(stopper), false, false, options, nullptr);
        search->RunBlocking(2);

        lczero::classic::Node* root = tree->GetCurrentHead();
        lczero::TrainingDataV1 rec;
        std::memset(&rec, 0, sizeof(rec));
        rec.version = lczero::kTrainingDataVersion;
        rec.input_format = lczero::kInputFormat10x10;
        bool black = tree->IsBlackToMove();
        rec.side_to_move = black ? 1 : 0;

        lczero::Move best = lczero::FillSearchTargets(
            root, tree->GetPositionHistory(), backend.get(), rec);

        double sum = 0.0;  // sum over LEGAL-visited moves (pi<0 = illegal sentinel)
        for (int i = 0; i < lczero::kPolicySize; ++i)
            if (rec.probabilities[i] > 0.0f) sum += rec.probabilities[i];
        if (std::abs(sum - 1.0) > 1e-3) {
            std::cerr << "[FAIL] move " << m << ": sum(pi) = " << sum
                      << " (expected 1.0)" << std::endl;
            std::exit(1);
        }
        if (!std::isfinite(rec.policy_kld) || rec.policy_kld < -1e-6f) {
            std::cerr << "[FAIL] move " << m << ": invalid policy_kld = "
                      << rec.policy_kld << std::endl;
            std::exit(1);
        }
        std::cout << "  move " << m << " (" << (black ? "black" : "white")
                  << "): sum(pi)=" << sum << " visits=" << rec.visits
                  << " root_q=" << rec.root_q << " best_q=" << rec.best_q
                  << " orig_q=" << rec.orig_q << " kld=" << rec.policy_kld
                  << std::endl;

        records.push_back(rec);
        stm_black.push_back(black);

        tree->MakeMove(best);
        lczero::GameResult r = tree->GetPositionHistory().ComputeGameResult();
        if (r != lczero::GameResult::UNDECIDED) { final_result = r; break; }
    }

    if (records.empty()) { std::cerr << "[FAIL] no records produced!" << std::endl; std::exit(1); }
    std::cout << "[PASS] sum(pi)==1.0 and policy_kld valid for all "
              << records.size() << " positions." << std::endl;
    if (has_cache) {
        bool any_positive = false;
        for (const auto& r : records) if (r.policy_kld > 0.0f) any_positive = true;
        std::cout << (any_positive
            ? "  policy_kld > 0 observed (search diverged from raw NN prior). OK."
            : "  [WARN] all policy_kld == 0 (possible cache miss).") << std::endl;
    }

    // z parity: use the real outcome if the game ended, else inject WHITE_WON
    // purely to exercise AssignResult's parity logic.
    lczero::GameResult test_result =
        (final_result != lczero::GameResult::UNDECIDED) ? final_result
                                                        : lczero::GameResult::WHITE_WON;
    std::cout << "  Assigning z with result=" << (int)test_result
              << (final_result == lczero::GameResult::UNDECIDED
                      ? " (injected for parity test)" : " (actual game result)")
              << std::endl;
    for (size_t i = 0; i < records.size(); ++i)
        lczero::AssignResult(records[i], test_result, stm_black[i]);

    for (size_t i = 0; i < records.size(); ++i) {
        const float q = records[i].result_q, d = records[i].result_d;
        if (test_result == lczero::GameResult::DRAW) {
            if (q != 0.0f || d != 1.0f) {
                std::cerr << "[FAIL] draw z wrong at " << i << std::endl; std::exit(1);
            }
        } else {
            const bool white_won = (test_result == lczero::GameResult::WHITE_WON);
            const bool stm_white = !stm_black[i];
            const float expected = (white_won == stm_white) ? 1.0f : -1.0f;
            if (q != expected || d != 0.0f) {
                std::cerr << "[FAIL] z parity wrong at " << i << ": stm_black="
                          << stm_black[i] << " got q=" << q << " expected " << expected << std::endl;
                std::exit(1);
            }
        }
    }
    std::cout << "[PASS] z parity correct for all positions." << std::endl;

    std::cout << "\n========================================" << std::endl;
    std::cout << "ALL T2 (EXTRACT) TESTS PASSED!" << std::endl;
    std::cout << "========================================\n" << std::endl;
}

// T3: full self-play game -> writes all positions to a .gz, then verifies the
// file round-trips with a result assigned to every record.
void run_selfplay_tests(const std::string& weights_path) {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING T3 (SELF-PLAY 1 GAME) TESTS..." << std::endl;
    std::cout << "========================================\n" << std::endl;

    setup_custom_variant();   // the real definition, not a copy

    std::string fen = "vrhbqkberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV w BIbi - 8+8 0 1";

    lczero::OptionsParser parser;
    lczero::classic::SearchParams::Populate(&parser);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kHistoryFill, "no");
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseEpsilonId, 0.25f);
    parser.GetMutableDefaultsOptions()->Set<float>(lczero::classic::BaseSearchParams::kNoiseAlphaId, 0.3f);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_path);
    parser.GetMutableDefaultsOptions()->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "threads=2");
    const lczero::OptionsDict& options = parser.GetOptionsDict();

    std::unique_ptr<lczero::Backend> backend;
    try {
        auto raw_backend = std::make_unique<lczero::OnnxBackend>();
        raw_backend->UpdateConfiguration(options);
        backend = lczero::CreateMemCache(std::move(raw_backend), options);
        std::cout << "[T3] OnnxBackend + MemCache loaded." << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "[T3] OnnxBackend failed (" << e.what()
                  << "); using MockBackend." << std::endl;
        backend = std::make_unique<MockBackend>();
    }

    const std::string out_file =
        std::string("test_selfplay_game") + lczero::TrainingDataWriter::Extension();

    std::cout << "Playing 1 game (visits=32, max_moves=30, temp_cutoff_ply=8)..." << std::endl;
    lczero::GameResult result = lczero::PlayOneGame(
        fen, backend.get(), options, /*visits=*/32, /*max_moves=*/30,
        /*temp_cutoff_ply=*/8, out_file, /*search_threads=*/2);
    std::cout << "Game finished: result=" << (int)result << ", file=" << out_file << std::endl;

    // --- Verify the file round-trips and every record is valid ---
    std::vector<lczero::TrainingDataV1> recs;
    if (!lczero::ReadTrainingData(out_file, recs)) {
        std::cerr << "[FAIL] Could not read back " << out_file << std::endl; std::exit(1);
    }
    if (recs.empty()) { std::cerr << "[FAIL] No records in file!" << std::endl; std::exit(1); }

    for (size_t i = 0; i < recs.size(); ++i) {
        const auto& r = recs[i];
        if (r.version != lczero::kTrainingDataVersion ||
            r.input_format != lczero::kInputFormat10x10) {
            std::cerr << "[FAIL] rec " << i << ": bad version/input_format" << std::endl; std::exit(1);
        }
        double sum = 0.0;  // sum over LEGAL-visited moves (pi<0 = illegal sentinel)
        for (int k = 0; k < lczero::kPolicySize; ++k)
            if (r.probabilities[k] > 0.0f) sum += r.probabilities[k];
        if (std::abs(sum - 1.0) > 1e-3) {
            std::cerr << "[FAIL] rec " << i << ": sum(pi)=" << sum << std::endl; std::exit(1);
        }
        const bool z_draw = (r.result_d == 1.0f && r.result_q == 0.0f);
        const bool z_decisive = (r.result_d == 0.0f && (r.result_q == 1.0f || r.result_q == -1.0f));
        if (!z_draw && !z_decisive) {
            std::cerr << "[FAIL] rec " << i << ": z not assigned (q=" << r.result_q
                      << " d=" << r.result_d << ")" << std::endl; std::exit(1);
        }
    }

    // The first (startpos) record must have non-empty piece planes (pieces exist).
    bool any_plane = false;
    for (int p = 0; p < 26; ++p)
        if (recs[0].piece_planes[p][0] != 0 || recs[0].piece_planes[p][1] != 0) any_plane = true;
    if (!any_plane) {
        std::cerr << "[FAIL] startpos record has all-empty piece planes!" << std::endl; std::exit(1);
    }

    std::cout << "  Records written/read: " << recs.size()
              << " | side_to_move[0]=" << (int)recs[0].side_to_move
              << " rule50[0]=" << (int)recs[0].rule50_count
              << " checks_us[0]=" << (int)recs[0].checks_remaining_us
              << " castle_us_oo_sq[0]=" << (int)recs[0].castling_us_oo_sq
              << std::endl;
    std::cout << "[PASS] All " << recs.size()
              << " records valid (pi=1, z assigned, planes non-empty)." << std::endl;

    std::remove(out_file.c_str());

    std::cout << "\n========================================" << std::endl;
    std::cout << "ALL T3 (SELF-PLAY) TESTS PASSED!" << std::endl;
    std::cout << "========================================\n" << std::endl;
}
