/// Ánh xạ ký tự quân (FEN) → đường dẫn asset SVG trong `assets/pieces/`.
///
/// Quy ước tên file: `<color>-<name>-<L>.svg` với color ∈ {white,black},
/// L = ký tự HOA cho Trắng / thường cho Đen.
///
/// Bộ quân của biến thể hiện tại (khớp `src/app/variant_setup.cc` của engine):
/// Tốt p, Mã n, Tượng b, Xe r, Hậu q, Hoàng gia k (quân royal, đếm chiếu), Centaur m,
/// Wildebeest v, Alibaba y, Sergeant s, Pháo c, Grasshopper g. Không còn Archbishop,
/// Chancellor, Amazon.
class PieceAssets {
  static const _dir = 'assets/pieces';

  /// Tên trong tên file ảnh. (Tên `grasshoper` viết thiếu một chữ p là tên tệp đã đặt,
  /// giữ nguyên để khỏi đổi tên ảnh.)
  static const Map<String, String> _names = {
    'p': 'pawn',
    'n': 'knight',
    'b': 'bishop', // customPiece1 (BmW)
    'r': 'rook',
    'q': 'queen',
    'k': 'king', // Hoàng gia (royal)
    'm': 'general', // Centaur (KnN)
    'v': 'wildebeest', // customPiece3 (CN)
    'y': 'alibaba', // customPiece4 (ADmW)
    's': 'sergeant', // customPiece5
    'c': 'cannon', // Pháo (mRcpRW); ảnh vector hoá từ PNG bằng tool/png_to_piece_svg.py
    'g': 'grasshoper', // Grasshopper (gQK)
  };

  /// Các loại quân có ảnh (chữ thường).
  static Iterable<String> get pieceTypes => _names.keys;

  /// Quân royal (Hoàng gia) — được in số chiếu còn lại lên mặt.
  static bool isRoyal(String letter) => letter.toLowerCase() == 'k';

  /// Đường dẫn SVG cho quân theo ký tự FEN.
  static String assetFor(String letter) {
    final isWhite = letter == letter.toUpperCase();
    final t = letter.toLowerCase();
    final name = _names[t] ?? 'pawn';
    final color = isWhite ? 'white' : 'black';
    final fl = isWhite ? t.toUpperCase() : t;
    return '$_dir/$color-$name-$fl.svg';
  }
}
