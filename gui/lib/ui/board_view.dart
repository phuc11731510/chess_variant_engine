import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../domain/board_state.dart';
import 'board_painter.dart';
import 'piece_assets.dart';

/// Bàn cờ 10×10: nền (BoardPainter) + lớp tô sáng + lớp quân (SVG) + nhận chạm.
///
/// [flipped] = true khi người cầm Đen (lật bàn). [selectedFlat] = ô đang chọn
/// (rank*10+file) hoặc null. [targetFlats] = các ô đích hợp lệ. [onTapSquare]
/// gọi với toạ độ BÀN CỜ (r=rank, f=file).
class BoardView extends StatelessWidget {
  final BoardState board;
  final bool flipped;
  final int? selectedFlat;
  final Set<int> targetFlats;
  final void Function(int r, int f)? onTapSquare;

  const BoardView({
    super.key,
    required this.board,
    this.flipped = false,
    this.selectedFlat,
    this.targetFlats = const {},
    this.onTapSquare,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final side = constraints.biggest.shortestSide;
        final cell = side / 10;

        final children = <Widget>[
          SizedBox(
            width: side,
            height: side,
            child: CustomPaint(painter: BoardPainter(flipped: flipped)),
          ),
          SizedBox(
            width: side,
            height: side,
            child: CustomPaint(
              painter: HighlightPainter(
                board: board,
                selectedFlat: selectedFlat,
                targets: targetFlats,
                flipped: flipped,
              ),
            ),
          ),
        ];

        for (int r = 0; r < 10; r++) {
          for (int f = 0; f < 10; f++) {
            final piece = board.at(r, f);
            if (piece == null) continue;
            final row = flipped ? r : 9 - r;
            final col = flipped ? 9 - f : f;
            final royalLabel = PieceAssets.isRoyal(piece.letter)
                ? (piece.isWhite ? board.whiteRoyalChecks : board.blackRoyalChecks)
                : null;
            children.add(Positioned(
              left: col * cell,
              top: row * cell,
              width: cell,
              height: cell,
              child: PieceWidget(
                piece: piece,
                size: cell,
                royalCheckLabel: royalLabel,
              ),
            ));
          }
        }

        return SizedBox(
          width: side,
          height: side,
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTapUp: onTapSquare == null
                ? null
                : (d) {
                    final col = (d.localPosition.dx / cell).floor().clamp(0, 9);
                    final row = (d.localPosition.dy / cell).floor().clamp(0, 9);
                    final r = flipped ? row : 9 - row;
                    final f = flipped ? 9 - col : col;
                    onTapSquare!(r, f);
                  },
            child: Stack(children: children),
          ),
        );
      },
    );
  }
}

/// Lớp tô sáng: ô đang chọn (vàng) + ô đích hợp lệ (chấm tròn; vòng nếu là ăn quân).
class HighlightPainter extends CustomPainter {
  final BoardState board;
  final int? selectedFlat;
  final Set<int> targets;
  final bool flipped;

  const HighlightPainter({
    required this.board,
    required this.selectedFlat,
    required this.targets,
    required this.flipped,
  });

  Offset _topLeft(int r, int f, double cell) {
    final row = flipped ? r : 9 - r;
    final col = flipped ? 9 - f : f;
    return Offset(col * cell, row * cell);
  }

  @override
  void paint(Canvas canvas, Size size) {
    final cell = size.width / 10;

    if (selectedFlat != null) {
      final r = selectedFlat! ~/ 10, f = selectedFlat! % 10;
      final tl = _topLeft(r, f, cell);
      canvas.drawRect(
        tl & Size(cell, cell),
        Paint()..color = const Color(0x80F6F669), // vàng nhạt
      );
    }

    for (final t in targets) {
      final r = t ~/ 10, f = t % 10;
      final center = _topLeft(r, f, cell) + Offset(cell / 2, cell / 2);
      final isCapture = board.at(r, f) != null;
      final paint = Paint()..color = const Color(0x33000000);
      if (isCapture) {
        paint
          ..style = PaintingStyle.stroke
          ..strokeWidth = cell * 0.09;
        canvas.drawCircle(center, cell * 0.45, paint);
      } else {
        canvas.drawCircle(center, cell * 0.16, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant HighlightPainter old) =>
      old.selectedFlat != selectedFlat ||
      old.targets != targets ||
      old.flipped != flipped ||
      !identical(old.board, board);
}

/// Một quân SVG căn giữa ô. Quân royal (vua) được dán [PieceAssets.royalSymbol]
/// ở góc dưới-phải và (nếu có) số chiếu còn lại in mờ trên mặt.
class PieceWidget extends StatelessWidget {
  final Piece piece;
  final double size;
  final int? royalCheckLabel;

  const PieceWidget({
    super.key,
    required this.piece,
    required this.size,
    this.royalCheckLabel,
  });

  @override
  Widget build(BuildContext context) {
    final pad = size * 0.04;
    final svg = SvgPicture.asset(
      PieceAssets.assetFor(piece.letter),
      fit: BoxFit.contain,
    );

    if (!PieceAssets.isRoyal(piece.letter)) {
      return Padding(padding: EdgeInsets.all(pad), child: svg);
    }

    final symSize = size * 0.40;
    return Padding(
      padding: EdgeInsets.all(pad),
      child: Stack(
        children: [
          Positioned.fill(child: svg),
          // Số chiếu còn lại trước khi thua, in lên mặt General (alpha 0.80).
          // Vua Trắng: chữ #333333; vua Đen: #cccccc.
          if (royalCheckLabel != null)
            Align(
              alignment: const Alignment(0.0, -0.10),
              child: Text(
                '$royalCheckLabel',
                style: TextStyle(
                  fontSize: size * 0.52,
                  fontWeight: FontWeight.bold,
                  height: 1.0,
                  color: (piece.isWhite
                          ? const Color(0xFF333333)
                          : const Color(0xFFCCCCCC))
                      .withValues(alpha: 0.80),
                ),
              ),
            ),
          Positioned(
            right: 0,
            bottom: 0,
            width: symSize,
            height: symSize,
            child: SvgPicture.asset(
              PieceAssets.royalSymbol,
              fit: BoxFit.contain,
            ),
          ),
        ],
      ),
    );
  }
}
