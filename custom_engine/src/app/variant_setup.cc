#include <iostream>
#include <string>
#include <vector>
#include <sstream>
#include <cassert>
#include <cctype>

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
#include "app/variant_setup.h"


using namespace Stockfish;


// Full Fairy-Stockfish global init — the exact sequence main.cc runs before any
// mode. The Android FFI path (fz_create) has no main(), so it must run this once
// itself; otherwise bitboards/magics/options/threads are uninitialized and the
// engine segfaults at startup. Idempotent.
void init_engine_globals() {
    static std::once_flag once;
    std::call_once(once, [] {
        static const char* kArgv[] = {"fairyzero"};
        pieceMap.init();
        variants.init();
        CommandLine::init(1, const_cast<char**>(kArgv));
        UCI::init(Options);
        Tune::init();
        PSQT::init(variants.find(Options["UCI_Variant"])->second);
        Bitboards::init();
        Position::init();
        Bitbases::init();
        Endgames::init();
        Threads.set(size_t(Options["Threads"]));
        Search::clear();
        Eval::NNUE::init();
    });
}

// The variant's rules and their edge cases are written out in LUAT_BIEN_THE.md,
// and re-implemented independently by src/tests/test_rules_oracle.cc
// (--audit-rules). Two rules are NOT expressible in this INI and live in code:
//   * checkCounting counts every checking piece (a double check = 2 checks):
//     Position::do_move, src/chess/position.cpp;
//   * an e.p. capture that lands in the promotion zone promotes: movegen.cpp +
//     position.cpp (commit 52439cc).
// `k` is the royal piece ("Hoang gia", king step + knight): Fairy-Stockfish
// requires the royal piece to use the king slot.
const Variant* setup_custom_variant() {
    std::string ini_text = R"(
[custom_10x10_variant]
maxRank = 10
maxFile = j
pawn = p
knight = n
bishop = b
rook = r
queen = q
king = k:KN
amazon = a
chancellor = e
archbishop = h
centaur = m
customPiece1 = v:CN
customPiece2 = y:AD
customPiece3 = s:fKifmnDifmnA
pawnTypes = p s
promotionPawnTypes = p s
enPassantTypes = p s
nMoveRuleTypes = p s
doubleStep = true
doubleStepRegionWhite = *1 *2 *3
doubleStepRegionBlack = *10 *9 *8
promotionRegionWhite = *8 *9 *10
promotionRegionBlack = *3 *2 *1
mandatoryPawnPromotion = true
promotionPieceTypes = b m n r v y
castling = true
castlingKingsideFile = h
castlingQueensideFile = d
castlingRookKingsideFile = i
castlingRookQueensideFile = b
stalemateValue = loss
checkCounting = true
)";
    std::istringstream ss(ini_text);
    variants.parse_istream<false>(ss);
    const Variant* v = variants.find("custom_10x10_variant")->second;
    if (!v) {
        std::cerr << "[FATAL] custom_10x10_variant not found!" << std::endl;
        std::exit(1);
    }
    UCI::init_variant(v);
    PSQT::init(v);
    return v;
}

std::string CheckStartFen(const std::string& fen) {
    std::istringstream in(fen);
    std::vector<std::string> field;
    for (std::string t; in >> t;) field.push_back(t);
    // board, side, castling, e.p., checks [, rule50, move number]
    if (field.size() < 5)
        return "expected at least 5 fields (board side castling e.p. checks), got " +
               std::to_string(field.size());
    const std::string& checks = field[4];
    if (!(checks.size() == 3 && checks[1] == '+' && checks[0] >= '1' && checks[0] <= '9' &&
          checks[2] >= '1' && checks[2] <= '9'))
        return "the 5th field must be the checks still needed, like 8+8 (got '" + checks +
               "'); without it Fairy-Stockfish plays 1+1";
    if (field[1] != "w" && field[1] != "b") return "side to move must be w or b";
    // The board syntax first: Fairy-Stockfish skips, without a word, the pieces
    // written past the 10th file of a rank, and a short rank just leaves its last
    // squares empty -- either way a mistyped rank silently changes the position.
    {
        int ranks = 0, squares = 0;
        const std::string& b = field[0];
        for (size_t i = 0; i <= b.size(); ++i) {
            if (i == b.size() || b[i] == '/') {
                if (squares != 10)
                    return "rank " + std::to_string(10 - ranks) + " of the board has " +
                           std::to_string(squares) + " squares, not 10";
                ++ranks;
                squares = 0;
            } else if (std::isdigit(static_cast<unsigned char>(b[i]))) {
                int n = 0;
                while (i < b.size() && std::isdigit(static_cast<unsigned char>(b[i])))
                    n = 10 * n + (b[i++] - '0');
                --i;
                squares += n;
            } else if (std::string("pnbrqkaehmvysPNBRQKAEHMVYS").find(b[i]) != std::string::npos) {
                ++squares;
            } else {
                return std::string("unknown piece letter '") + b[i] + "' in the board";
            }
            if (squares > 10) return "a rank of the board has more than 10 squares";
        }
        if (ranks != 10) return "the board has " + std::to_string(ranks) + " ranks, not 10";
    }

    lczero::ChessBoard board(fen);
    const Stockfish::Position& pos = board.GetRawPosition();
    if (pos.count<Stockfish::KING>(Stockfish::WHITE) != 1 ||
        pos.count<Stockfish::KING>(Stockfish::BLACK) != 1)
        return "each side needs exactly one royal piece (k/K)";
    // What Fairy-Stockfish understood must be what was written. The board and the
    // side to move are compared as text.
    std::istringstream back(pos.fen());
    std::vector<std::string> got;
    for (std::string t; back >> t;) got.push_back(t);
    const char* names[] = {"board", "side to move"};
    for (int i = 0; i < 2; ++i)
        if (got.size() <= static_cast<size_t>(i) || got[i] != field[i])
            return std::string(names[i]) + " read back as '" +
                   (got.size() > static_cast<size_t>(i) ? got[i] : "") + "', not '" + field[i] + "'";
    // Castling rights by MEANING, not spelling. Fairy-Stockfish keeps a right as
    // a (royal square, rook square) pair and writes it back as K/Q/k/q (so the
    // start position's "BIbi" comes back as "KQkq"). Reading, it takes a file
    // letter literally but resolves "K" as the first rook from the i-file towards
    // the a-file and "Q" as the first rook from the b-file towards the j-file:
    // with the rooks elsewhere (a shuffled start) a lone "K" can become a
    // QUEEN-side right with the a-file rook, and a right whose royal piece or
    // rook is not on its square is dropped without a word. So: every letter must
    // give exactly its right (K/Q on that side, a file letter with its rook on
    // that file), and there must be no other right.
    using Stockfish::CastlingRights;
    const int kept = int(pos.can_castle(Stockfish::WHITE_OO)) + int(pos.can_castle(Stockfish::WHITE_OOO)) +
                     int(pos.can_castle(Stockfish::BLACK_OO)) + int(pos.can_castle(Stockfish::BLACK_OOO));
    const int letters = field[2] == "-" ? 0 : static_cast<int>(field[2].size());
    for (int i = 0; i < letters; ++i) {
        const char ch = field[2][i];
        const Stockfish::Color c =
            std::islower(static_cast<unsigned char>(ch)) ? Stockfish::BLACK : Stockfish::WHITE;
        const char up = static_cast<char>(std::toupper(static_cast<unsigned char>(ch)));
        const CastlingRights oo = c & Stockfish::KING_SIDE, ooo = c & Stockfish::QUEEN_SIDE;
        bool ok = false;
        if (up == 'K') {
            ok = pos.can_castle(oo);
        } else if (up == 'Q') {
            ok = pos.can_castle(ooo);
        } else if (up >= 'A' && up <= 'J') {
            for (const CastlingRights cr : {oo, ooo})
                ok = ok || (pos.can_castle(cr) &&
                            Stockfish::file_of(pos.castling_rook_square(cr)) == Stockfish::File(up - 'A'));
        }
        if (!ok)
            return std::string("castling right '") + ch + "' of '" + field[2] +
                   "' was not set up as written (the royal piece and that rook must be on their "
                   "squares; write the rook's file, e.g. BIbi, rather than K/Q)";
    }
    if (kept != letters)
        return "castling rights '" + field[2] + "' gave " + std::to_string(kept) + " right(s), not " +
               std::to_string(letters);
    const Stockfish::Color us = pos.side_to_move();
    if (pos.attackers_to(pos.square<Stockfish::KING>(~us), us))
        return "the side that is not to move is in check";
    if (board.GenerateLegalMoves().empty()) return "no legal move: the game is already over";
    return "";
}
