/// Một ô cờ (0-based): file 0..9 (a..j), rank 0..9 (rank1..rank10).
class Sq {
  final int file;
  final int rank;
  const Sq(this.file, this.rank);

  /// Chỉ số phẳng khớp `BoardState.cells[rank][file]` = rank*10 + file.
  int get flat => rank * 10 + file;

  /// Tên UCI thật, vd "f1", "e10".
  String get name => '${String.fromCharCode(0x61 + file)}${rank + 1}';

  @override
  bool operator ==(Object other) =>
      other is Sq && other.file == file && other.rank == rank;

  @override
  int get hashCode => flat;
}

/// Một nước đi UCI đã phân tích: ô nguồn, ô đích, (tuỳ chọn) hậu tố phong cấp.
/// Hỗ trợ hàng hai chữ số (e10) và hậu tố phong (f2f1h).
class UciMove {
  final Sq from;
  final Sq to;
  final String? promo; // ký tự quân phong, hoặc null
  final String uci; // chuỗi gốc

  const UciMove(this.from, this.to, this.promo, this.uci);

  static UciMove? tryParse(String s) {
    int i = 0;

    int? readFile() {
      if (i >= s.length) return null;
      final c = s.codeUnitAt(i);
      if (c < 0x61 || c > 0x6a) return null; // a..j
      i++;
      return c - 0x61;
    }

    int? readRank() {
      final start = i;
      while (i < s.length && s.codeUnitAt(i) >= 0x30 && s.codeUnitAt(i) <= 0x39) {
        i++;
      }
      if (i == start) return null;
      return int.parse(s.substring(start, i)) - 1;
    }

    final ff = readFile();
    final fr = readRank();
    final tf = readFile();
    final tr = readRank();
    if (ff == null || fr == null || tf == null || tr == null) return null;

    final promo = (i < s.length) ? s.substring(i) : null;
    return UciMove(Sq(ff, fr), Sq(tf, tr), promo, s);
  }
}
