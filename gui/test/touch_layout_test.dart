// Giao diện cảm ứng (Android) của màn hình xem ván: thanh công cụ, bố cục ngang / dọc, ngăn kéo danh sách ván và bảng
// tìm kiếm, vuốt ngang để lùi / tiến nước, chuẩn bị nhật ký khi mở ván.

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/config/launch_config.dart';
import 'package:fairyzero_gui/engine/engine_service.dart';
import 'package:fairyzero_gui/main.dart';
import 'package:fairyzero_gui/ui/game_picker.dart';
import 'package:fairyzero_gui/ui/search_panel.dart';

/// Engine giả: thế sau k nước là [fen]; nước hợp lệ ở thế k là đúng nước thứ k của [script].
class _Engine implements EngineService {
  final List<String> script;
  int applied = 0;
  _Engine(this.script);
  static const fen = 'k9/10/10/10/10/10/10/10/10/K9 w - - 8+8 0 1';

  @override
  Future<void> start() async {}
  @override
  Future<void> newGame({String? fen}) async => applied = 0;
  @override
  Future<void> applyMove(String uci) async => applied++;
  @override
  Future<List<String>> legalMoves() async =>
      applied < script.length ? [script[applied]] : [];
  @override
  Future<String> currentFen() async => fen;
  @override
  Future<GameResult> gameResult() async =>
      applied >= script.length ? GameResult.white : GameResult.undecided;
  @override
  Future<String> bestMove() async => throw StateError('xem lại không tìm nước');
  @override
  Future<void> dispose() async {}
}

const _tsv =
    'so\ttep\tnua_nuoc\tket_qua\tquan_trang\tquan_den\tly_do\tghi_chu\n'
    '0\tvan_0000.txt\t3\tW\t2\t2\tno_moves\t\n'
    '1\tvan_0001.txt\t3\tB\t2\t2\tchecks\t\n';

Directory _lib() {
  final dir = Directory.systemTemp.createTempSync('fz_touch_');
  File('${dir.path}/chi_muc.tsv').writeAsStringSync(_tsv);
  File('${dir.path}/van_0000.txt').writeAsStringSync('a1a2 a10a9 a2a3\n');
  // Ván 1 chỉ được ghi khi "prepare" chạy (như nhật ký lười của Android).
  return dir;
}

Future<void> _pump(
  WidgetTester tester,
  Size size,
  Directory dir,
  List<int> prepared,
) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    MaterialApp(
      home: BoardScreen(
        config: LaunchConfig(enginePath: '', replayDir: dir.path),
        engineFactory: (_) => _Engine(['a1a2', 'a10a9', 'a2a3']),
        touchUi: true,
        prepareGame: (e) {
          prepared.add(e.id);
          File(
            '${dir.path}/van_${e.id.toString().padLeft(4, '0')}.txt',
          ).writeAsStringSync('a1a2 a10a9 a2a3\n');
        },
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
    'cảm ứng, màn hình ngang: bảng tìm kiếm cạnh bàn, danh sách ván là ngăn kéo',
    (tester) async {
      final prepared = <int>[];
      final dir = _lib();
      await _pump(tester, const Size(1340, 800), dir, prepared);
      expect(
        find.byType(SearchPanel),
        findsOneWidget,
        reason: 'đủ chỗ cạnh bàn',
      );
      expect(find.byIcon(Icons.analytics_outlined), findsNothing);
      expect(find.text('Ván'), findsOneWidget, reason: 'nút mở danh sách ván');
      expect(find.byType(GamePicker), findsNothing);
      expect(prepared, [0], reason: 'ván đầu được chuẩn bị khi mở');

      await tester.tap(find.text('Ván'));
      await tester.pumpAndSettle();
      expect(find.byType(GamePicker), findsOneWidget);
      await tester.tap(find.textContaining('#1').first);
      await tester.pumpAndSettle();
      expect(prepared, [
        0,
        1,
      ], reason: 'chọn ván 1 trong ngăn kéo thì chuẩn bị nhật ký của nó');
      expect(
        find.byType(GamePicker),
        findsNothing,
        reason: 'chọn xong ngăn kéo đóng',
      );
      expect(find.textContaining('Ván #1'), findsWidgets);
    },
  );

  testWidgets(
    'cảm ứng, màn hình dọc cao: bảng tìm kiếm nằm DƯỚI bàn, danh sách ván là ngăn kéo; vuốt ngang trên bàn lướt nước',
    (tester) async {
      final prepared = <int>[];
      final dir = _lib();
      await _pump(tester, const Size(800, 1340), dir, prepared);
      expect(find.byType(SearchPanel), findsOneWidget);
      expect(find.byIcon(Icons.analytics_outlined), findsNothing);
      expect(find.text('Ván'), findsOneWidget);
      final board = tester.getRect(find.byType(AspectRatio).first);
      final panel = tester.getRect(find.byType(SearchPanel));
      expect(
        panel.top,
        greaterThanOrEqualTo(board.bottom),
        reason: 'bảng nằm phía dưới bàn',
      );
      expect(panel.height, greaterThan(170));
      expect(board.top, lessThan(120), reason: 'bàn sát phía trên (dưới thanh công cụ)');

      expect(find.textContaining('nửa nước 0/3'), findsOneWidget);
      // Vuốt sang trái = tiến một nước; sang phải = lùi.
      await tester.fling(
        find.byType(AspectRatio).first,
        const Offset(-300, 0),
        1500,
      );
      await tester.pumpAndSettle();
      expect(find.textContaining('nửa nước 1/3'), findsOneWidget);
      await tester.fling(
        find.byType(AspectRatio).first,
        const Offset(300, 0),
        1500,
      );
      await tester.pumpAndSettle();
      expect(find.textContaining('nửa nước 0/3'), findsOneWidget);
    },
  );

  testWidgets(
    'cảm ứng, màn hình dọc thấp (không đủ chỗ dưới bàn): bảng tìm kiếm là ngăn kéo bên phải',
    (tester) async {
      final prepared = <int>[];
      final dir = _lib();
      await _pump(tester, const Size(800, 900), dir, prepared);
      expect(find.byType(SearchPanel), findsNothing);
      expect(find.byIcon(Icons.analytics_outlined), findsOneWidget);
      await tester.tap(find.byIcon(Icons.analytics_outlined));
      await tester.pumpAndSettle();
      expect(find.byType(SearchPanel), findsOneWidget);
    },
  );

  testWidgets('cảm ứng: nút tự chạy bật / tắt', (tester) async {
    final prepared = <int>[];
    final dir = _lib();
    await _pump(tester, const Size(800, 1340), dir, prepared);
    expect(find.byIcon(Icons.play_arrow), findsOneWidget);
    await tester.tap(find.byIcon(Icons.play_arrow));
    await tester.pump();
    expect(find.byIcon(Icons.pause), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 1100));
    expect(find.textContaining('nửa nước 1/3'), findsOneWidget);
    await tester.tap(find.byIcon(Icons.pause));
    await tester.pump();
    expect(find.byIcon(Icons.play_arrow), findsOneWidget);
  });
}
