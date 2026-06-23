/// Kết quả ván cờ engine trả về (khớp lệnh `result` của engine).
enum GameResult { undecided, white, black, draw }

/// Giao diện trừu tượng tới "bộ não" engine.
///
/// Tách khỏi cách hiện thực để: (1) desktop dùng [EngineService] qua tiến trình
/// con UCI ([UciProcessEngine]); (2) Android (Giai đoạn 2) dùng cùng giao diện
/// nhưng gọi thư viện native qua dart:ffi. Toàn bộ lớp UI/điều phối chỉ phụ
/// thuộc interface này, nên đổi nền tảng không phải sửa phần còn lại.
abstract class EngineService {
  /// Khởi động engine + handshake (uci/isready). Gọi một lần lúc mở app.
  Future<void> start();

  /// Bắt đầu ván mới: reset về [fen] (null = startpos mặc định của biến thể).
  Future<void> newGame({String? fen});

  /// Áp một nước (UCI thật, vd "b3b5", "f1i1", "f2f1h") vào lịch sử và đẩy
  /// thế cờ mới cho engine.
  Future<void> applyMove(String uci);

  /// Danh sách nước hợp lệ ở thế hiện tại (UCI thật).
  Future<List<String>> legalMoves();

  /// FEN một dòng của thế hiện tại (để GUI vẽ bàn).
  Future<String> currentFen();

  /// Kết quả ván ở thế hiện tại.
  Future<GameResult> gameResult();

  /// Cho engine nghĩ và trả về nước tốt nhất (UCI thật). Dùng từ M4.
  Future<String> bestMove();

  /// Dừng + giải phóng tiến trình engine.
  Future<void> dispose();
}
