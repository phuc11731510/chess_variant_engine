import 'package:flutter/material.dart';

import '../domain/search_record.dart';

/// Bảng bên phải bàn cờ (tự đấu / xem lại): lần tìm kiếm MCTS đã chọn nước đang xem —
/// số lượt tìm N, prior P của mạng, giá trị Q, WDL, điểm cp và biến chính của từng nước
/// engine cân nhắc. Q / cp / WDL đổi sang phía TRẮNG (dương = Trắng có lợi); nhật ký gốc
/// (theo phía bên đi, đúng như engine in) xem ở mục cuối.
class SearchPanel extends StatelessWidget {
  /// Lần tìm của nước đang xem (null: thế xuất phát hoặc không có nhật ký).
  final SearchRecord? record;

  /// Nửa nước đang xem (1 = nước đầu; 0 = thế xuất phát).
  final int ply;

  /// Nước đã đi ở nửa nước này (null ở thế xuất phát).
  final String? played;

  /// Trắng là bên đi nước này.
  final bool whiteMoved;

  const SearchPanel({
    super.key,
    required this.record,
    required this.ply,
    required this.played,
    required this.whiteMoved,
  });

  static const _mono = TextStyle(
    fontFamily: 'Consolas',
    fontFamilyFallback: ['Courier New', 'monospace'],
    fontSize: 12,
    color: Colors.white,
    height: 1.25,
  );

  @override
  Widget build(BuildContext context) {
    final rec = record;
    final side = whiteMoved ? 'Trắng' : 'Đen';
    final children = <Widget>[
      Text(
        ply == 0 ? 'Thế xuất phát' : 'Nửa nước $ply · $side đi → ${played ?? "?"}',
        style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
      ),
      const SizedBox(height: 4),
    ];
    if (ply == 0) {
      children.add(_note('Chưa có nước nào. Đi tới một nước để xem lần tìm đã chọn nó.'));
    } else if (rec == null) {
      children.add(_note('Không có nhật ký tìm kiếm cho nước này.'));
    } else {
      final nodes = rec.nodes;
      final secs = rec.timeMs == null ? null : rec.timeMs! / 1000.0;
      children.add(_note([
        if (nodes != null) '$nodes lượt tìm',
        if (rec.nps != null) '${rec.nps} nps',
        if (secs != null) '${secs.toStringAsFixed(1)} s',
      ].join(' · ')));
      if (played != null && rec.bestmove != played) {
        children.add(_note('Nhật ký ghi engine trả về ${rec.bestmove}, ván đi $played.',
            color: Colors.orangeAccent));
      }
      children.add(_note('Q, cp, WDL theo phía TRẮNG: dương = Trắng có lợi '
          '(engine in theo phía bên đi; bản gốc ở cuối bảng).'));
      children.add(_note('P = prior trong cây (tự đấu: 0.75·mạng + 0.25·nhiễu Dirichlet ở gốc); '
          'Pnet = prior thô của mạng, trước nhiễu.'));
      children.add(const SizedBox(height: 6));
      children.add(Text(
        '${'Nước'.padRight(7)}${'N'.padLeft(6)}${'%N'.padLeft(6)}${'P'.padLeft(7)}${'Pnet'.padLeft(7)}'
        '${'Q Trắng'.padLeft(8)}${'Trắng/Hòa/Đen %'.padLeft(17)}',
        style: _mono.copyWith(color: Colors.white54),
      ));
      for (final c in rec.candidates) {
        children.add(_row(c, nodes));
      }
      if (played != null && !rec.candidates.any((c) => c.move == played)) {
        children.add(_note('Nước đã đi ($played) không nằm trong các nước engine liệt kê.'));
      }
      children.add(const SizedBox(height: 8));
      children.add(Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: EdgeInsets.zero,
          childrenPadding: EdgeInsets.zero,
          title: Text('Nhật ký gốc (giá trị theo phía bên đi)',
              style: TextStyle(color: Colors.white70, fontSize: 12)),
          children: [
            SelectableText(rec.rawText, style: _mono.copyWith(fontSize: 11, color: Colors.white70)),
          ],
        ),
      ));
    }
    return Container(
      color: const Color(0xFF262421),
      child: ListView(padding: const EdgeInsets.all(10), children: children),
    );
  }

  Widget _note(String s, {Color color = Colors.white60}) => Padding(
        padding: const EdgeInsets.only(bottom: 2),
        child: Text(s, style: TextStyle(color: color, fontSize: 12)),
      );

  Widget _row(SearchCandidate c, int? nodes) {
    final v = c.forWhite(whiteMoved);
    String sign(num x, int digits) =>
        '${x >= 0 ? "+" : ""}${digits == 0 ? x.toString() : x.toStringAsFixed(digits)}';
    final pct = (c.n == null || nodes == null || nodes == 0)
        ? ''
        : (100.0 * c.n! / nodes).toStringAsFixed(1);
    final wdl = v.whiteWin == null
        ? ''
        : '${(v.whiteWin! / 10).toStringAsFixed(1)}/${(v.draw! / 10).toStringAsFixed(1)}/'
            '${(v.blackWin! / 10).toStringAsFixed(1)}';
    final line = '${c.move.padRight(7)}${(c.n?.toString() ?? '').padLeft(6)}${pct.padLeft(6)}'
        '${(c.p?.toStringAsFixed(4) ?? '').padLeft(7)}${(c.pnet?.toStringAsFixed(4) ?? '').padLeft(7)}'
        '${(v.q == null ? '' : sign(v.q!, 3)).padLeft(8)}${wdl.padLeft(17)}';
    final cp = v.cp == null ? '' : 'cp Trắng ${sign(v.cp!, 0)} · ';
    final isPlayed = c.move == played;
    return Container(
      margin: const EdgeInsets.only(top: 2),
      padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 1),
      color: isPlayed ? const Color(0x33FFC107) : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(line, style: isPlayed ? _mono.copyWith(fontWeight: FontWeight.bold) : _mono),
          if (c.pv.isNotEmpty || cp.isNotEmpty)
            Text(
              '  ${isPlayed ? "(đã đi) " : ""}$cp${c.pv.isEmpty ? "" : "pv: ${c.pv.join(" ")}"}',
              style: _mono.copyWith(fontSize: 11, color: Colors.white54),
            ),
        ],
      ),
    );
  }
}
