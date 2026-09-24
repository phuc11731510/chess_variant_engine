#pragma once
#include <cstdint>

namespace lczero {

// On-disk training-data record for the 10x10 FairyZero variant.
//
// Adapted from Lc0's V6TrainingData but resized for this project:
//   - policy:  probabilities[10600]  (Lc0 chess uses 1858)  — layout = MoveToNNIndex
//   - planes:  216 history planes (27 planes/ply x 8 ply) stored sparsely as
//              128-bit bitboard masks (2 x uint64); aux planes stored as scalars.
//   - value:   WDL (Win/Draw/Loss) from side-to-move perspective.
//
// IMPORTANT (3 conventions that MUST match the Python reader):
//   1. policy index = MoveToNNIndex (type*100 + from_rank*10 + from_file)
//   2. value order  = [Win, Draw, Loss], side-to-move perspective
//   3. plane order  = encoder order: [ply][27 planes], each plane a 128-bit mask
//      (bit s = rank*12 + file in Stockfish 12-stride coords).
//
// The struct is byte-packed; the static_assert below locks the layout so the
// Python `struct.unpack` format stays in sync (silent corruption guard).

// Version history (the byte layout below has never changed):
//   1: root_q, best_q, played_q were written from the OPPONENT's perspective
//      (a sign error in FillSearchTargets). orig_q was already side-to-move,
//      except when the cache missed and it fell back to best_q.
//   2: all search values are side-to-move (2026-09-23). Readers flip the three
//      fields above for version-1 records (python/dataset.py: search_q()).
//   3: repetitions are detected at every rule-50 count (2026-09-23, same day):
//      before, a repetition was only seen while rule50 < 14, so games in
//      versions 1-2 could go on past a threefold repetition (about 1 game in 4
//      in gen0) and the repetition planes were missing on ~35% of repeated
//      positions. Also from version 3 a double check counts 2 checks (rule
//      fixed by the owner: every checking piece counts; before, 1 per checking
//      move). The layout and every field's meaning are unchanged, so readers
//      need nothing new; the number only tells the data apart.
//   4: orig_q/orig_d/policy_kld are always the root's real raw eval (2026-09-24).
//      Before, when the root's NN-cache entry had been overwritten (8.5% of the
//      gen-0 records), they were a copy of best_q/best_d and 0. Readers treat
//      such a copy in older records as "unknown" (python/dataset.py).
constexpr uint32_t kTrainingDataVersion = 4;
constexpr uint32_t kInputFormat10x10 = 1;

// Sentinel for "no castling right" in the castling-file fields.
constexpr uint8_t kNoCastlingFile = 0xFF;

constexpr int kPolicySize = 10600;     // 106 move types x 100 from-squares
constexpr int kHistoryPlanes = 216;    // 27 planes/ply x 8 ply

#pragma pack(push, 1)
struct TrainingDataV1 {
  uint32_t version;       // = kTrainingDataVersion
  uint32_t input_format;  // = kInputFormat10x10

  // Policy target pi (visit distribution); only legal-move indices are non-zero.
  float probabilities[kPolicySize];  // 10600 * 4 = 42400 bytes

  // 216 history piece-planes as 128-bit bitboard masks ([lo64, hi64] per plane).
  uint64_t piece_planes[kHistoryPlanes][2];  // 216 * 16 = 3456 bytes

  // --- Scalar auxiliary planes (reconstructed by the Python reader) ---
  uint8_t rule50_count;
  // Castling: FILE INDEX (0-9) of the participating rook, or kNoCastlingFile.
  // Storing the file (not a boolean) supports Chess960-style rook placement.
  // Reader sets the bit at: us-planes -> rank 0, them-planes -> rank 9.
  uint8_t castling_us_ooo_file;
  uint8_t castling_us_oo_file;
  uint8_t castling_them_ooo_file;
  uint8_t castling_them_oo_file;
  uint64_t ep_mask[2];  // en-passant plane (128-bit mask)
  uint8_t checks_remaining_us;
  uint8_t checks_remaining_them;
  uint8_t side_to_move;  // 0 = white-to-move frame, 1 = black (already canonical)

  // --- Value / eval targets ---
  // All side-to-move perspective (the three search values only from version 2).
  float result_q, result_d;  // z (game outcome)
  float root_q, root_d;      // search root eval
  float best_q, best_d;      // q (best-move eval after search)
  float played_q, played_d;  // eval of the actually played move

  // --- Fields for diff_focus (Section 8.2.6) ---
  float orig_q, orig_d;  // raw NN eval of the root (un-noised)
  float policy_kld;      // KL(pi_visits || p_nn_raw); before v4 = 0 on a cache miss

  uint32_t visits;     // total root visits
  uint16_t played_idx;  // index into probabilities[] of the played move
  uint16_t best_idx;    // index into probabilities[] of the best move
};
#pragma pack(pop)

// Layout lock: 8 + 42400 + 3456 + 24 + 48 + 4 = 45940.
static_assert(sizeof(TrainingDataV1) == 45940,
              "TrainingDataV1 layout changed; update Python reader + this size.");

}  // namespace lczero
