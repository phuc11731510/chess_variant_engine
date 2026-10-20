// Tự đấu: xem lại các nước đã đi (lùi / tiến / về đầu / về hiện tại) trong khi ván vẫn tiếp tục.

import 'dart:async';

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/config/launch_config.dart';
import 'package:fairyzero_gui/domain/game_controller.dart';
import 'package:fairyzero_gui/engine/engine_service.dart';
import 'package:fairyzero_gui/main.dart';
import 'package:fairyzero_gui/ui/move_strip.dart';

/// Engine giả cho tự đấu: mỗi nước chờ test "thả" mới đi; thế sau k nước có một
/// Tốt ở hàng 6, cột k (k = 0..9) để phân biệt từng thế.
class GatedEngine implements EngineService {
  int played = 0;
  final List<Completer<String>> gates = [];

  String _fen() {
    final k = played % 10;
    final left = k == 0 ? '' : '$k';
    final right = k == 9 ? '' : '${9 - k}';
    final row = '${left}P$right';
    return 'vrhbqkberv/msysnnsysm/yppppppppy/10/10/$row/10/YPPPPPPPPY/MSYSNNSYSM/VRHBQKBERV '
        '${played % 2 == 0 ? "w" : "b"} - - 8+8 0 1';
  }

  /// Thả nước tiếp theo cho vòng tự đấu.
  void release(String uci) => gates.removeAt(0).complete(uci);

  @override
  Future<void> start() async {}
  @override
  Future<void> newGame({String? fen}) async {}
  @override
  Future<void> applyMove(String uci) async => played++;
  @override
  Future<List<String>> legalMoves() async => const [];
  @override
  Future<String> currentFen() async => _fen();
  @override
  Future<GameResult> gameResult() async => GameResult.undecided;
  @override
  Future<String> bestMove() {
    final c = Completer<String>();
    gates.add(c);
    return c.future;
  }

  @override
  Future<void> dispose() async {}
}

/// Chạy [n] nước: thả từng nước rồi để vòng lặp xử lý xong.
Future<void> play(GatedEngine e, int n, [int from = 0]) async {
  for (int i = 0; i < n; i++) {
    while (e.gates.isEmpty) {
      await Future<void>.delayed(Duration.zero);
    }
    final k = from + i;
    e.release('a${k % 8 + 1}a${k % 8 + 2}');
    for (int j = 0; j < 20; j++) {
      await Future<void>.delayed(Duration.zero);
    }
  }
}

void main() {
  test(
    'GameController tu dau: xem lai nuoc di trong khi van tiep tuc',
    () async {
      final e = GatedEngine();
      final c = GameController(
        engine: e,
        humanIsWhite: true,
        selfPlay: true,
        maxPlies: 400,
      );
      unawaited(
        c.init(),
      ); // init() chạy luôn vòng tự đấu nên không bao giờ xong: không await
      await play(e, 4);
      expect(c.moves.length, 4);
      expect(c.fens.length, 5); // thế xuất phát + sau 4 nước
      expect(c.inReview, false);
      expect(c.shownPly, 4);

      c.stepBack();
      expect(c.shownPly, 3);
      expect(c.inReview, true);
      expect(c.shownBoard.at(4, 3), isNotNull); // Tốt ở cột 3 = thế sau 3 nước
      expect(c.shownBoard.at(4, 4), isNull);
      c.goStart();
      expect(c.shownPly, 0);
      expect(c.shownLastMoveFlats, isEmpty);
      expect(c.shownBoard.at(4, 0), isNotNull);
      c.stepForward();
      expect(c.shownPly, 1);
      expect(c.shownLastMoveFlats.length, 2); // tô nước thứ nhất

      // Ván vẫn tiếp tục: nước mới tới thì vẫn đang xem thế cũ.
      c.goToPly(2);
      await play(e, 2, 4);
      expect(c.moves.length, 6);
      expect(c.viewPly, 2);
      expect(c.shownBoard.at(4, 2), isNotNull);
      expect(c.shownBoard.at(4, 6), isNull);

      // Tiến tới nước mới nhất -> xem trực tiếp lại; chặn quá biên.
      c.goToPly(5);
      expect(c.inReview, true);
      c.stepForward();
      expect(c.inReview, false);
      expect(c.shownPly, 6);
      c.stepForward();
      expect(c.shownPly, 6);
      c.goToPly(-5);
      expect(c.shownPly, 0);
      c.goLive();
      expect(c.viewPly, isNull);
      c.goToPly(999);
      expect(c.viewPly, isNull);
      c.dispose();
    },
  );

  testWidgets('MoveStrip: bấm ô nước đi và các nút gọi đúng hàm', (
    tester,
  ) async {
    final calls = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Align(
            alignment: Alignment.bottomCenter,
            child: SizedBox(
              width: 600,
              child: MoveStrip(
                moves: const ['e2e4', 'e9e7', 'f1f3', 'f9f7'],
                shownPly: 2,
                live: false,
                onSelect: (p) => calls.add('chon$p'),
                onFirst: () => calls.add('dau'),
                onPrev: () => calls.add('lui'),
                onNext: () => calls.add('tien'),
                onLast: () => calls.add('cuoi'),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('2. f1f3'));
    await tester.tap(find.byIcon(Icons.first_page));
    await tester.tap(find.byIcon(Icons.chevron_left));
    await tester.tap(find.byIcon(Icons.chevron_right));
    await tester.tap(find.byIcon(Icons.last_page));
    expect(calls, ['chon3', 'dau', 'lui', 'tien', 'cuoi']);
  });

  testWidgets('màn hình tự đấu: phím mũi tên / Home / End / lăn chuột', (
    tester,
  ) async {
    final e = GatedEngine();
    final cfg = LaunchConfig.fromArgs(const ['--self-play']);
    await tester.pumpWidget(
      MaterialApp(
        home: BoardScreen(config: cfg, engineFactory: (_) => e),
      ),
    );
    // Vòng tự đấu chạy trong vùng FakeAsync của test: mỗi bước = thả nước + pump.
    for (int i = 0; i < 3; i++) {
      await tester.pump();
      e.release('a${i + 1}a${i + 2}');
      await tester.pump();
      await tester.pump();
    }
    expect(find.text('1. a1a2'), findsOneWidget);
    expect(find.textContaining('xem lại'), findsNothing);

    await tester.sendKeyEvent(LogicalKeyboardKey.arrowLeft);
    await tester.pump();
    expect(find.textContaining('sau nửa nước 2/3'), findsOneWidget);
    await tester.sendKeyEvent(LogicalKeyboardKey.home);
    await tester.pump();
    expect(find.textContaining('sau nửa nước 0/3'), findsOneWidget);
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
    await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
    await tester.pump();
    expect(find.textContaining('sau nửa nước 2/3'), findsOneWidget);

    // Lăn chuột lên trên bàn = lùi; xuống = tiến.
    final p = TestPointer(1, PointerDeviceKind.mouse);
    await tester.sendEventToBinding(
      p.hover(tester.getCenter(find.byType(AspectRatio))),
    );
    await tester.sendEventToBinding(p.scroll(const Offset(0, -20)));
    await tester.pump();
    expect(find.textContaining('sau nửa nước 1/3'), findsOneWidget);
    await tester.sendEventToBinding(p.scroll(const Offset(0, 20)));
    await tester.pump();
    expect(find.textContaining('sau nửa nước 2/3'), findsOneWidget);

    // Bấm ô nước đi; rồi End -> về thời gian thực.
    await tester.tap(find.text('1. a1a2'));
    await tester.pump();
    expect(find.textContaining('sau nửa nước 1/3'), findsOneWidget);
    await tester.sendKeyEvent(LogicalKeyboardKey.end);
    await tester.pump();
    expect(find.textContaining('xem lại'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });
}
