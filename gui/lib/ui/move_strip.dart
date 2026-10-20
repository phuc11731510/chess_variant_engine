import 'package:flutter/material.dart';

/// Thanh nước đi của chế độ tự đấu: nút về đầu / lùi / tiến / về nước mới nhất và dải
/// nước đi cuộn ngang; bấm vào một nước thì bàn hiện thế SAU nước đó.
///
/// Các nút không nhận tiêu điểm bàn phím ([InkWell.canRequestFocus] = false) để phím
/// Space (tạm dừng) và các phím mũi tên vẫn do màn hình chính xử lý sau khi bấm nút.
class MoveStrip extends StatefulWidget {
  /// Mọi nước đã đi (UCI thật).
  final List<String> moves;

  /// Nửa nước đang hiện trên bàn (0 = thế xuất phát, moves.length = mới nhất).
  final int shownPly;

  /// Đang xem trực tiếp (thế mới nhất, dải tự cuộn theo nước mới).
  final bool live;

  final ValueChanged<int> onSelect;
  final VoidCallback onFirst;
  final VoidCallback onPrev;
  final VoidCallback onNext;
  final VoidCallback onLast;

  const MoveStrip({
    super.key,
    required this.moves,
    required this.shownPly,
    required this.live,
    required this.onSelect,
    required this.onFirst,
    required this.onPrev,
    required this.onNext,
    required this.onLast,
  });

  @override
  State<MoveStrip> createState() => _MoveStripState();
}

class _MoveStripState extends State<MoveStrip> {
  static const double _extent = 92; // bề rộng mỗi ô nước đi
  static const double _height = 34;
  final ScrollController _sc = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollToShown();
  }

  @override
  void didUpdateWidget(MoveStrip old) {
    super.didUpdateWidget(old);
    if (old.shownPly != widget.shownPly ||
        old.moves.length != widget.moves.length) {
      _scrollToShown();
    }
  }

  @override
  void dispose() {
    _sc.dispose();
    super.dispose();
  }

  /// Cuộn để ô của nước đang hiện nằm giữa dải (nước mới nhất thì sát mép phải).
  void _scrollToShown() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_sc.hasClients) return;
      final pos = _sc.position;
      final idx = widget.shownPly - 1; // ô của nước dẫn tới thế đang hiện
      var target = idx < 0
          ? 0.0
          : idx * _extent - (pos.viewportDimension - _extent) / 2;
      target = target.clamp(0.0, pos.maxScrollExtent).toDouble();
      if ((pos.pixels - target).abs() > 0.5) _sc.jumpTo(target);
    });
  }

  Widget _btn(IconData icon, String tip, VoidCallback onTap, bool enabled) {
    return Tooltip(
      message: tip,
      child: InkWell(
        canRequestFocus: false,
        onTap: enabled ? onTap : null,
        child: SizedBox(
          width: _height,
          height: _height,
          child: Icon(
            icon,
            size: 22,
            color: enabled ? Colors.white70 : Colors.white24,
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final n = widget.moves.length;
    final p = widget.shownPly;
    return Container(
      height: _height,
      color: const Color(0xFF262421),
      child: Row(
        children: [
          _btn(
            Icons.first_page,
            'Về thế xuất phát (Home)',
            widget.onFirst,
            p > 0,
          ),
          _btn(Icons.chevron_left, 'Lùi một nước (←)', widget.onPrev, p > 0),
          _btn(Icons.chevron_right, 'Tiến một nước (→)', widget.onNext, p < n),
          _btn(Icons.last_page, 'Về nước mới nhất (End)', widget.onLast, p < n),
          Expanded(
            child: n == 0
                ? const Align(
                    alignment: Alignment.centerLeft,
                    child: Padding(
                      padding: EdgeInsets.only(left: 8),
                      child: Text(
                        'chưa có nước đi',
                        style: TextStyle(color: Colors.white38, fontSize: 12),
                      ),
                    ),
                  )
                : ListView.builder(
                    controller: _sc,
                    scrollDirection: Axis.horizontal,
                    itemExtent: _extent,
                    itemCount: n,
                    itemBuilder: (context, i) {
                      final white = i % 2 == 0;
                      final selected = i + 1 == p;
                      final label = white
                          ? '${i ~/ 2 + 1}. ${widget.moves[i]}'
                          : widget.moves[i];
                      return InkWell(
                        canRequestFocus: false,
                        onTap: () => widget.onSelect(i + 1),
                        child: Container(
                          alignment: Alignment.center,
                          margin: const EdgeInsets.symmetric(
                            horizontal: 1,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: selected
                                ? const Color(0xFF8A6D1F)
                                : (white
                                      ? const Color(0xFF34322F)
                                      : const Color(0xFF2C2A27)),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: FittedBox(
                            fit: BoxFit.scaleDown,
                            child: Text(
                              label,
                              style: TextStyle(
                                color: selected ? Colors.white : Colors.white70,
                                fontSize: 12,
                                fontFamily: 'Consolas',
                                fontWeight: selected
                                    ? FontWeight.bold
                                    : FontWeight.normal,
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}
