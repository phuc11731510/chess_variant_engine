/// Một quân cờ trên bàn. `letter` giữ nguyên ký tự FEN (HOA = Trắng, thường = Đen).
class Piece {
  final String letter;
  const Piece(this.letter);

  bool get isWhite => letter == letter.toUpperCase();

  /// Ký tự loại quân (luôn thường): p n b r k m a e h y s v.
  String get type => letter.toLowerCase();
}

/// Trạng thái bàn cờ 10×10 dựng TỪ FEN (chỉ dùng trường bố trí quân để vẽ).
///
/// Lưới: `cells[r][f]`, với r=0..9 là HÀNG 1..10 (r=0 là hàng 1 = đáy Trắng),
/// f=0..9 là CỘT a..j. Đây là toạ độ BÀN CỜ (không phụ thuộc hướng hiển thị).
class BoardState {
  final List<List<Piece?>> cells;

  /// checksRemaining đọc trực tiếp từ FEN ("A+B"): A=[WHITE], B=[BLACK] — số nước
  /// CHIẾU mỗi bên còn phải THỰC HIỆN để thắng. null nếu FEN không có trường này.
  final int? checksWhite;
  final int? checksBlack;

  /// Bên đi: true = Trắng (đọc từ FEN token 2). Dùng để biết tới lượt ai.
  final bool whiteToMove;

  const BoardState(this.cells,
      {this.checksWhite, this.checksBlack, this.whiteToMove = true});

  /// Số lần vua TRẮNG còn có thể BỊ CHIẾU trước khi THUA = checksRemaining[BLACK]
  /// (Đen thắng khi dùng hết số chiếu của mình). Hiển thị trên mặt vua Trắng.
  int? get whiteRoyalChecks => checksBlack;

  /// Tương tự cho vua ĐEN = checksRemaining[WHITE].
  int? get blackRoyalChecks => checksWhite;

  Piece? at(int r, int f) =>
      (r >= 0 && r < 10 && f >= 0 && f < 10) ? cells[r][f] : null;

  /// Parse FEN (đầy đủ hoặc chỉ trường bố trí quân). FEN liệt kê hàng 10 → hàng 1.
  /// Chuỗi rỗng/số: số ô trống (xử lý cả số hai chữ số "10").
  factory BoardState.fromFen(String fen) {
    final placement = fen.trim().split(RegExp(r'\s+')).first;
    final rows = placement.split('/');
    final cells =
        List.generate(10, (_) => List<Piece?>.filled(10, null), growable: false);

    for (int i = 0; i < rows.length && i < 10; i++) {
      // rows[0] = hàng 10 (đỉnh) ... rows[9] = hàng 1 (đáy) -> r = 9 - i.
      final r = 9 - i;
      final s = rows[i];
      int f = 0;
      int k = 0;
      while (k < s.length && f < 10) {
        final code = s.codeUnitAt(k);
        if (code >= 48 && code <= 57) {
          // đọc trọn số (gộp các chữ số liên tiếp -> hỗ trợ "10")
          int num = 0;
          while (k < s.length && s.codeUnitAt(k) >= 48 && s.codeUnitAt(k) <= 57) {
            num = num * 10 + (s.codeUnitAt(k) - 48);
            k++;
          }
          f += num;
        } else {
          cells[r][f] = Piece(s[k]);
          f++;
          k++;
        }
      }
    }
    final parts = fen.trim().split(RegExp(r'\s+'));
    final whiteToMove = !(parts.length > 1 && parts[1] == 'b');

    // Trường check-counting "A+B" (nếu có) — tìm token dạng số+số.
    int? cw, cb;
    for (final t in parts) {
      final m = RegExp(r'^(\d+)\+(\d+)$').firstMatch(t);
      if (m != null) {
        cw = int.parse(m.group(1)!);
        cb = int.parse(m.group(2)!);
        break;
      }
    }
    return BoardState(cells,
        checksWhite: cw, checksBlack: cb, whiteToMove: whiteToMove);
  }
}

/// FEN xuất phát của biến thể (dùng làm fallback khi engine chưa sẵn sàng).
const String kVariantStartposFen =
    'vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV w BIbi - 7+7 0 1';
