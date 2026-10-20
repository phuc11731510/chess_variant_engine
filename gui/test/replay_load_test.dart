// Xem lại ván đã lưu: đọc biên bản (nhật ký tự đấu / danh sách nước UCI) và dựng ván không cần engine tìm kiếm.

import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/config/launch_config.dart';
import 'package:fairyzero_gui/config/replay_loader.dart';
import 'package:fairyzero_gui/domain/game_controller.dart';
import 'package:fairyzero_gui/engine/engine_service.dart';

/// Engine giả chỉ biết áp nước: thế sau k nước có Tốt ở hàng 6, cột k % 10; chỉ [ok] là nước hợp lệ.
class ReplayEngine implements EngineService {
  final Set<String> ok;
  int played = 0;
  ReplayEngine(this.ok);
  @override
  Future<void> start() async {}
  @override
  Future<void> newGame({String? fen}) async {}
  @override
  Future<void> applyMove(String uci) async => played++;
  @override
  Future<List<String>> legalMoves() async => ok.toList();
  @override
  Future<String> currentFen() async {
    final k = played % 10;
    final left = k == 0 ? '' : '$k';
    final right = k == 9 ? '' : '${9 - k}';
    return 'vrhbqkberv/msysnnsysm/yppppppppy/10/10/${left}P$right/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV '
        '${played % 2 == 0 ? "w" : "b"} - - 8+8 0 1';
  }

  @override
  Future<GameResult> gameResult() async => GameResult.white;
  @override
  Future<String> bestMove() async => throw StateError('xem lại không được tìm nước');
  @override
  Future<void> dispose() async {}
}

void main() {
  test('parseReplay: nhật ký tự đấu -> lệnh position cuối + nước của mục cuối', () {
    const log = '''
# tự đấu 2026-10-20 · model gen92
--- nửa nước 1 (trắng đi) → e3e5
position startpos
  depth 7 multipv 1 score cp 0 pv e3e5
--- nửa nước 2 (đen đi) → b8b6
position startpos moves e3e5
--- nửa nước 3 (trắng đi) → a3a4
position startpos moves e3e5 b8b6
    a3a4 N 10 P 0.1 Q 0.0
''';
    final g = parseReplay(log);
    expect(g.startFen, isNull);
    expect(g.moves, ['e3e5', 'b8b6', 'a3a4']);
  });

  test('parseReplay: position fen ... moves ...; danh sách nước thuần; lỗi khi rỗng', () {
    final a = parseReplay(
      '--- nửa nước 1 → j9i7\nposition fen 10/10/10/6k3/10/3s6/10/R9/5N1K2/6B3 w - - 2+5 0 1 moves a3a7\n',
    );
    expect(a.startFen, '10/10/10/6k3/10/3s6/10/R9/5N1K2/6B3 w - - 2+5 0 1');
    expect(a.moves, ['a3a7', 'j9i7']);
    final b = parseReplay('# ván thử\n1. e3e5 b8b6\n2. a3a10 c8c10q\n');
    expect(b.moves, ['e3e5', 'b8b6', 'a3a10', 'c8c10q']);
    expect(() => parseReplay('không có gì ở đây'), throwsFormatException);
  });

  test('LaunchConfig: --replay <tệp>', () {
    final c = LaunchConfig.fromArgs(const ['--replay', 'tu_dau_log/x.txt']);
    expect(c.replayPath, 'tu_dau_log/x.txt');
    expect(LaunchConfig.fromArgs(const []).replayPath, isNull);
  });

  test('GameController xem lại: đủ thế sau từng nước, dừng ở thế đầu, chặn nước sai', () async {
    final c = GameController(
      engine: ReplayEngine({'e3e5', 'b8b6', 'a3a4'}),
      humanIsWhite: true,
      replay: true,
    );
    await c.initReplay(['e3e5', 'b8b6', 'a3a4']);
    expect(c.moves, ['e3e5', 'b8b6', 'a3a4']);
    expect(c.fens.length, 4);
    expect(c.shownPly, 0); // mở ra ở thế xuất phát
    expect(c.inReview, true);
    expect(c.humansTurn, false);
    c.stepForward();
    expect(c.shownPly, 1);
    expect(c.shownLastMoveFlats.length, 2);
    c.goLive();
    expect(c.shownPly, 3);
    expect(c.result, GameResult.white);
    c.dispose();

    final d = GameController(
      engine: ReplayEngine({'e3e5'}),
      humanIsWhite: true,
      replay: true,
    );
    await d.initReplay(['e3e5', 'zzzz', 'a3a4']);
    expect(d.moves, ['e3e5']);
    expect(d.status, contains('không hợp lệ'));
    d.dispose();
  });

  test('GameController xem lại: Space tự chạy tiến từng nước tới nước cuối rồi dừng', () async {
    final c = GameController(
      engine: ReplayEngine({'e3e5', 'b8b6'}),
      humanIsWhite: true,
      replay: true,
    );
    await c.initReplay(['e3e5', 'b8b6']);
    c.togglePause(); // trong chế độ xem lại = bật tự chạy
    expect(c.autoPlaying, true);
    await Future<void>.delayed(GameController.autoStep * 3);
    expect(c.shownPly, 2);
    expect(c.autoPlaying, false);
    c.dispose();
  });
}
