import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart' show Archive, ZipDecoder;

import 'final_oracle.dart';
import 'v6_game.dart';
import 'van.dart';

/// Nguồn ván của dữ liệu huấn luyện: thư mục (cả thư mục con), gói `.zip` hoặc một tệp `.xz`; bản Dart của
/// `liet_ke_van` / `xuat` trong `custom_engine/python/xem_du_lieu.py`. Thứ tự ván = thứ tự tên tệp (trong gói
/// = thứ tự trong gói), nên số thứ tự ván GIỐNG bản Python.

const List<String> gameExts = ['.xz', '.gz', '.bin'];

/// Một ván: tệp, hoặc thành viên [member] của gói zip [path].
class GameSource {
  final String path;
  final String? member;
  const GameSource(this.path, [this.member]);

  String get name {
    final base = path.split(RegExp(r'[\\/]')).last;
    return member != null ? '$base:$member' : base;
  }
}

bool _isGameName(String n) => gameExts.any(n.endsWith);

/// Liệt kê ván của [source]. Ném [FileSystemException] nếu không có.
List<GameSource> listGames(String source) {
  final files = <String>[];
  if (FileSystemEntity.isDirectorySync(source)) {
    for (final e in Directory(
      source,
    ).listSync(recursive: true, followLinks: false)) {
      if (e is File && (_isGameName(e.path) || e.path.endsWith('.zip'))) {
        files.add(e.path);
      }
    }
  } else if (FileSystemEntity.isFileSync(source)) {
    files.add(source);
  } else {
    throw FileSystemException('không có $source');
  }
  files.sort();
  final out = <GameSource>[];
  for (final f in files) {
    if (f.endsWith('.zip')) {
      final arch = ZipDecoder().decodeBytes(File(f).readAsBytesSync());
      for (final m in arch) {
        if (m.isFile && _isGameName(m.name)) out.add(GameSource(f, m.name));
      }
    } else if (_isGameName(f)) {
      out.add(GameSource(f));
    }
  }
  return out;
}

/// Đọc các ván từ nguồn, giữ lại MỘT gói zip đang mở (các ván liền nhau thường cùng một gói).
class GameReader {
  String? _zipPath;
  Archive? _zip;

  Uint8List bytesOf(GameSource g) {
    if (g.member == null) return File(g.path).readAsBytesSync();
    if (_zipPath != g.path) {
      _zip = ZipDecoder().decodeBytes(File(g.path).readAsBytesSync());
      _zipPath = g.path;
    }
    final f = _zip!.findFile(g.member!);
    if (f == null) throw FormatException('${g.path} không có ${g.member}');
    return Uint8List.fromList(f.content as List<int>);
  }

  Van read(GameSource g) {
    if (!g.path.endsWith('.xz') && !(g.member ?? '').endsWith('.xz')) {
      throw const FormatException('định dạng cũ (.gz / .bin) chưa hỗ trợ');
    }
    return Van(decodeV6Game(bytesOf(g), g.name), g.name);
  }
}

/// Một dòng của `chi_muc.tsv`.
class IndexRow {
  final int i;
  final String tenLog;
  final int nuoc;
  final String ma;
  final int trang, den;
  final String ly;
  final String ghiChu;
  const IndexRow(
    this.i,
    this.tenLog,
    this.nuoc,
    this.ma,
    this.trang,
    this.den,
    this.ly,
    this.ghiChu,
  );

  String get tsv => [i, tenLog, nuoc, ma, trang, den, ly, ghiChu].join('\t');
}

const List<String> indexColumns = [
  'so',
  'tep',
  'nua_nuoc',
  'ket_qua',
  'quan_trang',
  'quan_den',
  'ly_do',
  'ghi_chu',
];

String tenLogOf(int i) => 'van_${i.toString().padLeft(4, '0')}.txt';

String _cut80(String s) {
  final r = s.replaceAll('\t', ' ').runes.toList();
  return r.length <= 80
      ? String.fromCharCodes(r)
      : String.fromCharCodes(r.sublist(0, 80));
}

/// Dòng chỉ mục của ván thứ [i]: giải mã, kiểm, hỏi [oracle] thế cuối (null = không biết lý do kết thúc).
/// [oracle2]: bộ luật dự phòng, chỉ hỏi khi thế cuối của [oracle] lệch bản ghi.
/// [log] (nếu có) nhận văn bản nhật ký của ván (cho kiểm thử ghi đủ mọi tệp).
Future<IndexRow> indexRowOf(
  int i,
  int total,
  GameSource g,
  GameReader reader,
  FinalOracle? oracle, {
  FinalOracle? oracle2,
  void Function(String log)? log,
}) async {
  final tenLog = tenLogOf(i);
  final Van v;
  try {
    v = reader.read(g);
  } on Exception catch (e) {
    // Tệp hỏng / đọc lỗi: ván này hiện "đọc lỗi" trong bảng, các ván khác vẫn dùng được.
    return IndexRow(
      i,
      tenLog,
      0,
      '?',
      0,
      0,
      'unreadable',
      _cut80(e is FormatException ? e.message : '$e'),
    );
  } on RangeError catch (e) {
    return IndexRow(i, tenLog, 0, '?', 0, 0, 'unreadable', _cut80('$e'));
  }
  final loi = v.kiem();
  if (log != null) log(nhatKy(v, soVan: i, tong: total));
  var cuoi = datQuan(v.banCuoi());
  final ma = maKetQua[v.ketQua()]!;
  var ghiChu = '';
  var ly = 'unknown';
  if (oracle != null) {
    var fi = await oracle.query(v.fen, v.nuoc);
    var cuoiEngine = fi.fen.trim().split(RegExp(r'\s+'))[0];
    if (cuoiEngine != cuoi && oracle2 != null) {
      // Thế cuối lệch: có thể ván có nước mà luật của [oracle] cấm (ván đời luật cũ / mới); thử bộ luật kia.
      final fi2 = await oracle2.query(v.fen, v.nuoc);
      final cuoi2 = fi2.fen.trim().split(RegExp(r'\s+'))[0];
      if (cuoi2 == cuoi) {
        fi = fi2;
        cuoiEngine = cuoi2;
      }
    }
    ly = lyDo(fi.fen, fi.result, fi.legalCount, v.nuoc.length, ma);
    if (cuoiEngine != cuoi) ghiChu = 'ban co cuoi lech engine';
    final kqMa = const {'white': 'W', 'black': 'B', 'draw': 'D'}[fi.result];
    if (kqMa != null && kqMa != ma && ghiChu.isEmpty) {
      ghiChu = 'engine bao ${fi.result}, du lieu bao $ma';
    }
    cuoi = cuoiEngine;
  }
  if (loi.isNotEmpty) ghiChu = _cut80('giai ma sai: ${loi[0]}');
  final (t, d) = demQuan(cuoi);
  return IndexRow(i, tenLog, v.nuoc.length, ma, t, d, ly, ghiChu);
}

/// Văn bản `chi_muc.tsv`.
String indexTsv(List<IndexRow> rows) =>
    '${indexColumns.join('\t')}\n${rows.map((r) => '${r.tsv}\n').join()}';

/// Nhật ký của MỘT ván (để mở ván khi cần, không phải ghi cả đời dữ liệu ra đĩa).
String logOf(GameSource g, int i, int total, GameReader reader) =>
    nhatKy(reader.read(g), soVan: i, tong: total, tatCaNuocCoLuot: true);
