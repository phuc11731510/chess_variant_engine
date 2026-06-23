// Smoke test M0: app dựng được và parse cờ lệnh.

import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/config/launch_config.dart';
import 'package:fairyzero_gui/main.dart';

void main() {
  testWidgets('M0: app hien tieu de va bang cau hinh', (WidgetTester tester) async {
    final config = LaunchConfig.fromArgs(const []);
    await tester.pumpWidget(FairyZeroApp(config: config));

    expect(find.text('FairyZero — M0'), findsOneWidget);
    expect(find.textContaining('LaunchConfig:'), findsOneWidget);
  });

  test('LaunchConfig parse co lenh', () {
    final c = LaunchConfig.fromArgs(
      '--engine e.exe --model m.onnx --provider dml --visits 800 --black'.split(' '),
    );
    expect(c.enginePath, 'e.exe');
    expect(c.modelPath, 'm.onnx');
    expect(c.provider, 'dml');
    expect(c.visits, 800);
    expect(c.humanPlaysWhite, false);

    // Mac dinh: khong dat gi -> cpu + movetime mac dinh + cam Trang.
    final d = LaunchConfig.fromArgs(const []);
    expect(d.provider, 'cpu');
    expect(d.movetimeMs, LaunchConfig.defaultMovetimeMs);
    expect(d.humanPlaysWhite, true);
  });
}
