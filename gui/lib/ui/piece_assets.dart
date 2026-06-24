/// Ánh xạ ký tự quân (FEN) → đường dẫn asset SVG trong `fairyzero_piece_svg/`.
///
/// Quy ước tên file: `<color>-<name>-<L>.svg` với color ∈ {white,black},
/// L = ký tự HOA cho Trắng / thường cho Đen.
///
/// Ghi chú đặc biệt: quân ROYAL (`k`/`K`) và centaur (`m`/`M`) DÙNG CHUNG art
/// "general" (file `*-general-M/m.svg`). Quân royal được vẽ kèm [royalSymbol]
/// dán ở góc dưới-phải để đánh dấu là "General royal".
class PieceAssets {
  static const _dir = 'assets/pieces';

  static const Map<String, String> _names = {
    'p': 'pawn',
    'n': 'knight',
    'b': 'bishop',
    'r': 'rook',
    'a': 'amazon',
    'e': 'chancellor',
    'h': 'archbishop',
    'y': 'alibaba', // customPiece2 (AD)
    's': 'sergeant', // customPiece3
    'v': 'wildebeest', // customPiece1 (CN)
    'm': 'general', // centaur (non-royal)
    'k': 'general', // royal: dùng art general + overlay royalSymbol
  };

  /// Quân royal (vua) — cần overlay [royalSymbol].
  static bool isRoyal(String letter) => letter.toLowerCase() == 'k';

  /// Đường dẫn SVG cho quân theo ký tự FEN.
  static String assetFor(String letter) {
    final isWhite = letter == letter.toUpperCase();
    final t = letter.toLowerCase();
    final name = _names[t] ?? 'pawn';
    final color = isWhite ? 'white' : 'black';
    // Royal (`k`) dùng file art của general (`m`/`M`).
    final base = (t == 'k') ? 'm' : t;
    final fl = isWhite ? base.toUpperCase() : base;
    return '$_dir/$color-$name-$fl.svg';
  }

  /// Biểu tượng đánh dấu quân royal (dán góc dưới-phải).
  static const String royalSymbol = '$_dir/royal_symbol.svg';
}
