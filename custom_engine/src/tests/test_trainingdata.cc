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

// Parses + registers the custom 10x10 variant from an inline ini (so self-play
// and tests don't depend on an external variants.ini being loaded).
void run_roundtrip_emit(const std::string& prefix) {
    std::cout << "=== Emitting round-trip ground-truth data ===" << std::endl;
    setup_custom_variant();

    lczero::TrainingDataWriter writer(prefix + "_records.gz");
    std::ofstream dense_out(prefix + "_dense.bin", std::ios::binary);
    if (!dense_out) { std::cerr << "[FAIL] cannot open dense output" << std::endl; std::exit(1); }
    int num_cases = 0;

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

    writer.Finalize();
    dense_out.close();
    std::cout << "[roundtrip] Emitted " << num_cases << " cases -> "
              << prefix << "_records.gz / " << prefix << "_dense.bin" << std::endl;
}
