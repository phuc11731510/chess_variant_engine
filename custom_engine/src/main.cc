#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <cassert>

#include "bitboard.h"
#include "endgame.h"
#include "position.h"
#include "psqt.h"
#include "search.h"
#include "syzygy/tbprobe.h"
#include "thread.h"
#include "tt.h"
#include "uci.h"
#include "piece.h"
#include "variant.h"
#include "xboard.h"
#include "movegen.h"
#include "chess/board.h"
#include "chess/position.h"
#include "chess/gamestate.h"
#include "chess/encoder.h"
#include "trainingdata/trainingdata_v1.h"
#include "trainingdata/writer.h"
#include "selfplay/training_extract.h"
#include "selfplay/selfplay_game.h"
#include "selfplay/selfplay_driver.h"
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <cstdio>
#include <cmath>
#include <thread>
#include <atomic>
#include <mutex>
#include <chrono>
#include <memory>
#include <map>
#include <functional>
#include <algorithm>
#include "search/classic/search.h"
#include "search/classic/params.h"
#include "neural/backend.h"
#include "neural/shared_params.h"
#include "neural/onnx_backend.h"
#include "neural/zero_heap_cache.h"
#include "utils/random.h"
#include "chess/callbacks.h"
#include "app/cli.h"
#include "app/arena_mode.h"
#include "app/uci_nn_engine.h"
#include "app/play_mode.h"
#include "app/selfplay_mode.h"
#include "tests/engine_tests.h"

using namespace Stockfish;

int main(int argc, char* argv[]) {
    EngineOptions o = parse_cli(argc, argv);

    std::cout << engine_info() << " (Custom Variant Engine)" << std::endl;

    pieceMap.init();
    variants.init();
    CommandLine::init(argc, argv);
    UCI::init(Options);
    Tune::init();
    PSQT::init(variants.find(Options["UCI_Variant"])->second);
    Bitboards::init();
    Position::init();
    Bitbases::init();
    Endgames::init();
    Threads.set(size_t(Options["Threads"]));
    Search::clear(); // After threads are up
    Eval::NNUE::init();

    if (o.test_ep_mode) {
        run_ep_tests();
    } else if (o.test_board_mode) {
        run_board_tests();
    } else if (o.test_policy_mode) {
        run_policy_tests();
    } else if (o.test_trainingdata_mode) {
        run_trainingdata_tests();
    } else if (o.test_extract_mode) {
        run_extract_tests(o.weights_file);
    } else if (o.test_selfplay_mode) {
        run_selfplay_tests(o.weights_file);
    } else if (o.emit_roundtrip_mode) {
        run_roundtrip_emit(o.rt_prefix);
    } else if (o.test_perft_mode) {
        run_perft_tests();
    } else if (o.test_bits_mode) {
        run_bits_tests();
    } else if (o.test_rules_mode) {
        run_rules_tests();
    } else if (o.test_adapter_mode) {
        run_adapter_tests();
    } else if (o.test_nn_mode) {
        run_nn_tests();
    } else if (o.test_uci_mode) {
        run_uci_tests();
    } else if (o.test_encoder_mode) {
        run_encoder_tests();
    } else if (o.audit_generation_mode) {
        run_audit_generation(o.sp_games, o.sp_max_moves);
    } else if (o.uci_nn_mode) {
        run_uci_nn(o.weights_file, o.sp_provider, o.sp_fixed_batch);
    } else if (o.play_mode) {
        run_play(o.weights_file, o.sp_provider, o.sp_fixed_batch, o.sp_visits, o.play_human_white);
    } else if (o.arena_mode) {
        int rc = run_arena(o);
        if (rc != 0) return rc;
    } else if (o.test_mcts_mode) {
        run_mcts_tests(o.weights_file);
    } else if (o.selfplay_mode) {
        int rc = run_selfplay(o);
        if (rc != 0) return rc;
    } else {
        UCI::loop(argc, argv);
    }

    Threads.set(0);
    variants.clear_all();
    pieceMap.clear_all();
    delete XBoard::stateMachine;
    return 0;
}
