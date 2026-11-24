import '../domain/search_record.dart';

/// Kết quả ván cờ engine trả về (khớp lệnh `result` của engine).
enum GameResult { undecided, white, black, draw }

/// Engine cho biết lần tìm kiếm vừa chọn nước ở [EngineService.bestMove] (các dòng
/// info / RootStats) — để GUI hiện bảng tìm kiếm của từng nước. Chỉ engine tiến trình
/// UCI ở chế độ tự đấu có; GUI hỏi bằng `engine is SearchLogSource`.
abstract interface class SearchLogSource {
  /// Lần tìm của lần gọi [EngineService.bestMove] gần nhất (null nếu không ghi).
  SearchRecord? get lastSearch;
}

/// Engine có thêm một bộ luật dự phòng (Android: `libfzcu.so` = luật trước 2026-11-24, phong cấp hàng 8 là
/// Mã, Tượng, Alibaba, Pháo, Grasshopper). Ván của các đời cũ có nước mà luật mới cấm (phong Tượng / Pháo ở hàng 8),
/// ván mới có nước mà luật cũ cấm (phong Centaur ở hàng 8); hai tập này không giao nhau nên mỗi ván phát lại được
/// bằng đúng một trong hai bộ. GUI hỏi bằng `engine is RuleSetSwitcher`.
abstract interface class RuleSetSwitcher {
  /// Đổi sang bộ luật kia (xoay vòng). False nếu không có bộ luật dự phòng (không đổi gì).
  Future<bool> switchRuleSet();
}

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
