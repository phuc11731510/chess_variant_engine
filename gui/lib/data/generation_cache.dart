import 'dart:async';
import 'dart:io';
import 'dart:isolate';

import 'final_oracle.dart';
import 'final_oracle_ffi.dart';
import 'game_library.dart';

/// Một đời dữ liệu (thư mục `games_genN` hoặc gói zip) đã được đổi sang bảng chỉ mục xem lại, lưu ĐỆM trong thư mục
/// riêng của ứng dụng: `chi_muc.tsv` (bảng các ván: số nửa nước, kết quả, số quân, lý do kết thúc) và `nguon.txt`
/// (dấu vân tay của nguồn + tệp / thành viên zip của từng ván). Nhật ký từng ván (`van_NNNN.txt`, ~130 KB) chỉ
/// được ghi khi ván đó được mở: cả đời dữ liệu là vài trăm MB chữ, không cần giữ hết.
///
/// Đổi sang chỉ mục mất vài chục giây trên điện thoại (một lần cho mỗi đời; nguồn không đổi thì mở ngay).

const String _indexFile = 'chi_muc.tsv';
const String _sourceFile = 'nguon.txt';

/// Cách hỏi thế cuối của ván: 'ffi' = engine trong ứng dụng (Android), 'none' = không hỏi (không biết lý do kết
/// thúc), 'process:<đường dẫn engine>' = engine chạy riêng (máy tính, kiểm thử).
typedef OracleKind = String;

Future<FinalOracle?> _openOracle(OracleKind kind, {bool backup = false}) async {
  if (kind == 'ffi') {
    // [1] = luật trước 2026-11-24 (libfzcu.so), xem RuleSetSwitcher.
    return backup ? FfiFinalOracle(libName: 'libfzcu.so') : FfiFinalOracle();
  }
  if (kind.startsWith('process:')) {
    // 'process:<engine>' hoặc 'process:<engine>|<engine luật dự phòng>'.
    final parts = kind.substring(8).split('|');
    if (backup) {
      return parts.length > 1 ? ProcessFinalOracle.start(parts[1]) : null;
    }
    return ProcessFinalOracle.start(parts[0]);
  }
  return null;
}

/// Dấu vân tay của nguồn: số ván + tổng kích thước + thời điểm sửa mới nhất của các tệp. Đổi (vòng lặp ghi thêm ván,
/// gói zip được thay) thì chỉ mục cũ không còn đúng và phải làm lại.
String fingerprint(String source, List<GameSource> ds) {
  if (isGroupSource(source)) return groupFingerprint(groupFiles(source));
  var bytes = 0;
  var newest = 0;
  final seen = <String>{};
  for (final g in ds) {
    if (!seen.add(g.path)) continue;
    final st = File(g.path).statSync();
    bytes += st.size;
    final m = st.modified.millisecondsSinceEpoch;
    if (m > newest) newest = m;
  }
  return 'v1|${ds.length}|$bytes|$newest';
}

/// Dấu vân tay của một NHÓM tệp (các gói của một đời mạng): chỉ dựa vào tên, kích thước và giờ sửa, KHÔNG mở gói, nên
/// quét màn hình đầu nhanh dù có hàng chục gói. Thêm gói mới (vòng lặp vẫn đang sinh ván của mạng mới nhất), dọn gói
/// cũ hoặc thay gói đều làm dấu đổi.
String groupFingerprint(List<String> files) {
  var bytes = 0;
  var newest = 0;
  var n = 0;
  var h = 0;
  for (final p in files) {
    final st = File(p).statSync();
    if (st.type == FileSystemEntityType.notFound) continue;
    n++;
    bytes += st.size;
    final m = st.modified.millisecondsSinceEpoch;
    if (m > newest) newest = m;
    // Tên tệp cũng góp vào dấu (gói thay bằng gói khác cùng kích thước vẫn khác tên).
    for (final c in p.split(RegExp(r'[\\/]')).last.codeUnits) {
      h = (h * 31 + c) & 0x3fffffff;
    }
  }
  return 'g1|$n|$bytes|$newest|$h';
}

/// Chỉ mục trong [cacheDir] còn đúng với [source] không (cùng dấu vân tay)?
bool isCurrent(String source, String cacheDir) {
  try {
    final f = File('$cacheDir/$_sourceFile');
    if (!f.existsSync() || !File('$cacheDir/$_indexFile').existsSync()) {
      return false;
    }
    if (isGroupSource(source)) {
      return f.readAsLinesSync().first == groupFingerprint(groupFiles(source));
    }
    return f.readAsLinesSync().first == fingerprint(source, listGames(source));
  } on Exception {
    return false;
  }
}

/// Tên thư mục đệm của một nguồn tên [name] (chỉ giữ chữ, số, `_ . -`).
String cacheNameOf(String name) => name.replaceAll(RegExp(r'[^A-Za-z0-9_.-]'), '_');

/// Dọn bộ nhớ đệm: trong [xemDir] xoá mọi thư mục đệm có tên KHÔNG nằm trong [keep]. Bộ nhớ đệm chỉ đáng giữ khi còn đúng
/// với dữ liệu hiện có (đời còn nguồn và nguồn không đổi); đời đã bị vòng lặp dọn gói, hoặc đã có thêm / bớt gói, thì bảng ván
/// và nhật ký trong đó nói về ván không còn (hoặc không còn đủ) trong dữ liệu huấn luyện, nên bỏ đi; mở đời đó lần sau đổi lại
/// từ nguồn. Trả về số thư mục đã xoá. Không đụng tới tệp lẻ, và lỗi xoá từng thư mục không làm hỏng cả lượt dọn.
int purgeStaleCaches(String xemDir, Set<String> keep) {
  var removed = 0;
  try {
    final dir = Directory(xemDir);
    if (!dir.existsSync()) return 0;
    for (final e in dir.listSync(followLinks: false)) {
      if (e is! Directory) continue;
      final name = e.path.split(RegExp(r'[\\/]')).last;
      if (keep.contains(name)) continue;
      try {
        e.deleteSync(recursive: true);
        removed++;
      } on Exception {
        // đang bị dùng / không xoá được: lần quét sau thử lại
      }
    }
  } on Exception {
    // không liệt kê được: bỏ qua lượt dọn này
  }
  return removed;
}

/// Tin nhắn từ tiến trình nền: [done] / [total] ván đã xử lý, hoặc [error], hoặc [finished].
class ConvertEvent {
  final int done;
  final int total;
  final String? error;
  final bool finished;
  final int unreadable;
  const ConvertEvent(
    this.done,
    this.total, {
    this.error,
    this.finished = false,
    this.unreadable = 0,
  });
}

class _Job {
  final SendPort port;
  final String source;
  final String cacheDir;
  final OracleKind oracle;
  final bool force;
  const _Job(this.port, this.source, this.cacheDir, this.oracle, this.force);
}

/// Dựng chỉ mục của [source] vào [cacheDir] ở một isolate nền; đẩy tiến độ ra luồng. Nguồn không đổi thì xong ngay.
Stream<ConvertEvent> convert(
  String source,
  String cacheDir, {
  OracleKind oracle = 'ffi',
  bool force = false,
}) {
  final ctl = StreamController<ConvertEvent>();
  final rx = ReceivePort();
  Isolate? iso;
  rx.listen((m) {
    if (m is ConvertEvent) {
      ctl.add(m);
      if (m.finished || m.error != null) {
        rx.close();
        iso?.kill();
        ctl.close();
      }
    }
  });
  () async {
    try {
      iso = await Isolate.spawn(
        _run,
        _Job(rx.sendPort, source, cacheDir, oracle, force),
      );
    } catch (e) {
      ctl.add(ConvertEvent(0, 0, error: '$e'));
      rx.close();
      ctl.close();
    }
  }();
  ctl.onCancel = () {
    rx.close();
    iso?.kill();
  };
  return ctl.stream;
}

Future<void> _run(_Job job) async {
  final cacheDir = job.cacheDir;
  final force = job.force;
  try {
    final ds = listGames(job.source);
    if (ds.isEmpty) {
      job.port.send(
        const ConvertEvent(
          0,
          0,
          error: 'không có ván nào (tệp .xz) trong nguồn này',
        ),
      );
      return;
    }
    final fp = fingerprint(job.source, ds);
    final dir = Directory(cacheDir)..createSync(recursive: true);
    final src = File('$cacheDir/$_sourceFile');
    if (!force &&
        src.existsSync() &&
        File('$cacheDir/$_indexFile').existsSync() &&
        src.readAsLinesSync().first == fp) {
      job.port.send(ConvertEvent(ds.length, ds.length, finished: true));
      return;
    }
    FinalOracle? oracle;
    try {
      oracle = await _openOracle(job.oracle);
    } catch (_) {
      oracle =
          null; // engine không nạp được: vẫn có bảng ván, chỉ thiếu lý do kết thúc
    }
    FinalOracle? oracle2;
    if (oracle != null) {
      try {
        oracle2 = await _openOracle(job.oracle, backup: true);
      } catch (_) {
        oracle2 = null; // không có bộ luật dự phòng: ván lệch luật báo "lệch engine" như trước
      }
    }
    final reader = GameReader();
    final rows = <IndexRow>[];
    var last = 0;
    try {
      for (int i = 0; i < ds.length; i++) {
        rows.add(
          await indexRowOf(i, ds.length, ds[i], reader, oracle, oracle2: oracle2),
        );
        final now = DateTime.now().millisecondsSinceEpoch;
        if (now - last > 150 || i + 1 == ds.length) {
          last = now;
          job.port.send(ConvertEvent(i + 1, ds.length));
        }
      }
    } finally {
      await oracle?.close();
      await oracle2?.close();
    }
    // Nhật ký cũ (đánh số theo nguồn cũ) không còn khớp: xoá trước khi ghi chỉ mục mới.
    for (final e in dir.listSync()) {
      if (e is File && RegExp(r'van_\d+\.txt$').hasMatch(e.path)) {
        e.deleteSync();
      }
    }
    final buf = StringBuffer('$fp\n');
    for (final g in ds) {
      buf.write('${g.path}\t${g.member ?? ''}\n');
    }
    final tmp = File('$cacheDir/$_indexFile.tmp')
      ..writeAsStringSync(indexTsv(rows));
    tmp.renameSync('$cacheDir/$_indexFile');
    src.writeAsStringSync(buf.toString());
    job.port.send(
      ConvertEvent(
        ds.length,
        ds.length,
        finished: true,
        unreadable: rows.where((r) => r.ly == 'unreadable').length,
      ),
    );
  } catch (e, st) {
    job.port.send(ConvertEvent(0, 0, error: '$e\n$st'));
  }
}

/// Bộ chuẩn bị nhật ký từng ván cho bảng chọn ván: ghi `van_NNNN.txt` khi ván được mở lần đầu.
class GameFilePreparer {
  final String cacheDir;
  final GameReader _reader = GameReader();
  late final List<GameSource> _games = _readSources();
  GameFilePreparer(this.cacheDir);

  List<GameSource> _readSources() {
    final lines = File('$cacheDir/$_sourceFile').readAsLinesSync();
    return [
      for (final l in lines.skip(1))
        if (l.isNotEmpty) _parse(l),
    ];
  }

  static GameSource _parse(String l) {
    final k = l.lastIndexOf('\t');
    final member = l.substring(k + 1);
    return GameSource(l.substring(0, k), member.isEmpty ? null : member);
  }

  /// Bảo đảm tệp nhật ký của ván [i] có trong [cacheDir]; trả đường dẫn của nó.
  void ensure(int i) {
    final out = File('$cacheDir/${tenLogOf(i)}');
    if (out.existsSync()) return;
    final tmp = File('${out.path}.tmp')
      ..writeAsStringSync(logOf(_games[i], i, _games.length, _reader));
    tmp.renameSync(out.path);
  }
}
