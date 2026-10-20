import 'dart:io';

/// Nhật ký ván tự đấu: mỗi nước engine đi, ghi đúng lệnh `position` đã gửi (có đủ
/// dãy nước từ thế gốc nên dựng lại được thế, kể cả bộ đếm luật 50 nước), số lượt
/// tìm / tốc độ thật, và vài nước tốt nhất engine đã cân nhắc (điểm + biến chính).
/// Ghi vào `tu_dau_log/tu_dau_<thời điểm>.txt` trong thư mục hiện hành; lỗi ghi tệp
/// không bao giờ làm hỏng ván.
class SelfPlayLog {
  final String header;
  File? _file;
  bool _failed = false;

  SelfPlayLog(this.header);

  /// Đường dẫn tệp (null nếu chưa ghi gì hoặc không ghi được).
  String? get path => _file?.path;

  void entry({
    required int ply,
    required String positionCmd,
    required Map<int, String> infos,
    required List<String> stats,
    required String bestmove,
  }) {
    if (_failed) return;
    try {
      _file ??= _open();
      final b = StringBuffer()
        ..writeln('--- nửa nước ${ply + 1} (${ply.isEven ? "trắng" : "đen"} đi) → $bestmove')
        ..writeln(positionCmd);
      for (final k in (infos.keys.toList()..sort())) {
        b.writeln('  ${infos[k]}');
      }
      // N = số lượt tìm, P = xác suất ban đầu (prior) của mạng, Q = giá trị nước đó từ phía người đi.
      for (final s in stats) {
        b.writeln('    $s');
      }
      _file!.writeAsStringSync(b.toString(), mode: FileMode.append, flush: true);
    } catch (_) {
      _failed = true;
    }
  }

  File _open() {
    final dir = Directory('tu_dau_log')..createSync(recursive: true);
    final t = DateTime.now();
    String two(int v) => v.toString().padLeft(2, '0');
    final name =
        'tu_dau_${t.year}${two(t.month)}${two(t.day)}_${two(t.hour)}${two(t.minute)}${two(t.second)}.txt';
    final f = File('${dir.path}${Platform.pathSeparator}$name');
    f.writeAsStringSync('$header\n');
    return f;
  }
}
