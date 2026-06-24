// Golden test M3/M4: render bàn cờ ra PNG để kiểm tra trực quan.
// Tạo/đối chiếu ảnh: flutter test --update-goldens test/board_golden_test.dart
// LƯU Ý: môi trường test KHÔNG nạp font -> chữ (nhãn toạ độ, số chiếu) hiện thành
// Ô VUÔNG; chỉ xác nhận VỊ TRÍ. Glyph thật xác minh bằng chụp cửa sổ app.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/domain/board_state.dart';
import 'package:fairyzero_gui/domain/uci_move.dart';
import 'package:fairyzero_gui/ui/board_view.dart';

Future<void> _pumpBoard(
  WidgetTester tester, {
  required bool flipped,
  int? selectedFlat,
  Set<int> targets = const {},
}) async {
  await tester.runAsync(() async {
    await tester.pumpWidget(MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        backgroundColor: const Color(0xFF302E2B),
        body: Center(
          child: SizedBox(
            width: 600,
            height: 600,
            child: BoardView(
              board: BoardState.fromFen(kVariantStartposFen),
              flipped: flipped,
              selectedFlat: selectedFlat,
              targetFlats: targets,
            ),
          ),
        ),
      ),
    ));
    await Future<void>.delayed(const Duration(milliseconds: 800));
    await tester.pumpAndSettle();
  });
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('board startpos (white view)', (tester) async {
    await tester.binding.setSurfaceSize(const Size(640, 660));
    await _pumpBoard(tester, flipped: false);
    await expectLater(find.byType(BoardView),
        matchesGoldenFile('goldens/board_startpos_white.png'));
  });

  testWidgets('board startpos (black view / flipped)', (tester) async {
    await tester.binding.setSurfaceSize(const Size(640, 660));
    await _pumpBoard(tester, flipped: true);
    await expectLater(find.byType(BoardView),
        matchesGoldenFile('goldens/board_startpos_black.png'));
  });

  testWidgets('board voi o chon + o dich (tap-tap)', (tester) async {
    await tester.binding.setSurfaceSize(const Size(640, 660));
    await _pumpBoard(
      tester,
      flipped: false,
      selectedFlat: const Sq(1, 2).flat, // b3
      targets: {const Sq(1, 3).flat, const Sq(1, 4).flat}, // b4, b5
    );
    await expectLater(find.byType(BoardView),
        matchesGoldenFile('goldens/board_highlight.png'));
  });
}
