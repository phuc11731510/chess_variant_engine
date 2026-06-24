import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../domain/board_state.dart';
import 'board_painter.dart';
import 'piece_assets.dart';

/// Bàn cờ 10×10: nền + tô sáng + quân (SVG) + nhận chạm VÀ kéo-thả.
///
/// Hỗ trợ cả **chạm-chạm** (onTapSquare) lẫn **kéo-thả** (onDragStart/End):
/// GestureDetector phân xử — chạm tại chỗ → tap; di chuyển → kéo.
class BoardView extends StatefulWidget {
  final BoardState board;
  final bool flipped;
  final int? selectedFlat;
  final Set<int> targetFlats;
  final void Function(int r, int f)? onTapSquare;

  // Bảng chọn phong cấp.
  final int? promoSquare;
  final List<String> promoOptions;
  final bool playerIsWhite;
  final void Function(String letter)? onPickPromotion;

  // Kéo-thả. onDragStart trả về true nếu được phép nhấc quân ở ô đó.
  final bool Function(int r, int f)? onDragStart;
  final void Function(int r, int f)? onDragEnd;
  final VoidCallback? onDragCancel;

  const BoardView({
    super.key,
    required this.board,
    this.flipped = false,
    this.selectedFlat,
    this.targetFlats = const {},
    this.onTapSquare,
    this.promoSquare,
    this.promoOptions = const [],
    this.playerIsWhite = true,
    this.onPickPromotion,
    this.onDragStart,
    this.onDragEnd,
    this.onDragCancel,
  });

  @override
  State<BoardView> createState() => _BoardViewState();
}

class _BoardViewState extends State<BoardView> {
  /// Ô đang được nhấc lên kéo (file,rank), hoặc null.
  ({int f, int r})? _dragFrom;

  /// Vị trí con trỏ (local) khi kéo — chỉ lớp quân-đang-kéo lắng nghe để khỏi
  /// rebuild cả bàn mỗi khung hình.
  final ValueNotifier<Offset?> _dragPos = ValueNotifier(null);

  double _cell = 1;

  /// Lệch giữa con trỏ và góc trên-trái ô lúc bắt đầu kéo. Giữ nguyên suốt quá
  /// trình kéo để quân KHÔNG "nhảy" về tâm con trỏ (giữ đúng điểm bạn đã bấm).
  Offset _grabOffset = Offset.zero;

  @override
  void dispose() {
    _dragPos.dispose();
    super.dispose();
  }

  ({int r, int f}) _toBoard(Offset local) {
    final col = (local.dx / _cell).floor().clamp(0, 9);
    final row = (local.dy / _cell).floor().clamp(0, 9);
    final r = widget.flipped ? row : 9 - row;
    final f = widget.flipped ? 9 - col : col;
    return (r: r, f: f);
  }

  void _panStart(DragStartDetails d) {
    final p = _toBoard(d.localPosition);
    final ok = widget.onDragStart?.call(p.r, p.f) ?? false;
    if (ok) {
      // Lưu lệch chuột↔ô để giữ nguyên điểm bấm (không dính tâm con trỏ).
      final row = widget.flipped ? p.r : 9 - p.r;
      final col = widget.flipped ? 9 - p.f : p.f;
      _grabOffset = d.localPosition - Offset(col * _cell, row * _cell);
      setState(() => _dragFrom = (f: p.f, r: p.r));
      _dragPos.value = d.localPosition;
    }
  }

  void _panUpdate(DragUpdateDetails d) {
    if (_dragFrom == null) return;
    _dragPos.value = d.localPosition;
  }

  void _panEnd(DragEndDetails d) {
    if (_dragFrom == null) return;
    final pos = _dragPos.value;
    setState(() => _dragFrom = null);
    _dragPos.value = null;
    if (pos != null) {
      final p = _toBoard(pos);
      widget.onDragEnd?.call(p.r, p.f);
    } else {
      widget.onDragCancel?.call();
    }
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final side = constraints.biggest.shortestSide;
        _cell = side / 10;
        final cell = _cell;
        final board = widget.board;
        final flipped = widget.flipped;

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
                selectedFlat: widget.selectedFlat,
                targets: widget.targetFlats,
                flipped: flipped,
              ),
            ),
          ),
        ];

        // Quân tĩnh (bỏ qua quân đang được kéo để khỏi vẽ trùng).
        for (int r = 0; r < 10; r++) {
          for (int f = 0; f < 10; f++) {
            final piece = board.at(r, f);
            if (piece == null) continue;
            if (_dragFrom != null && _dragFrom!.r == r && _dragFrom!.f == f) {
              continue;
            }
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

        // Bảng chọn phong cấp (nổi trên bàn, cột chạy từ ô đích về phía người chơi).
        if (widget.promoSquare != null && widget.promoOptions.isNotEmpty) {
          children.add(Positioned.fill(
            child: GestureDetector(
              onTap: () => widget.onPickPromotion?.call(''),
              child: Container(color: const Color(0x88000000)),
            ),
          ));
          final pr = widget.promoSquare! ~/ 10, pf = widget.promoSquare! % 10;
          final pcol = flipped ? 9 - pf : pf;
          final prow = flipped ? pr : 9 - pr;
          final n = widget.promoOptions.length;
          final startRow = (prow + n <= 10) ? prow : (10 - n);
          for (int k = 0; k < n; k++) {
            final letter = widget.promoOptions[k];
            final disp = widget.playerIsWhite
                ? letter.toUpperCase()
                : letter.toLowerCase();
            children.add(Positioned(
              left: pcol * cell,
              top: (startRow + k) * cell,
              width: cell,
              height: cell,
              child: GestureDetector(
                onTap: () => widget.onPickPromotion?.call(letter),
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    border: Border.all(color: Colors.black26),
                  ),
                  child: Padding(
                    padding: EdgeInsets.all(cell * 0.06),
                    child: SvgPicture.asset(
                      PieceAssets.assetFor(disp),
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
              ),
            ));
          }
        }

        // Quân đang kéo (bám con trỏ) — chỉ lớp này rebuild mỗi khung hình.
        if (_dragFrom != null) {
          final dp = board.at(_dragFrom!.r, _dragFrom!.f);
          if (dp != null) {
            children.add(ValueListenableBuilder<Offset?>(
              valueListenable: _dragPos,
              builder: (context, pos, _) {
                if (pos == null) return const SizedBox.shrink();
                return Positioned(
                  left: pos.dx - _grabOffset.dx,
                  top: pos.dy - _grabOffset.dy,
                  width: cell,
                  height: cell,
                  child: IgnorePointer(
                    child: PieceWidget(piece: dp, size: cell),
                  ),
                );
              },
            ));
          }
        }

        return SizedBox(
          width: side,
          height: side,
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTapUp: widget.onTapSquare == null
                ? null
                : (d) {
                    final p = _toBoard(d.localPosition);
                    widget.onTapSquare!(p.r, p.f);
                  },
            onPanStart: widget.onDragStart == null ? null : _panStart,
            onPanUpdate: widget.onDragStart == null ? null : _panUpdate,
            onPanEnd: widget.onDragStart == null ? null : _panEnd,
            child: Stack(children: children),
          ),
        );
      },
    );
  }
}

/// Lớp tô sáng: ô đang chọn (vàng) + ô đích hợp lệ (chấm tròn; vòng nếu ăn quân).
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
        Paint()..color = const Color(0x80F6F669),
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
/// ở góc dưới-phải và (nếu có) số chiếu còn lại in trên mặt.
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
