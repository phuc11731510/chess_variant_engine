#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <sstream>
#include <cassert>
#include <cctype>

#include "chess/encoder.h"
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
// (--audit-rules). Rules that are NOT expressible in this INI live in code:
//   * checkCounting counts every checking piece (a double check = 2 checks):
//     Position::do_move, src/chess/position.cpp; the N of the N-checks rule is the
//     "N+N" of the start FEN;
//   * an e.p. capture that lands in the promotion zone promotes (rank 8: a choice): movegen.cpp +
//     position.cpp;
//   * the two tiers of promotion (optionalPromotionRegion / optionalPromotionPieceTypes, added to this
//     Fairy-Stockfish copy): rank 8 (Black: 3) a pawn or Sergeant may stay or become n y g b c, rank 9
//     (Black: 2) it must become one of the nine.
// `k` is the royal piece ("Hoang gia"): it moves or captures one square in any direction, and in the
// outer ring of the 5x5 around it only MOVES (never captures) where not blocked (Fairy-Stockfish requires
// the royal piece to use the king slot). The other pieces are custom pieces: their NUMBERS are the plane
// order of the network input (lczero_chess/chess/encoder.cc: kPieceKindOrder), so do not renumber them.
// In Betza notation m = move only, n = blocked on the way (for N: Xiangqi horse, blocked on the square
// next to it in the long direction), c = captures only, p = by hopping over exactly one piece, g = by
// hopping over exactly one piece and landing right behind it (the grasshopper).
const Variant* setup_custom_variant() {
    std::string ini_text = R"(
[custom_10x10_variant]
maxRank = 10
maxFile = j
pawn = p
knight = n
bishop = -
rook = r
queen = q
king = k:KmnDmnAmnN
amazon = -
chancellor = -
archbishop = -
centaur = -
customPiece1 = b:BmW
customPiece2 = m:KnN
customPiece3 = v:CN
customPiece4 = y:ADmW
customPiece5 = s:fKifmnDifmnA
customPiece6 = c:mRcpRW
customPiece7 = g:gQK
pawnTypes = p s
promotionPawnTypes = p s
enPassantTypes = p s
nMoveRuleTypes = p s
doubleStep = true
doubleStepRegionWhite = *1 *2 *3
doubleStepRegionBlack = *10 *9 *8
promotionRegionWhite = *8 *9
promotionRegionBlack = *3 *2
optionalPromotionRegionWhite = *8
optionalPromotionRegionBlack = *3
optionalPromotionPieceTypes = n b y c g
mandatoryPawnPromotion = true
promotionPieceTypes = n b r q m v y c g
castling = false
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
    // The network input and policy are laid out for a fixed set of pieces (lczero_chess/chess/nn_layout.h):
    // a piece the encoder does not know would silently vanish from the network input.
    std::string unsupported;
    if (!lczero::EncoderCoversVariant(*v, &unsupported)) {
        std::cerr << "[FATAL] custom_10x10_variant does not fit the encoder: " << unsupported
                  << " (update variant_setup.cc to the new rules, or the encoder)." << std::endl;
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
        return "the 5th field must be the checks still needed, like 7+7 (got '" + checks +
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
            } else if (std::string("pnrqkbmvyscgPNRQKBMVYSCG").find(b[i]) != std::string::npos) {
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
    // No castling in this game: the third field must say so ("-"), whatever Fairy-Stockfish would make of a
    // letter there.
    if (field[2] != "-") return "castling does not exist in this game: the 3rd field must be '-' (got '" + field[2] + "')";
    const Stockfish::Color us = pos.side_to_move();
    if (pos.attackers_to(pos.square<Stockfish::KING>(~us), us))
        return "the side that is not to move is in check";
    if (board.GenerateLegalMoves().empty()) return "no legal move: the game is already over";
    return "";
}

std::string LoadStartFens(const std::string& arg, std::vector<std::string>* book, std::string* single) {
    book->clear();
    auto trim = [](std::string s) {
        const auto b = s.find_first_not_of(" \t\r\n");
        if (b == std::string::npos) return std::string();
        return s.substr(b, s.find_last_not_of(" \t\r\n") - b + 1);
    };
    std::ifstream ff(arg);
    if (ff) {  // an opening book: one FEN per line (# = comment)
        std::string line;
        for (int line_no = 1; std::getline(ff, line); ++line_no) {
            line = trim(line);   // a book saved on Windows ends its lines in \r
            if (line.empty() || line[0] == '#') continue;
            const std::string why = CheckStartFen(line);
            if (!why.empty()) return arg + ":" + std::to_string(line_no) + ": " + why + "\n  " + line;
            book->push_back(line);
        }
        if (book->empty()) return "no FEN in " + arg;
        return "";
    }
    *single = trim(arg);  // a single FEN string
    const std::string why = CheckStartFen(*single);
    if (!why.empty())
        return "--start-fen is neither a readable file nor a valid FEN: " + why + "\n  " + *single;
    return "";
}
