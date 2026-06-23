import 'package:flutter/material.dart';

import 'config/launch_config.dart';

/// FairyZero GUI — điểm vào.
///
/// M0: đọc cờ lệnh -> [LaunchConfig], in ra (stdout + cửa sổ), mở một cửa sổ
/// trống có sẵn preview màu bàn cờ chuẩn chess.com. Bàn cờ thật + nối engine là
/// các mốc sau (M2+).
void main(List<String> args) {
  final config = LaunchConfig.fromArgs(args);
  // In ra terminal để kiểm tra M0 (hiện khi chạy `flutter run` hoặc mở từ terminal).
  // ignore: avoid_print
  print(config.toString());
  runApp(FairyZeroApp(config: config));
}

class FairyZeroApp extends StatelessWidget {
  final LaunchConfig config;
  const FairyZeroApp({super.key, required this.config});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FairyZero',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(useMaterial3: true, brightness: Brightness.dark),
      home: M0Screen(config: config),
    );
  }
}

/// Màn hình M0: nền tối + preview bàn cờ (màu chess.com) + bảng cấu hình.
class M0Screen extends StatelessWidget {
  final LaunchConfig config;
  const M0Screen({super.key, required this.config});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF302E2B),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'FairyZero — M0',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            const Text(
              'Khung Flutter chay duoc. Ban co that o moc M3.',
              style: TextStyle(color: Colors.white60, fontSize: 12),
            ),
            const SizedBox(height: 20),
            // Preview 8x8 bang dung mau chess.com -> xac nhan hang so mau cho M3.
            SizedBox(
              width: 200,
              height: 200,
              child: CustomPaint(painter: _CheckerPreviewPainter()),
            ),
            const SizedBox(height: 20),
            // Bang cau hinh da parse tu co lenh.
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.30),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                config.toString(),
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 13,
                  color: Colors.white,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Vẽ một lưới 8x8 bằng đúng hai màu ô của chess.com để kiểm tra hằng số màu.
class _CheckerPreviewPainter extends CustomPainter {
  // Hai màu này sẽ dùng lại cho BoardPainter ở M3.
  static const Color light = Color(0xFFEEEED2);
  static const Color dark = Color(0xFF769656);

  @override
  void paint(Canvas canvas, Size size) {
    const n = 8;
    final cell = size.width / n;
    final paint = Paint();
    for (int r = 0; r < n; r++) {
      for (int c = 0; c < n; c++) {
        paint.color = ((r + c) % 2 == 0) ? light : dark;
        canvas.drawRect(
          Rect.fromLTWH(c * cell, r * cell, cell, cell),
          paint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
