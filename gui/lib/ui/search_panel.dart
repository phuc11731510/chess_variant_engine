import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../domain/search_record.dart';

/// Một lựa chọn trong menu của tiêu đề cột %N: luỹ thừa [exponent] = 1/T của số lượt thăm.
class TempChoice {
  final double exponent;
  final String hint;
  const TempChoice(this.exponent, this.hint);

  /// Chữ hiện ở tiêu đề cột: `%N`, `%N^2`, `%N^0.5`...
  String get header => exponent == 1 ? '%N' : '%N^${formatExponent(exponent)}';
}

String formatExponent(double e) =>
    e == e.roundToDouble() ? e.toInt().toString() : e.toString();

/// Các nhiệt độ có sẵn. Engine chọn nước theo xác suất ∝ (N / N_max)^(1/T)
/// (`MoveChoiceProbabilities`, selfplay_game.cc), tức ∝ N^(1/T): T = 0,5 là N².
const List<TempChoice> kTempChoices = [
  TempChoice(1, 'T = 1: chỉ tỉ lệ lượt thăm, chưa áp nhiệt độ'),
  TempChoice(2, 'T = 0,5: như sinh dữ liệu và arena'),
  TempChoice(4, 'T = 0,25'),
  TempChoice(10, 'T = 0,1: gần như luôn nước nhiều lượt nhất'),
  TempChoice(0.5, 'T = 2: phẳng hơn tỉ lệ lượt thăm'),
];

/// Xác suất chọn nước khi áp nhiệt độ: p_i = N_i^e / Σ N_j^e (e = 1/T), tính trên các nước có số lượt [ns]
/// (null = bỏ qua, trả về null). Chia cho N_max trước khi luỹ thừa để e lớn không tràn số, đúng như engine.
List<double?> temperatureShares(List<int?> ns, double exponent) {
  final nMax = ns.fold<int>(0, (m, n) => n != null && n > m ? n : m);
  if (nMax <= 0) return List<double?>.filled(ns.length, null);
  double sum = 0;
  final w = <double?>[
    for (final n in ns)
      n == null ? null : math.pow(n / nMax, exponent).toDouble(),
  ];
  for (final x in w) {
    if (x != null) sum += x;
  }
  return [for (final x in w) x == null ? null : x / sum];
}

/// Bảng bên phải bàn cờ (tự đấu / xem lại): lần tìm kiếm MCTS đã chọn nước đang xem —
/// số lượt tìm N, prior P của mạng, giá trị Q, điểm cp và biến chính của từng nước
/// engine cân nhắc. Q / cp đổi sang phía TRẮNG (dương = Trắng có lợi); không hiện cột WDL
/// (Trắng/Hòa/Đen %: chủ dự án chỉ cần cột Q), nhưng nhật ký gốc vẫn có wdl; nhật ký gốc
/// (theo phía bên đi, đúng như engine in) xem ở mục cuối.
///
/// Rê chuột vào tiêu đề cột **%N** (tỉ lệ lượt thăm) thì hiện menu chọn nhiệt độ: chọn một mức (vd %N^2 = T 0,5)
/// thì thêm một cột %N^e cạnh %N, cho biết xác suất engine chọn từng nước khi áp nhiệt độ đó.
class SearchPanel extends StatefulWidget {
  /// Lần tìm của nước đang xem (null: thế xuất phát hoặc không có nhật ký).
  final SearchRecord? record;

  /// Nửa nước đang xem (1 = nước đầu; 0 = thế xuất phát).
  final int ply;

  /// Nước đã đi ở nửa nước này (null ở thế xuất phát).
  final String? played;

  /// Trắng là bên đi nước này.
  final bool whiteMoved;

  /// Luỹ thừa 1/T đang chọn cho cột %N thứ hai (1 = chỉ cột %N).
  final double exponent;
  final ValueChanged<double>? onExponentChanged;

  const SearchPanel({
    super.key,
    required this.record,
    required this.ply,
    required this.played,
    required this.whiteMoved,
    this.exponent = 1,
    this.onExponentChanged,
  });

  @override
  State<SearchPanel> createState() => _SearchPanelState();
}

class _SearchPanelState extends State<SearchPanel> {
  static const _mono = TextStyle(
    fontFamily: 'Consolas',
    fontFamilyFallback: ['Courier New', 'monospace'],
    fontSize: 12,
    color: Colors.white,
    height: 1.25,
  );

  // Độ rộng (số ký tự) từng cột: bảng dùng chữ đơn cách nên tiêu đề và dòng thẳng hàng.
  static const _wMove = 7, _wN = 6, _wPct = 8, _wP = 7, _wPnet = 7, _wQ = 8;

  final LayerLink _link = LayerLink();
  OverlayEntry? _menu;
  Timer? _hideTimer;

  SearchRecord? get record => widget.record;
  bool get _extra => widget.exponent != 1;

  @override
  void dispose() {
    _hideTimer?.cancel();
    _menu?.remove();
    _menu = null;
    super.dispose();
  }

  // --- menu chọn nhiệt độ (hiện khi rê chuột vào tiêu đề %N, ẩn khi chuột rời cả tiêu đề lẫn menu) ---

  void _enter() {
    _hideTimer?.cancel();
    if (_menu != null) return;
    final entry = OverlayEntry(builder: _buildMenu);
    _menu = entry;
    Overlay.of(context).insert(entry);
  }

  void _leave() {
    _hideTimer?.cancel();
    _hideTimer = Timer(const Duration(milliseconds: 250), _hideMenu);
  }

  void _hideMenu() {
    _hideTimer?.cancel();
    _menu?.remove();
    _menu = null;
  }

  void _choose(double e) {
    widget.onExponentChanged?.call(e);
    _hideMenu();
  }

  Widget _buildMenu(BuildContext context) {
    return CompositedTransformFollower(
      link: _link,
      showWhenUnlinked: false,
      targetAnchor: Alignment.bottomLeft,
      followerAnchor: Alignment.topLeft,
      offset: const Offset(0, 2),
      child: Align(
        alignment: Alignment.topLeft,
        child: MouseRegion(
          onEnter: (_) => _hideTimer?.cancel(),
          onExit: (_) => _leave(),
          child: Material(
            elevation: 8,
            color: const Color(0xFF34322F),
            borderRadius: BorderRadius.circular(6),
            child: Container(
              width: 340,
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.fromLTRB(12, 2, 12, 6),
                    child: Text(
                      'Xác suất chọn nước khi áp nhiệt độ T:\nengine chọn theo N^(1/T) / tổng.',
                      style: TextStyle(color: Colors.white54, fontSize: 11),
                    ),
                  ),
                  for (final c in kTempChoices)
                    InkWell(
                      key: ValueKey('nhiet_do_${formatExponent(c.exponent)}'),
                      canRequestFocus: false,
                      onTap: () => _choose(c.exponent),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 5,
                        ),
                        child: Row(
                          children: [
                            Icon(
                              c.exponent == widget.exponent
                                  ? Icons.radio_button_checked
                                  : Icons.radio_button_unchecked,
                              size: 16,
                              color: c.exponent == widget.exponent
                                  ? Colors.amber
                                  : Colors.white38,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text.rich(
                                TextSpan(
                                  children: [
                                    TextSpan(
                                      text: c.header,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 13,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    TextSpan(
                                      text: '   ${c.hint}',
                                      style: const TextStyle(
                                        color: Colors.white60,
                                        fontSize: 11,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  // --- bảng ---

  Widget _cell(String text, int width, {bool right = true}) => Text(
    right ? text.padLeft(width) : text.padRight(width),
    style: _mono.copyWith(color: Colors.white54),
  );

  Widget _headerRow() {
    final hov = _mono.copyWith(
      color: Colors.amber,
      decoration: TextDecoration.underline,
      decorationStyle: TextDecorationStyle.dotted,
      decorationColor: Colors.amber,
    );
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _cell('Nước', _wMove, right: false),
        _cell('N', _wN),
        // Tiêu đề %N: rê chuột vào thì hiện menu nhiệt độ (bấm cũng mở, cho cảm ứng / người dùng không rê chuột).
        CompositedTransformTarget(
          link: _link,
          child: MouseRegion(
            cursor: SystemMouseCursors.click,
            onEnter: (_) => _enter(),
            onExit: (_) => _leave(),
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: _enter,
              child: Text(
                '%N'.padLeft(_wPct),
                key: const ValueKey('tieu_de_pct_n'),
                style: hov,
              ),
            ),
          ),
        ),
        if (_extra)
          Text(
            TempChoice(widget.exponent, '').header.padLeft(_wPct),
            key: const ValueKey('tieu_de_pct_nt'),
            style: _mono.copyWith(color: Colors.amber),
          ),
        _cell('P', _wP),
        _cell('Pnet', _wPnet),
        _cell('Q Trắng', _wQ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final rec = record;
    final side = widget.whiteMoved ? 'Trắng' : 'Đen';
    final played = widget.played;
    final ply = widget.ply;
    final children = <Widget>[
      Text(
        ply == 0
            ? 'Thế xuất phát'
            : 'Nửa nước $ply · $side đi → ${played ?? "?"}',
        style: const TextStyle(
          color: Colors.white,
          fontSize: 14,
          fontWeight: FontWeight.bold,
        ),
      ),
      const SizedBox(height: 4),
    ];
    if (ply == 0) {
      children.add(
        _note('Chưa có nước nào. Đi tới một nước để xem lần tìm đã chọn nó.'),
      );
    } else if (rec == null) {
      children.add(_note('Không có nhật ký tìm kiếm cho nước này.'));
    } else {
      final nodes = rec.nodes;
      final secs = rec.timeMs == null ? null : rec.timeMs! / 1000.0;
      children.add(
        _note(
          [
            if (nodes != null) '$nodes lượt tìm',
            if (rec.nps != null) '${rec.nps} nps',
            if (secs != null) '${secs.toStringAsFixed(1)} s',
          ].join(' · '),
        ),
      );
      if (played != null && rec.bestmove != played) {
        children.add(
          _note(
            'Nhật ký ghi engine trả về ${rec.bestmove}, ván đi $played.',
            color: Colors.orangeAccent,
          ),
        );
      }
      children.add(
        _note(
          'Q, cp theo phía TRẮNG: dương = Trắng có lợi '
          '(engine in theo phía bên đi; bản gốc ở cuối bảng).',
        ),
      );
      children.add(
        _note(
          'P = prior trong cây (tự đấu: 0.75·mạng + 0.25·nhiễu Dirichlet ở gốc); '
          'Pnet = prior thô của mạng, trước nhiễu.',
        ),
      );
      children.add(
        _note(
          'Rê chuột (hoặc chạm) vào tiêu đề %N để chọn nhiệt độ: thêm cột %N^e = xác suất engine chọn '
          'từng nước khi áp nhiệt độ T = 1/e (vd %N^2 là T = 0,5).',
        ),
      );
      if (_extra) {
        final e = formatExponent(widget.exponent);
        children.add(
          _note(
            '${TempChoice(widget.exponent, '').header} = N^$e / ΣN^$e trên các nước đang liệt kê '
            '(nước ngoài bảng có rất ít lượt nên gần như không đổi con số khi T ≤ 1).',
            color: Colors.amber,
          ),
        );
      }
      children.add(const SizedBox(height: 6));
      children.add(
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: _headerRow(),
        ),
      );
      final cands = rec.candidates;
      final shares = temperatureShares([
        for (final c in cands) c.n,
      ], widget.exponent);
      for (int i = 0; i < cands.length; i++) {
        children.add(_row(cands[i], nodes, _extra ? shares[i] : null));
      }
      if (played != null && !cands.any((c) => c.move == played)) {
        children.add(
          _note(
            'Nước đã đi ($played) không nằm trong các nước engine liệt kê.',
          ),
        );
      }
      children.add(const SizedBox(height: 8));
      children.add(
        Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            tilePadding: EdgeInsets.zero,
            childrenPadding: EdgeInsets.zero,
            title: const Text(
              'Nhật ký gốc (giá trị theo phía bên đi)',
              style: TextStyle(color: Colors.white70, fontSize: 12),
            ),
            children: [
              SelectableText(
                rec.rawText,
                style: _mono.copyWith(fontSize: 11, color: Colors.white70),
              ),
            ],
          ),
        ),
      );
    }
    // Material (không phải Container có màu): ExpansionTile / ListTile vẽ nền và hiệu ứng bấm lên Material gần nhất.
    return Material(
      color: const Color(0xFF262421),
      child: ListView(padding: const EdgeInsets.all(10), children: children),
    );
  }

  Widget _note(String s, {Color color = Colors.white60}) => Padding(
    padding: const EdgeInsets.only(bottom: 2),
    child: Text(s, style: TextStyle(color: color, fontSize: 12)),
  );

  Widget _row(SearchCandidate c, int? nodes, double? share) {
    final v = c.forWhite(widget.whiteMoved);
    String sign(num x, int digits) =>
        '${x >= 0 ? "+" : ""}${digits == 0 ? x.toString() : x.toStringAsFixed(digits)}';
    final pct = (c.n == null || nodes == null || nodes == 0)
        ? ''
        : (100.0 * c.n! / nodes).toStringAsFixed(1);
    final pctT = share == null ? null : (100.0 * share).toStringAsFixed(1);
    final line =
        '${c.move.padRight(_wMove)}${(c.n?.toString() ?? '').padLeft(_wN)}${pct.padLeft(_wPct)}'
        '${pctT == null ? '' : pctT.padLeft(_wPct)}'
        '${(c.p?.toStringAsFixed(4) ?? '').padLeft(_wP)}${(c.pnet?.toStringAsFixed(4) ?? '').padLeft(_wPnet)}'
        '${(v.q == null ? '' : sign(v.q!, 3)).padLeft(_wQ)}';
    final cp = v.cp == null ? '' : 'cp Trắng ${sign(v.cp!, 0)} · ';
    final isPlayed = c.move == widget.played;
    return Container(
      margin: const EdgeInsets.only(top: 2),
      padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 1),
      color: isPlayed ? const Color(0x33FFC107) : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const NeverScrollableScrollPhysics(),
            child: Text(
              line,
              style: isPlayed
                  ? _mono.copyWith(fontWeight: FontWeight.bold)
                  : _mono,
            ),
          ),
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
