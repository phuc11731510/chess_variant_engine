import 'dart:io';

/// Một ván trong thư mục xem lại (`--replay-dir`): một dòng của `chi_muc.tsv`.
class ReplayEntry {
  /// Số thứ tự của ván trong nguồn dữ liệu (cột `so`).
  final int id;

  /// Tên tệp nhật ký (`van_NNNN.txt`) nằm cùng thư mục.
  final String file;

  /// Số nửa nước.
  final int plies;

  /// Kết quả theo dữ liệu: `W` Trắng thắng, `B` Đen thắng, `D` hoà, `?` đọc lỗi.
  final String result;
  final int whitePieces;
  final int blackPieces;

  /// Mã lý do kết thúc (xem [reasonLabels]).
  final String reason;

  /// Ghi chú lỗi khi dựng bảng (rỗng = ổn).
  final String note;

  /// Nhãn CỐ ĐỊNH của ván (rỗng = không có): với ván của vòng lặp liên tục là `<số gói>.<thứ tự trong gói, từ 1>`, vd `992.8`
  /// = ván thứ 8 của gói `goi_00992_...zip`. Khác [id] (vị trí trong danh sách của đời, đổi khi vòng lặp thêm / dọn gói), nhãn này
  /// theo ván mãi mãi và khớp tên gói trên điện thoại.
  final String label;

  const ReplayEntry({
    required this.id,
    required this.file,
    required this.plies,
    required this.result,
    required this.whitePieces,
    required this.blackPieces,
    required this.reason,
    required this.note,
    this.label = '',
  });

  /// Cách gọi ván trên màn hình: nhãn cố định nếu có, không thì `#<id>`.
  String get tag => label.isEmpty ? '#$id' : label;

  ReplayEntry withLabel(String l) => ReplayEntry(
    id: id,
    file: file,
    plies: plies,
    result: result,
    whitePieces: whitePieces,
    blackPieces: blackPieces,
    reason: reason,
    note: note,
    label: l,
  );

  int get pieces => whitePieces + blackPieces;
  bool get decisive => result == 'W' || result == 'B';

  String get resultText {
    switch (result) {
      case 'W':
        return 'Trắng thắng';
      case 'B':
        return 'Đen thắng';
      case 'D':
        return 'Hoà';
      default:
        return '?';
    }
  }

  String get reasonText => reasonLabels[reason] ?? reason;

  /// Mã lý do (`ly_do` trong chi_muc.tsv, do xem_du_lieu.py ghi) -> chữ hiện trong bảng.
  static const Map<String, String> reasonLabels = {
    'checks': 'đủ số lần chiếu',
    'no_moves': 'hết nước đi (thua)',
    'rule50': 'luật 50 nước',
    'repetition': 'lặp thế 3 lần',
    'cut': 'bị cắt (quá dài)',
    'adjudicated': 'chấp thua',
    'unknown': 'không rõ',
    'unreadable': 'đọc lỗi',
  };

  static ReplayEntry? tryParse(String line) {
    final c = line.split('\t');
    if (c.length < 7) return null;
    final id = int.tryParse(c[0]);
    final plies = int.tryParse(c[2]);
    final w = int.tryParse(c[4]);
    final b = int.tryParse(c[5]);
    if (id == null || plies == null || w == null || b == null) return null;
    return ReplayEntry(
      id: id,
      file: c[1],
      plies: plies,
      result: c[3],
      whitePieces: w,
      blackPieces: b,
      reason: c[6],
      note: c.length > 7 ? c[7].trim() : '',
    );
  }
}

/// Thư mục các ván để xem lại: `chi_muc.tsv` (bảng các ván) + `van_NNNN.txt` (nhật ký từng ván).
/// Tạo bằng `custom_engine/python/xem_du_lieu.py <nguồn> --xuat <thư mục> --engine ...`.
class ReplayLibrary {
  final String dir;
  final List<ReplayEntry> entries;

  /// Gọi TRƯỚC khi mở nhật ký của một ván (Android: ghi nhật ký của ván đó từ dữ liệu huấn luyện khi cần).
  /// Null = nhật ký đã có sẵn trong [dir].
  final void Function(ReplayEntry e)? prepare;
  const ReplayLibrary(this.dir, this.entries, {this.prepare});

  static const indexName = 'chi_muc.tsv';

  /// Đọc `chi_muc.tsv` trong [dir]. Ném [FileSystemException] / [FormatException] nếu không có / rỗng.
  static ReplayLibrary load(String dir, {void Function(ReplayEntry e)? prepare}) {
    final f = File('$dir${Platform.pathSeparator}$indexName');
    final lines = f.readAsLinesSync();
    final out = <ReplayEntry>[];
    for (final l in lines.skip(1)) {
      if (l.trim().isEmpty) continue;
      final e = ReplayEntry.tryParse(l);
      if (e != null) out.add(e);
    }
    if (out.isEmpty) throw FormatException('$indexName không có ván nào');
    final labels = _readLabels(dir);
    final entries = labels.isEmpty
        ? out
        : [for (final e in out) e.withLabel(labels[e.id] ?? '')];
    return ReplayLibrary(dir, entries, prepare: prepare);
  }

  /// Nhãn cố định của từng ván, đọc từ `nguon.txt` (do app Android ghi cạnh chi_muc.tsv); rỗng nếu không có tệp đó.
  static Map<int, String> _readLabels(String dir) {
    try {
      final f = File('$dir${Platform.pathSeparator}nguon.txt');
      if (!f.existsSync()) return const {};
      return labelsFromSources(f.readAsLinesSync().skip(1));
    } on Exception {
      return const {};
    }
  }

  /// Nhãn theo từng dòng `<đường dẫn gói>\t<thành viên>` của `nguon.txt` (dòng thứ i = ván số i): gói của vòng lặp liên tục
  /// `goi_<số>_n<đời>_<ván>_<thế>.zip` cho nhãn `<số>.<thứ tự trong gói, từ 1>`; nguồn khác không có nhãn.
  static Map<int, String> labelsFromSources(Iterable<String> lines) {
    final re = RegExp(r'^goi_(\d+)_n\d+_\d+_\d+\.zip$');
    final out = <int, String>{};
    String? lastPath;
    var k = 0;
    var i = -1;
    for (final l in lines) {
      if (l.isEmpty) continue;
      i++;
      final tab = l.lastIndexOf('\t');
      final path = tab < 0 ? l : l.substring(0, tab);
      if (path != lastPath) {
        lastPath = path;
        k = 0;
      }
      k++;
      final m = re.firstMatch(path.split(RegExp(r'[\\/]')).last);
      if (m != null) out[i] = '${int.parse(m.group(1)!)}.$k';
    }
    return out;
  }

  String pathOf(ReplayEntry e) => '$dir${Platform.pathSeparator}${e.file}';

  /// Số quân nhiều nhất còn lại ở cuối một ván (cho thanh trượt bộ lọc).
  int get maxPieces => entries.fold(0, (m, e) => e.pieces > m ? e.pieces : m);
}
