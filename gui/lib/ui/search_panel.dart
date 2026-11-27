import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../domain/search_record.dart';
import '../engine/phan_tich.dart' show DanhGiaTho;

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

  /// Màn hình cảm ứng (bảng nằm dưới bàn hoặc cạnh bàn, chỗ ít): bỏ các ghi chú dài, chỉ giữ ghi chú cần thiết.
  final bool compact;

  /// Prior thô của mạng đang chọn ở đúng thế của lần tìm này (tính theo yêu cầu): cột Pnet lấy từ đây.
  final DanhGiaTho? rawPrior;

  /// Dòng điều khiển đặt trên cùng bảng (nút bật prior thô), hoặc null.
  final Widget? rawHeader;

  const SearchPanel({
    super.key,
    required this.record,
    required this.ply,
    required this.played,
    required this.whiteMoved,
    this.exponent = 1,
    this.onExponentChanged,
    this.compact = false,
    this.rawPrior,
    this.rawHeader,
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

  /// Kiểu chữ của bảng các nước: cảm ứng (chỗ rộng, màn hình xem gần) chữ to hơn; bảng tự thu nhỏ khi chỗ hẹp.
  TextStyle get _ms =>
      widget.compact ? _mono.copyWith(fontSize: 14) : _mono;

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
    style: _ms.copyWith(color: Colors.white54),
  );

  /// Chữ từng ô của dòng tiêu đề, đúng thứ tự trong [_headerRow], để đo bề rộng.
  List<String> _headerCells(({bool p, bool pnet}) prior) => [
    'Nước'.padRight(_wMove),
    'N'.padLeft(_wN),
    '%N'.padLeft(_wPct),
    if (_extra) TempChoice(widget.exponent, '').header.padLeft(_wPct),
    if (prior.p) 'P'.padLeft(_wP),
    if (prior.pnet) 'Pnet'.padLeft(_wPnet),
    'Q Trắng'.padLeft(_wQ),
  ];

  Widget _headerRow(({bool p, bool pnet}) prior) {
    final hov = _ms.copyWith(
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
            style: _ms.copyWith(color: Colors.amber),
          ),
        if (prior.p) _cell('P', _wP),
        if (prior.pnet) _cell('Pnet', _wPnet),
        _cell('Q Trắng', _wQ),
      ],
    );
  }

  /// Bảng các nước: tiêu đề + mỗi nước một dòng chữ đơn cách. Cả bảng được thu nhỏ vừa bề ngang của bảng khi chỗ hẹp
  /// (màn hình điện thoại xoay ngang, cỡ chữ hệ thống lớn) thay vì tràn ra ngoài; cột P / Pnet chỉ hiện khi nhật ký
  /// có (dữ liệu huấn luyện không lưu prior).
  Widget _table(List<SearchCandidate> cands, int? nodes, ({bool p, bool pnet}) prior) {
    final shares = temperatureShares([
      for (final c in cands) c.n,
    ], widget.exponent);
    // Bề rộng = dòng dài nhất (tiêu đề hoặc một nước) đo đúng bằng kiểu chữ và cỡ chữ hệ thống đang dùng.
    final lines = [
      for (int i = 0; i < cands.length; i++)
        _lineOf(cands[i], nodes, _extra ? shares[i] : null, prior),
    ];
    final scaler = MediaQuery.textScalerOf(context);
    // Kiểu chữ THỰC của các ô: _mono hợp với kiểu mặc định của giao diện (có thể thêm giãn chữ, vd Material 0,25 px
    // mỗi ký tự), nếu đo bằng _mono trơn thì bảng bị tính hẹp hơn thật và vẫn tràn.
    final style = DefaultTextStyle.of(context).style.merge(_ms);
    double measure(String s) {
      final tp = TextPainter(
        text: TextSpan(text: s, style: style),
        textDirection: TextDirection.ltr,
        textScaler: scaler,
      )..layout();
      return tp.width;
    }

    // Tiêu đề là một hàng các ô riêng nên cộng bề rộng từng ô; mỗi nước là một chuỗi.
    var width = _headerCells(prior).fold(0.0, (a, s) => a + measure(s));
    for (final s in lines) {
      final w = measure(s);
      if (w > width) width = w;
    }
    width += 8;
    return FittedBox(
      fit: BoxFit.scaleDown,
      alignment: Alignment.topLeft,
      child: SizedBox(
        width: width,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _headerRow(prior),
            for (int i = 0; i < cands.length; i++) _row(cands[i], lines[i]),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final rec = record;
    final side = widget.whiteMoved ? 'Trắng' : 'Đen';
    final played = widget.played;
    final ply = widget.ply;
    final children = <Widget>[
      if (widget.rawHeader != null) ...[widget.rawHeader!, const SizedBox(height: 4)],
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
      final cands = rec.candidates;
      final raw = widget.rawPrior;
      final prior = (p: cands.any((c) => c.p != null), pnet: raw != null || cands.any((c) => c.pnet != null));
      if (raw != null) {
        final qw = widget.whiteMoved ? raw.q : -raw.q;
        children.add(_note('Giá trị thô của mạng ở thế này: Q Trắng ${_sign(qw, 3)} · hoà ${(raw.d * 100).toStringAsFixed(1)}%',
            color: Colors.lightBlueAccent));
      }
      // Bảng các nước ngay dưới dòng tổng (chỗ ít, màn hình dọc: số liệu phải thấy ngay); các ghi chú xuống dưới bảng.
      children.add(const SizedBox(height: 4));
      children.add(_table(cands, nodes, prior));
      if (played != null && !cands.any((c) => c.move == played)) {
        children.add(
          _note(
            'Nước đã đi ($played) không nằm trong các nước engine liệt kê.',
          ),
        );
      }
      children.add(const SizedBox(height: 6));
      children.add(
        _note(
          'Q, cp theo phía TRẮNG: dương = Trắng có lợi '
          '(engine in theo phía bên đi; bản gốc ở cuối bảng).',
        ),
      );
      if (!prior.p && !prior.pnet) {
        // Nhật ký dựng từ dữ liệu huấn luyện: bản ghi chỉ lưu Q của hai nước.
        children.add(
          _note(
            'Dữ liệu huấn luyện chỉ lưu Q của nước đã đi và nước nhiều lượt nhất; '
            'các nước khác chỉ có số lượt thăm N.',
          ),
        );
      } else if (!widget.compact) {
        children.add(
          _note(
            'P = prior trong cây (tự đấu: 0.75·mạng + 0.25·nhiễu Dirichlet ở gốc); '
            'Pnet = prior thô của mạng, trước nhiễu.',
          ),
        );
      }
      children.add(
        _note(
          widget.compact
              ? 'Chạm tiêu đề %N để chọn nhiệt độ T: thêm cột %N^e = xác suất chọn nước.'
              : 'Rê chuột (hoặc chạm) vào tiêu đề %N để chọn nhiệt độ: thêm cột %N^e = xác suất engine chọn '
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

  String _sign(num x, int digits) =>
      '${x >= 0 ? "+" : ""}${digits == 0 ? x.toString() : x.toStringAsFixed(digits)}';

  /// Chữ của dòng một nước: Nước, N, %N, [%N^e], [P, Pnet], Q Trắng.
  String _lineOf(SearchCandidate c, int? nodes, double? share, ({bool p, bool pnet}) prior) {
    final v = c.forWhite(widget.whiteMoved);
    final pct = (c.n == null || nodes == null || nodes == 0)
        ? ''
        : (100.0 * c.n! / nodes).toStringAsFixed(1);
    final pctT = share == null ? null : (100.0 * share).toStringAsFixed(1);
    return '${c.move.padRight(_wMove)}${(c.n?.toString() ?? '').padLeft(_wN)}${pct.padLeft(_wPct)}'
        '${pctT == null ? '' : pctT.padLeft(_wPct)}'
        '${prior.p ? (c.p?.toStringAsFixed(4) ?? '').padLeft(_wP) : ''}'
        '${prior.pnet ? (_pnetOf(c)?.toStringAsFixed(4) ?? '').padLeft(_wPnet) : ''}'
        '${(v.q == null ? '' : _sign(v.q!, 3)).padLeft(_wQ)}';
  }

  /// Pnet của một nước: prior thô vừa tính (nếu bật) hơn Pnet trong nhật ký.
  double? _pnetOf(SearchCandidate c) => widget.rawPrior?.policy[c.move] ?? c.pnet;

  Widget _row(SearchCandidate c, String line) {
    final v = c.forWhite(widget.whiteMoved);
    final cp = v.cp == null ? '' : 'cp Trắng ${_sign(v.cp!, 0)} · ';
    final isPlayed = c.move == widget.played;
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 2),
      padding: const EdgeInsets.symmetric(horizontal: 2, vertical: 1),
      color: isPlayed ? const Color(0x33FFC107) : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            line,
            maxLines: 1,
            softWrap: false,
            style: isPlayed
                ? _ms.copyWith(fontWeight: FontWeight.bold)
                : _ms,
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
