import 'package:flutter/material.dart';

/// Vẽ nền lưới 10×10 (màu chess.com) + nhãn toạ độ (số hàng mép trái, chữ cột
/// mép dưới) theo phong cách chess.com: nhãn dùng MÀU Ô ĐỐI DIỆN để tương phản.
class BoardPainter extends CustomPainter {
  static const Color light = Color(0xFFEEEED2);
  static const Color dark = Color(0xFF769656);

  /// true = lật bàn (người cầm Đen): hàng/cột hiển thị đảo lại.
  final bool flipped;

  const BoardPainter({this.flipped = false});

  @override
  void paint(Canvas canvas, Size size) {
    final cell = size.width / 10;
    final paint = Paint();
    final fs = cell * 0.22;
    final pad = cell * 0.06;

    for (int row = 0; row < 10; row++) {
      for (int col = 0; col < 10; col++) {
        // a1 (default: row 9, col 0) -> (9+0) lẻ -> ô tối, đúng chess.com.
        final isDark = (row + col) % 2 == 1;
        paint.color = isDark ? dark : light;
        canvas.drawRect(Rect.fromLTWH(col * cell, row * cell, cell, cell), paint);

        final labelColor = isDark ? light : dark; // tương phản với ô

        // Số HÀNG: cột ngoài cùng trái, góc trên-trái.
        if (col == 0) {
          final rank = flipped ? (row + 1) : (10 - row);
          _text(canvas, '$rank', labelColor, fs,
              Offset(col * cell + pad, row * cell + pad));
        }
        // Chữ CỘT: hàng dưới cùng, góc dưới-phải.
        if (row == 9) {
          final fileIdx = flipped ? (9 - col) : col;
          final letter = String.fromCharCode('a'.codeUnitAt(0) + fileIdx);
          _text(canvas, letter, labelColor, fs,
              Offset((col + 1) * cell - pad, (row + 1) * cell - pad),
              rightAlign: true, bottomAlign: true);
        }
      }
    }
  }

  void _text(Canvas canvas, String s, Color color, double fontSize, Offset at,
      {bool rightAlign = false, bool bottomAlign = false}) {
    final tp = TextPainter(
      text: TextSpan(
        text: s,
        style: TextStyle(
            color: color, fontSize: fontSize, fontWeight: FontWeight.bold),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    var dx = at.dx, dy = at.dy;
    if (rightAlign) dx -= tp.width;
    if (bottomAlign) dy -= tp.height;
    tp.paint(canvas, Offset(dx, dy));
  }

  @override
  bool shouldRepaint(covariant BoardPainter oldDelegate) =>
      oldDelegate.flipped != flipped;
}
