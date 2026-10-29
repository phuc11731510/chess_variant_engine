// Bảng tìm kiếm bên phải (tự đấu / xem lại): đọc mục nhật ký, ghép RootStats với dòng info,
// đổi giá trị sang phía Trắng.

import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/config/replay_loader.dart';
import 'package:fairyzero_gui/domain/search_record.dart';

void main() {
  const log = '''
# tự đấu 2026-10-29 · model gen141
--- nửa nước 1 (trắng đi) → e3e4
position startpos
  depth 3 multipv 1 score cp 12 wdl 300 500 200 nodes 200 nps 50 time 4000 pv e3e4 b8b7 c3c4
  depth 2 multipv 2 score cp -40 wdl 200 450 350 nodes 200 nps 50 time 4000 pv g3g5 h8h7
    e3e4 N 82 P 0.2932 Q 0.009 Pnet 0.3861
    g3g5 N 34 P 0.0647 Q 0.052
--- nửa nước 2 (đen đi) → b8b7
position startpos moves e3e4
  depth 1 multipv 1 score cp 25 wdl 400 300 300 nodes 150 nps 30 time 5000 pv b8b7
    b8b7 N 50 P 0.2346 Q 0.100 Pnet 0.2346
''';

  test('parseLog: mục theo chỉ số nước; RootStats ghép với info cùng nước đầu PV', () {
    final m = SearchRecord.parseLog(log);
    expect(m.keys.toList()..sort(), [0, 1]);
    final r = m[0]!;
    expect(r.bestmove, 'e3e4');
    expect(r.positionCmd, 'position startpos');
    expect(r.nodes, 200);
    expect(r.timeMs, 4000);
    final c = r.candidates;
    expect(c.map((x) => x.move), ['e3e4', 'g3g5']);
    expect(c[0].n, 82);
    expect(c[0].p, 0.2932);
    expect(c[0].pnet, 0.3861);
    expect(c[1].pnet, isNull); // nhật ký cũ / thiếu Pnet
    expect(c[0].cp, 12);
    expect(c[0].pv, ['e3e4', 'b8b7', 'c3c4']);
    expect(c[1].win, 200);
  });

  test('forWhite: Trắng đi giữ dấu; Đen đi đổi dấu Q, cp và đổi chỗ thắng / thua', () {
    final m = SearchRecord.parseLog(log);
    final w = m[0]!.candidates.first.forWhite(true);
    expect(w.q, 0.009);
    expect(w.cp, 12);
    expect([w.whiteWin, w.draw, w.blackWin], [300, 500, 200]);
    final b = m[1]!.candidates.first.forWhite(false);
    expect(b.q, -0.100);
    expect(b.cp, -25);
    expect([b.whiteWin, b.draw, b.blackWin], [300, 300, 400]);
  });

  test('parseReplay mang theo lần tìm của từng nước', () {
    final g = parseReplay(log);
    expect(g.moves, ['e3e4', 'b8b7']);
    expect(g.searches[1]!.bestmove, 'b8b7');
    expect(parseReplay('e3e4 b8b7').searches, isEmpty);
  });
}
