// Bảng tìm kiếm: cột %N, và cột %N^e khi chọn nhiệt độ (rê chuột vào tiêu đề %N).

import 'dart:math' as math;

import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/domain/search_record.dart';
import 'package:fairyzero_gui/ui/search_panel.dart';

const _log = '''
--- nửa nước 1 (trắng đi) → e2e4
position startpos
  depth 1 seldepth 1 multipv 1 nodes 1000 nps 0 time 0 pv e2e4
    e2e4 N 600 P 0.5 Q 0.10
    d2d4 N 300 P 0.3 Q 0.05
    c2c4 N 100 P 0.2 Q -0.10
''';

// Nhật ký dựng từ dữ liệu huấn luyện: không có P / Pnet, Q chỉ có ở nước đã đi và nước nhiều lượt nhất.
const _logHuanLuyen = '''
--- nửa nước 1 (trắng đi) → e2e4
position startpos
  depth 1 seldepth 1 multipv 1 wdl 500 0 500 nodes 1000 nps 0 time 0 pv e2e4
    e2e4 N 600 Q 0.1000
    d2d4 N 300
    c2c4 N 90
    b2b4 N 9
''';

Widget _panel({
  required double exponent,
  ValueChanged<double>? onChanged,
  String log = _log,
  double width = 520,
  bool compact = false,
  double textScale = 1,
}) {
  final rec = SearchRecord.parseLog(log)[0]!;
  return MaterialApp(
    builder: (context, child) => MediaQuery(
      data: MediaQuery.of(context).copyWith(textScaler: TextScaler.linear(textScale)),
      child: child!,
    ),
    home: Scaffold(
      body: SizedBox(
        width: width,
        height: 700,
        child: SearchPanel(
          record: rec,
          ply: 1,
          played: 'e2e4',
          whiteMoved: true,
          exponent: exponent,
          onExponentChanged: onChanged,
          compact: compact,
        ),
      ),
    ),
  );
}

void main() {
  test('temperatureShares: N^e / ΣN^e, đúng như engine (N / N_max)^(1/T)', () {
    final s2 = temperatureShares([600, 300, 100], 2);
    final sum2 = 600 * 600 + 300 * 300 + 100 * 100;
    expect(s2[0], closeTo(600 * 600 / sum2, 1e-12));
    expect(s2[1], closeTo(300 * 300 / sum2, 1e-12));
    expect(s2[2], closeTo(100 * 100 / sum2, 1e-12));
    expect(s2.fold<double>(0, (a, b) => a + b!), closeTo(1, 1e-12));

    // e = 1 giữ nguyên tỉ lệ lượt thăm; e lớn không tràn số và dồn vào nước nhiều lượt nhất.
    expect(temperatureShares([600, 300, 100], 1)[0], closeTo(0.6, 1e-12));
    final big = temperatureShares([60000, 30000, 100], 200);
    expect(big[0], closeTo(1, 1e-12));
    expect(big[1], lessThan(1e-50));
    // Nước không có số lượt (null) bị bỏ qua; mọi nước 0 lượt thì không có xác suất.
    expect(temperatureShares([600, null, 300], 2)[1], isNull);
    expect(temperatureShares([0, 0], 2), [null, null]);
    // e = 0,5 (T = 2) phẳng hơn tỉ lệ lượt thăm.
    expect(temperatureShares([600, 300, 100], 0.5)[2]!, greaterThan(0.1));
    // Khớp công thức của engine cho T = 0,5: (N / N_max)^2 chuẩn hoá.
    final w = [for (final n in [600, 300, 100]) math.pow(n / 600, 2)];
    final tot = w.reduce((a, b) => a + b);
    expect(s2[1], closeTo(w[1] / tot, 1e-12));
  });

  testWidgets('dữ liệu huấn luyện: không có cột P / Pnet (trống), có đủ mọi nước có lượt thăm và cột Q Trắng', (tester) async {
    await tester.pumpWidget(_panel(exponent: 1, log: _logHuanLuyen));
    expect(find.textContaining('Pnet'), findsNothing);
    expect(find.textContaining('Q Trắng'), findsOneWidget);
    for (final mv in ['e2e4', 'd2d4', 'c2c4', 'b2b4']) {
      expect(find.textContaining(mv), findsWidgets, reason: 'nước $mv có trong bảng');
    }
    expect(find.textContaining('+0.100'), findsOneWidget, reason: 'Q của nước đã đi, phía Trắng');
    expect(find.textContaining('chỉ lưu Q của nước đã đi'), findsOneWidget);
  });

  testWidgets('bảng hẹp (điện thoại xoay ngang, cỡ chữ lớn): cột Q Trắng nằm trong bảng, không tràn', (tester) async {
    for (final scale in [1.0, 1.4]) {
      for (final exponent in [1.0, 2.0]) {
        for (final log in [_log, _logHuanLuyen]) {
          await tester.pumpWidget(_panel(exponent: exponent, log: log, width: 250, compact: true, textScale: scale));
          expect(tester.takeException(), isNull, reason: 'không tràn (scale $scale, e $exponent)');
          final q = tester.getRect(find.textContaining('Q Trắng'));
          expect(q.right, lessThanOrEqualTo(250.0 + 0.5), reason: 'cột Q Trắng trong bảng (scale $scale, e $exponent)');
          expect(q.left, greaterThanOrEqualTo(0));
        }
      }
    }
  });

  testWidgets('chỉ cột %N khi chưa chọn nhiệt độ; không có cột %N^e', (tester) async {
    await tester.pumpWidget(_panel(exponent: 1));
    expect(find.byKey(const ValueKey('tieu_de_pct_n')), findsOneWidget);
    expect(find.byKey(const ValueKey('tieu_de_pct_nt')), findsNothing);
    expect(find.textContaining('60.0'), findsOneWidget); // 600/1000
    expect(find.textContaining('30.0'), findsOneWidget);
  });

  testWidgets('chọn %N^2: thêm cột với xác suất N² / ΣN² (78.3 / 19.6 / 2.2)', (tester) async {
    await tester.pumpWidget(_panel(exponent: 2));
    expect(find.byKey(const ValueKey('tieu_de_pct_nt')), findsOneWidget);
    expect(find.textContaining('%N^2'), findsWidgets);
    expect(find.textContaining('78.3'), findsOneWidget);
    expect(find.textContaining('19.6'), findsOneWidget);
    expect(find.textContaining('2.2'), findsOneWidget);
    // cột %N gốc vẫn còn để so sánh
    expect(find.textContaining('60.0'), findsOneWidget);
  });

  testWidgets('rê chuột vào tiêu đề %N hiện menu, chọn %N^2 báo exponent 2, chuột rời thì menu ẩn', (tester) async {
    final picked = <double>[];
    await tester.pumpWidget(_panel(exponent: 1, onChanged: picked.add));
    final gesture = await tester.createGesture(kind: PointerDeviceKind.mouse);
    await gesture.addPointer(location: Offset.zero);
    addTearDown(gesture.removePointer);
    await tester.pump();
    expect(find.byKey(const ValueKey('nhiet_do_2')), findsNothing);

    await gesture.moveTo(tester.getCenter(find.byKey(const ValueKey('tieu_de_pct_n'))));
    await tester.pump();
    expect(find.byKey(const ValueKey('nhiet_do_2')), findsOneWidget, reason: 'menu hiện khi rê chuột vào %N');
    expect(find.byKey(const ValueKey('nhiet_do_4')), findsOneWidget);
    expect(find.byKey(const ValueKey('nhiet_do_0.5')), findsOneWidget);
    expect(find.textContaining('như sinh dữ liệu và arena'), findsOneWidget);

    // Đưa chuột sang menu (qua khe giữa) rồi bấm: menu không biến mất giữa chừng.
    await gesture.moveTo(tester.getCenter(find.byKey(const ValueKey('nhiet_do_2'))));
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.byKey(const ValueKey('nhiet_do_2')), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('nhiet_do_2')));
    await tester.pump();
    expect(picked, [2.0]);
    expect(find.byKey(const ValueKey('nhiet_do_2')), findsNothing, reason: 'chọn xong thì đóng menu');

    // Mở lại rồi đưa chuột ra xa: menu tự ẩn sau một lúc.
    await gesture.moveTo(tester.getCenter(find.byKey(const ValueKey('tieu_de_pct_n'))));
    await tester.pump();
    expect(find.byKey(const ValueKey('nhiet_do_4')), findsOneWidget);
    await gesture.moveTo(const Offset(5, 690));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.byKey(const ValueKey('nhiet_do_4')), findsNothing);
  });
}
