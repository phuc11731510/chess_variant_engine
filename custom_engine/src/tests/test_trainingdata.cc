// Training-data record layout / writer / reader tests:
//   --test-trainingdata, --emit-roundtrip.

#include "tests/test_common.h"

// Fills every byte of a record with a deterministic, record-specific pattern so
// the round-trip compares all 45940 bytes (not just a few named fields).
static void fill_deterministic(lczero::TrainingDataV1& rec, int seed) {
    auto* bytes = reinterpret_cast<uint8_t*>(&rec);
    for (size_t k = 0; k < sizeof(rec); ++k) {
        bytes[k] = static_cast<uint8_t>((seed * 131 + static_cast<int>(k) * 7 + 17) & 0xFF);
    }
    // Set a couple of named fields to sane values for human-readable sanity.
    rec.version = lczero::kTrainingDataVersion;
    rec.input_format = lczero::kInputFormat10x10;
}

// T1: verify TrainingDataV1 layout (45940 bytes) and Writer/Reader round-trip.
void run_trainingdata_tests() {
    std::cout << "\n========================================" << std::endl;
    std::cout << "RUNNING TRAINING DATA (T1) TESTS..." << std::endl;
    std::cout << "========================================\n" << std::endl;

    // TEST 1: struct layout size is locked at 45940 bytes.
    std::cout << "TEST 1: sizeof(TrainingDataV1) = " << sizeof(lczero::TrainingDataV1)
              << " (expected 45940)" << std::endl;
    if (sizeof(lczero::TrainingDataV1) != 45940) {
        std::cerr << "[FAIL] Unexpected struct size!" << std::endl;
        std::exit(1);
    }
    std::cout << "[PASS] TEST 1: layout size correct.\n" << std::endl;

    // TEST 2: write N records, read them back, compare bit-for-bit.
    std::cout << "TEST 2: Writer/Reader round-trip (bit-exact)..." << std::endl;
    const int kNumRecords = 5;
    std::vector<lczero::TrainingDataV1> originals(kNumRecords);
    for (int n = 0; n < kNumRecords; ++n) fill_deterministic(originals[n], n + 1);

    std::string fname =
        std::string("test_trainingdata_t1") + lczero::TrainingDataWriter::Extension();

    {
        lczero::TrainingDataWriter writer(fname);
        if (!writer.IsOpen()) {
            std::cerr << "[FAIL] Could not open output file: " << fname << std::endl;
            std::exit(1);
        }
        for (const auto& r : originals) writer.WriteChunk(r);
        writer.Finalize();
    }
    std::cout << "  - Wrote " << kNumRecords << " records to " << fname << std::endl;

    std::vector<lczero::TrainingDataV1> readback;
    if (!lczero::ReadTrainingData(fname, readback)) {
        std::cerr << "[FAIL] ReadTrainingData failed (open or truncated)!" << std::endl;
        std::exit(1);
    }
    if (readback.size() != originals.size()) {
        std::cerr << "[FAIL] Record count mismatch: wrote " << originals.size()
                  << ", read " << readback.size() << std::endl;
        std::exit(1);
    }
    for (int n = 0; n < kNumRecords; ++n) {
        if (std::memcmp(&originals[n], &readback[n], sizeof(lczero::TrainingDataV1)) != 0) {
            std::cerr << "[FAIL] Record " << n << " differs after round-trip!" << std::endl;
            std::exit(1);
        }
    }
    std::remove(fname.c_str());
    std::cout << "  - Read back " << readback.size()
              << " records, all bytes match." << std::endl;
    std::cout << "[PASS] TEST 2: round-trip bit-exact.\n" << std::endl;

    std::cout << "========================================" << std::endl;
    std::cout << "ALL TRAINING DATA (T1) TESTS PASSED!" << std::endl;
    std::cout << "========================================\n" << std::endl;
}

// --emit-roundtrip: ground truth for python/test_roundtrip.py. For each case
// writes BOTH <prefix>_records.gz (TrainingDataV1 records) and <prefix>_dense.bin
// (the [226*100] floats UnpackInputPlanes gives the NN for the SAME position);
// Python rebuilds the planes from the record and compares. With --weights it also
// writes <prefix>_eval.bin for python/test_engine_parity.py (eval_backend below).
void run_roundtrip_emit(const std::string& prefix, const std::string& weights_path) {
    std::cout << "=== Emitting round-trip ground-truth data ===" << std::endl;
    setup_custom_variant();

    lczero::TrainingDataWriter writer(prefix + "_records.gz");
    std::ofstream dense_out(prefix + "_dense.bin", std::ios::binary);
    if (!dense_out) { std::cerr << "[FAIL] cannot open dense output" << std::endl; std::exit(1); }
    int num_cases = 0;

    // With --weights: also what the ENGINE's backend stack (NN cache over the
    // ONNX backend, policy temperature 1, as in self-play) says about each case,
    // for python/test_engine_parity.py. Per case, little-endian:
    //   float q, float d, uint32 n, then n x (uint16 policy index, float prior)
    // over the legal moves in generation order.
    std::unique_ptr<lczero::Backend> eval_backend;
    std::ofstream eval_out;
    lczero::OptionsParser eval_parser;
    if (!weights_path.empty()) {
        auto* d = eval_parser.GetMutableDefaultsOptions();
        d->Set<std::string>(lczero::SharedBackendParams::kWeightsId, weights_path);
        d->Set<std::string>(lczero::SharedBackendParams::kBackendOptionsId, "threads=1");
        d->Set<float>(lczero::SharedBackendParams::kPolicySoftmaxTemp, 1.0f);
        eval_backend = lczero::CreateMemCache(
            [&] {
                auto b = std::make_unique<lczero::OnnxBackend>();
                b->UpdateConfiguration(eval_parser.GetOptionsDict());
                return b;
            }(),
            eval_parser.GetOptionsDict());
        eval_out.open(prefix + "_eval.bin", std::ios::binary);
        if (!eval_out) { std::cerr << "[FAIL] cannot open eval output" << std::endl; std::exit(1); }
    }

    auto emit = [&](const lczero::PositionHistory& h) {
        lczero::InputPlanes planes;
        int t = 0;
        lczero::EncodePositionForNN(h, lczero::kMoveHistory,
                                    lczero::FillEmptyHistory::FEN_ONLY, &planes, &t);
        std::vector<float> dense(226 * 100, 0.0f);
        lczero::UnpackInputPlanes(planes, dense.data(), 10, 10);
        dense_out.write(reinterpret_cast<const char*>(dense.data()),
                        dense.size() * sizeof(float));

        lczero::TrainingDataV1 rec;
        std::memset(&rec, 0, sizeof(rec));
        rec.version = lczero::kTrainingDataVersion;
        rec.input_format = lczero::kInputFormat10x10;
        lczero::EncodePlanesIntoRecord(h, rec);
        // Synthetic scalar/policy fields to verify field-level unpack in Python.
        rec.probabilities[100] = 0.25f;
        rec.probabilities[2005] = 0.75f;
        rec.result_q = -1.0f; rec.result_d = 0.0f;
        rec.root_q = 0.1f; rec.best_q = 0.5f; rec.orig_q = 0.123f;
        rec.policy_kld = 0.456f; rec.visits = 777;
        rec.played_idx = 2005; rec.best_idx = 2005;
        writer.WriteChunk(rec);
        ++num_cases;

        if (eval_backend) {
            const lczero::MoveList legal = h.Last().GetBoard().GenerateLegalMoves();
            lczero::EvalResult r;
            r.p.resize(legal.size());
            auto comp = eval_backend->CreateComputation();
            comp->AddInput(lczero::EvalPosition{&h, std::span<const lczero::Move>(legal.data(), legal.size())},
                           r.AsPtr());
            comp->ComputeBlocking();
            const uint32_t n = static_cast<uint32_t>(legal.size());
            eval_out.write(reinterpret_cast<const char*>(&r.q), 4);
            eval_out.write(reinterpret_cast<const char*>(&r.d), 4);
            eval_out.write(reinterpret_cast<const char*>(&n), 4);
            for (uint32_t i = 0; i < n; ++i) {
                const uint16_t idx = lczero::MoveToNNIndex(legal[i], 0);
                eval_out.write(reinterpret_cast<const char*>(&idx), 2);
                eval_out.write(reinterpret_cast<const char*>(&r.p[i]), 4);
            }
        }
    };

    // Case 0: startpos (white to move, castling BIbi, checks 8+8, no ep).
    {
        auto board = std::make_unique<lczero::ChessBoard>();
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(*board, 0, 1);
        emit(*h);
    }
    // Case 1: black to move with an active Sergeant en-passant (no castling).
    {
        auto board = std::make_unique<lczero::ChessBoard>(
            std::string("5k4/10/10/10/10/1s8/10/S9/10/5K4 w - - 8+8 0 1"));
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(*board, 0, 1);
        lczero::Move m = board->ParseMove("a3c5");
        if (!m.is_null()) h->Append(m);
        emit(*h);
    }
    // Case 2: position after several moves -> populates HISTORY plies 1-7.
    // This exercises the LightweightPosition board snapshot + per-ply flip path
    // (which T5's startpos/ep cases barely touched).
    {
        auto board = std::make_unique<lczero::ChessBoard>();
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(*board, 0, 1);
        for (int k = 0; k < 7; ++k) {
            lczero::MoveList lm = h->Last().GenerateLegalMoves();
            if (lm.empty()) break;
            h->Append(lm[0]);  // deterministic: first legal move
        }
        emit(*h);
    }

    // Cases 3+: positions from random games and a repetition sequence, so the
    // Python reconstruction is checked over the whole range of every aux field
    // (Black to move, castling rights lost one by one, a Sergeant's two e.p.
    // squares, rule50 > 0, checks < 8) and over set repetition planes in several
    // history plies -- not just three hand-picked boards.
    {
        std::mt19937_64 rng(0x5EED0DA7AULL);
        const char* fens[] = {
            lczero::ChessBoard::kStartposFen,
            "1r3k2r1/2p4p2/10/4n5/10/10/5B4/10/2P4P2/1R3K2R1 w BIbi - 8+8 0 1",
            "4k5/3s1s4/10/2P1S1P3/10/10/10/10/10/4K5 b - - 8+8 0 1",
        };
        for (const char* fen : fens) {
            for (int game = 0; game < 4; ++game) {
                auto h = std::make_unique<lczero::PositionHistory>();
                h->Reset(lczero::Position::FromFen(fen));
                for (int ply = 0; ply < 60; ++ply) {
                    const lczero::MoveList lm = h->Last().GenerateLegalMoves();
                    if (lm.empty() || h->ComputeGameResult() != lczero::GameResult::UNDECIDED) break;
                    if (ply % 7 == 3) emit(*h);
                    h->Append(lm[static_cast<size_t>(rng() % lm.size())]);
                }
            }
        }
        auto h = std::make_unique<lczero::PositionHistory>();
        h->Reset(lczero::Position::FromFen("n3k5/10/10/10/10/10/10/10/10/4K4N w - - 8+8 30 20"));
        for (const char* uci : {"j1i3", "a10b8", "i3j1", "b8a10", "j1i3", "a10b8", "i3j1"}) {
            const lczero::Move m = fztest::ParseLegalMove(*h, uci);
            if (m.is_null()) { std::cerr << "[FAIL] roundtrip setup: " << uci << std::endl; std::exit(1); }
            h->Append(m);
            emit(*h);   // from the 4th move on the current board is a repetition
        }
    }

    writer.Finalize();
    dense_out.close();
    std::cout << "[roundtrip] Emitted " << num_cases << " cases -> "
              << prefix << "_records.gz / " << prefix << "_dense.bin" << std::endl;
    if (eval_backend) {
        eval_out.close();
        std::cout << "[roundtrip] engine evaluations (" << weights_path << ") -> " << prefix
                  << "_eval.bin" << std::endl;
    }
}
