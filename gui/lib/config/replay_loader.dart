import 'dart:io';

/// Một ván đọc từ tệp để xem lại: thế xuất phát ([startFen] null = thế đầu của biến thể)
/// và dãy nước đi UCI thật.
class ReplayGame {
  final String? startFen;
  final List<String> moves;
  const ReplayGame(this.startFen, this.moves);
}

final RegExp _uciMove = RegExp(r'^[a-j](10|[1-9])[a-j](10|[1-9])[a-z]?$');

/// Đọc biên bản từ [path]. Hai dạng:
///  - nhật ký của chế độ tự đấu (`tu_dau_log/tu_dau_*.txt`): lấy lệnh `position ...` CUỐI CÙNG
///    (có đủ dãy nước từ thế gốc) rồi cộng nước engine chọn ở đúng mục đó (dòng `--- ... → nước`);
///  - tệp văn bản chỉ có các nước UCI cách nhau bằng khoảng trắng/xuống dòng (số thứ tự như "12." bị bỏ qua).
/// Ném [FormatException] nếu không tìm thấy nước nào.
ReplayGame readReplayFile(String path) {
  final text = File(path).readAsStringSync();
  return parseReplay(text);
}

ReplayGame parseReplay(String text) {
  final lines = text.split(RegExp(r'\r?\n'));
  int lastPos = -1;
  for (int i = 0; i < lines.length; i++) {
    if (lines[i].startsWith('position ')) lastPos = i;
  }
  if (lastPos >= 0) {
    final toks = lines[lastPos].trim().split(RegExp(r'\s+')).skip(1).toList();
    String? fen;
    int mi = toks.indexOf('moves');
    final head = mi < 0 ? toks : toks.sublist(0, mi);
    if (head.isNotEmpty && head.first == 'fen') fen = head.skip(1).join(' ');
    final moves = mi < 0 ? <String>[] : toks.sublist(mi + 1);
    // Mục nhật ký này: dòng tiêu đề ngay trước lệnh position có "→ <nước đã chơi>".
    if (lastPos > 0) {
      final m = RegExp(r'→\s*(\S+)').firstMatch(lines[lastPos - 1]);
      if (m != null && m.group(1) != '0000') moves.add(m.group(1)!);
    }
    if (moves.isEmpty) throw const FormatException('Không có nước đi nào trong tệp');
    return ReplayGame(fen, moves);
  }
  final moves = <String>[];
  for (final line in lines) {
    if (line.trimLeft().startsWith('#')) continue;
    for (final t in line.trim().split(RegExp(r'\s+'))) {
      if (_uciMove.hasMatch(t)) moves.add(t);
    }
  }
  if (moves.isEmpty) throw const FormatException('Không có nước đi nào trong tệp');
  return ReplayGame(null, moves);
}
