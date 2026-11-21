import '../engine/engine_service.dart' show GameResult;
import 'board_state.dart';

/// Vì sao một ván kết thúc. Cùng thứ tự kiểm với `PositionHistory::ComputeGameResult`
/// (custom_engine/src/lczero_chess/chess/position.cc) và `ly_do()` của
/// custom_engine/python/xem_du_lieu.py: 7 lần chiếu, luật 50 nước, lặp thế, hết nước đi.
enum EndReason {
  /// Một bên đã chiếu đủ 7 lần (số chiếu còn lại về 0).
  checks,

  /// Bên tới lượt không còn nước đi hợp lệ: bên đó THUA (dù bị chiếu hay không).
  noMoves,

  /// 100 nửa nước không ăn quân / không đi Tốt hay Sergeant / không phong cấp: hoà.
  rule50,

  /// Lặp thế 3 lần: hoà.
  repetition,

  /// Theo luật chưa phân thắng bại (ván bị cắt vì quá dài, hoặc chấp thua).
  unfinished,

  /// Không suy ra được (không nên xảy ra).
  unknown,
}

class GameEnd {
  final GameResult result;
  final EndReason reason;
  final int whitePieces;
  final int blackPieces;

  const GameEnd(this.result, this.reason, this.whitePieces, this.blackPieces);

  int get pieces => whitePieces + blackPieces;

  /// Suy ra từ FEN cuối ván, kết quả engine báo và số nước hợp lệ ở thế đó.
  factory GameEnd.of(String fen, GameResult result, int legalMoveCount) {
    final board = BoardState.fromFen(fen);
    final (white, black) = board.pieceCounts();
    final parts = fen.trim().split(RegExp(r'\s+'));
    final halfmove = parts.length > 5 ? int.tryParse(parts[5]) ?? 0 : 0;
    EndReason reason;
    if (result == GameResult.undecided) {
      reason = EndReason.unfinished;
    } else if ((board.checksWhite ?? 1) <= 0 || (board.checksBlack ?? 1) <= 0) {
      reason = EndReason.checks;
    } else if (halfmove >= 100) {
      reason = result == GameResult.draw ? EndReason.rule50 : EndReason.noMoves;
    } else if (result == GameResult.draw) {
      reason = EndReason.repetition;
    } else if (legalMoveCount == 0) {
      reason = EndReason.noMoves;
    } else {
      reason = EndReason.unknown;
    }
    return GameEnd(result, reason, white, black);
  }

  /// Lý do bằng chữ (có nói bên nào thắng / thua khi cần).
  String get reasonText {
    final winner = result == GameResult.white ? 'Trắng' : 'Đen';
    final loser = result == GameResult.white ? 'Đen' : 'Trắng';
    switch (reason) {
      case EndReason.checks:
        return '$winner đủ 7 lần chiếu';
      case EndReason.noMoves:
        return '$loser hết nước đi (thua)';
      case EndReason.rule50:
        return 'luật 50 nước';
      case EndReason.repetition:
        return 'lặp thế 3 lần';
      case EndReason.unfinished:
        return 'ván bị cắt / chấp thua (chưa phân thắng bại theo luật)';
      case EndReason.unknown:
        return 'không rõ lý do';
    }
  }
}
