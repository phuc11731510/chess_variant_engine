import 'dart:async';

import 'package:flutter/material.dart';

import '../config/launch_config.dart';
import '../domain/board_state.dart';
import '../domain/search_record.dart';
import '../domain/uci_move.dart';
import '../engine/native_ffi_engine.dart';
import '../engine/phan_tich.dart';
import 'board_view.dart';

/// Màn "Phân tích": chạy MCTS độc lập ở một thế (thế sau [moves] tính từ [startFen]) bằng mạng của [pt], rồi đi xuống
/// cây tìm kiếm để xem lượt thăm chia vào đâu. Cây còn nguyên tới khi tìm thế khác; "Tìm thêm" cộng lượt vào cùng cây.
class PhanTichScreen extends StatefulWidget {
  final PhanTich pt;
  final String startFen;
  final List<String> moves;

  /// Dòng tiêu đề (vd "Ván 992.8 · sau nửa nước 24").
  final String title;

  /// Lần tìm trong dữ liệu huấn luyện ở CÙNG thế (lần đã chọn nước kế tiếp của ván), để so ở tầng gốc; null nếu không có.
  final SearchRecord? record;

  /// Nước ván đã đi tiếp từ thế này (null ở cuối ván).
  final String? nextPlayed;

  const PhanTichScreen({
    super.key,
    required this.pt,
    required this.startFen,
    required this.moves,
    required this.title,
    this.record,
    this.nextPlayed,
  });

  @override
  State<PhanTichScreen> createState() => _PhanTichScreenState();
}

class _PhanTichScreenState extends State<PhanTichScreen> {
  static const _choices = [200, 800, 1600, 3000, 8000, 20000];
  int _nodes = 800;
  TienDoTim? _progress;
  bool _busy = false;
  String? _error;

  /// Đường đi từ gốc tới nút đang xem, và nút đó (null = chưa có cây cho thế này).
  List<String> _path = [];
  NutCay? _node;

  /// Engine chỉ luật cờ để dựng FEN của nút đang xem (engine phân tích đang giữ cây, không đặt thế khác lên nó được).
  NativeFfiEngine? _rules;
  final Map<String, String> _fenCache = {};
  BoardState? _board;
  Set<int> _lastMove = const {};

  String get _rootCmd => PhanTich.positionCmd(widget.startFen, widget.moves);

  @override
  void initState() {
    super.initState();
    _showBoard();
    if (widget.pt.treePosition == _rootCmd) _open(const []);
  }

  @override
  void dispose() {
    widget.pt.dung();
    _rules?.dispose();
    super.dispose();
  }

  Future<void> _search({required bool fresh}) async {
    setState(() {
      _busy = true;
      _error = null;
      _progress = const TienDoTim(0, 0);
    });
    try {
      final r = await widget.pt.tim(widget.startFen, widget.moves, _nodes,
          fresh: fresh, onProgress: (p) { if (mounted) setState(() => _progress = p); });
      if (!mounted) return;
      setState(() => _progress = r);
      await _open(fresh ? const [] : _path);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _open(List<String> path) async {
    try {
      final n = await widget.pt.cay(path);
      if (!mounted) return;
      setState(() {
        _path = List.of(path);
        _node = n;
        _error = null;
      });
      _showBoard();
    } catch (e) {
      if (!mounted) return;
      if (path.isNotEmpty) {
        await _open(const []);
      } else {
        setState(() {
          _node = null;
          _error = '$e';
        });
      }
    }
  }

  Future<void> _showBoard() async {
    final key = _path.join(' ');
    try {
      var fen = _fenCache[key];
      if (fen == null) {
        final r = _rules ??= NativeFfiEngine(const LaunchConfig(enginePath: ''), rulesOnly: true, ruleSet: widget.pt.ruleSet);
        await r.start();
        await r.newGame(fen: widget.startFen);
        for (final m in [...widget.moves, ..._path]) {
          await r.applyMove(m);
        }
        fen = await r.currentFen();
        _fenCache[key] = fen;
      }
      if (!mounted || key != _path.join(' ')) return;
      final all = [...widget.moves, ..._path];
      final mv = all.isEmpty ? null : UciMove.tryParse(all.last);
      setState(() {
        _board = BoardState.fromFen(fen!);
        _lastMove = mv == null ? const {} : {mv.from.flat, mv.to.flat};
      });
    } catch (_) {
      // bàn cờ chỉ để nhìn: lỗi dựng FEN không chặn phân tích
    }
  }

  bool get _whiteToMove => _board?.whiteToMove ?? true;

  String _sign(double x, [int d = 3]) => '${x >= 0 ? '+' : ''}${x.toStringAsFixed(d)}';

  @override
  Widget build(BuildContext context) {
    final p = _progress;
    final node = _node;
    return Scaffold(
      backgroundColor: const Color(0xFF302E2B),
      appBar: AppBar(
        backgroundColor: const Color(0xFF262421),
        title: Text('Phân tích · gen${widget.pt.gen}', style: const TextStyle(fontSize: 17)),
      ),
      body: LayoutBuilder(builder: (context, c) {
        final wide = c.maxWidth > c.maxHeight && c.maxWidth >= 700;
        final boardSide = wide ? c.maxHeight - 24 : (c.maxWidth < 420 ? c.maxWidth - 24 : 400.0);
        final board = _board == null
            ? SizedBox(width: boardSide, height: boardSide)
            : SizedBox(
                width: boardSide,
                height: boardSide,
                child: BoardView(board: _board!, lastMoveFlats: _lastMove),
              );
        final panel = ListView(
          padding: const EdgeInsets.all(12),
          children: [
            Text(widget.title, style: const TextStyle(color: Colors.white70)),
            const SizedBox(height: 8),
            _controls(),
            if (p != null)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Text(
                  '${p.done ? 'Xong' : 'Đang tìm'}: ${p.nodes} lượt ở gốc · ${p.nps} lượt/giây'
                  '${p.bestmove != null ? ' · nước tốt nhất ${p.bestmove}' : ''}',
                  style: const TextStyle(color: Colors.white60, fontSize: 12),
                ),
              ),
            if (_busy) const Padding(padding: EdgeInsets.only(top: 6), child: LinearProgressIndicator()),
            if (_error != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_error!, style: const TextStyle(color: Colors.orangeAccent))),
            const SizedBox(height: 10),
            if (node != null) ...[
              _breadcrumb(),
              const SizedBox(height: 6),
              Text(
                'Nút: N ${node.n} · Q Trắng ${_sign(_whiteToMove ? node.q : -node.q)} · hoà ${(node.d * 100).toStringAsFixed(1)}% · '
                'còn ~${node.m.toStringAsFixed(0)} nửa nước${node.terminal ? ' · thế kết thúc' : ''} · ${_whiteToMove ? 'Trắng' : 'Đen'} đi',
                style: const TextStyle(color: Colors.white, fontSize: 13),
              ),
              const SizedBox(height: 6),
              _children(node),
            ] else if (!_busy)
              const Text('Chưa có cây cho thế này: chọn số lượt rồi bấm "Tìm mới".', style: TextStyle(color: Colors.white54)),
          ],
        );
        if (wide) {
          return Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Padding(padding: const EdgeInsets.all(12), child: board),
            Expanded(child: panel),
          ]);
        }
        return Column(children: [
          Padding(padding: const EdgeInsets.only(top: 12), child: Center(child: board)),
          Expanded(child: panel),
        ]);
      }),
    );
  }

  Widget _controls() {
    final hasTree = _node != null;
    return Wrap(
      spacing: 8,
      runSpacing: 6,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        DropdownButton<int>(
          value: _nodes,
          items: [for (final n in _choices) DropdownMenuItem(value: n, child: Text('$n lượt'))],
          onChanged: _busy ? null : (v) => setState(() => _nodes = v ?? _nodes),
        ),
        FilledButton(onPressed: _busy ? null : () => _search(fresh: true), child: const Text('Tìm mới')),
        OutlinedButton(onPressed: _busy || !hasTree ? null : () => _search(fresh: false), child: Text('Tìm thêm $_nodes')),
        if (_busy) TextButton(onPressed: widget.pt.dung, child: const Text('Dừng')),
      ],
    );
  }

  Widget _breadcrumb() {
    final chips = <Widget>[
      ActionChip(label: const Text('Gốc'), onPressed: _path.isEmpty ? null : () => _open(const [])),
    ];
    for (var i = 0; i < _path.length; i++) {
      chips.add(ActionChip(
        label: Text(_path[i]),
        onPressed: i == _path.length - 1 ? null : () => _open(_path.sublist(0, i + 1)),
      ));
    }
    return Wrap(spacing: 4, runSpacing: 4, children: chips);
  }

  static const _mono = TextStyle(fontFamily: 'monospace', fontSize: 14, color: Colors.white, height: 1.3);

  Widget _children(NutCay node) {
    final rec = _path.isEmpty ? widget.record : null;
    final recN = <String, int>{};
    int? recTotal;
    if (rec != null) {
      for (final c in rec.candidates) {
        if (c.n != null) recN[c.move] = c.n!;
      }
      recTotal = rec.nodes ?? (recN.isEmpty ? null : recN.values.reduce((a, b) => a + b));
    }
    final sumN = node.children.fold<int>(0, (a, c) => a + c.n);
    final visited = node.children.where((c) => c.n > 0).toList();
    final unvisited = node.children.length - visited.length;
    String row(String mv, String n, String pct, String p, String q, String r) =>
        '${mv.padRight(7)}${n.padLeft(7)}${pct.padLeft(7)}${p.padLeft(8)}${q.padLeft(8)}${rec == null ? '' : r.padLeft(8)}';
    final white = _whiteToMove;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      FittedBox(
        fit: BoxFit.scaleDown,
        alignment: Alignment.centerLeft,
        child: Text(row('Nước', 'N', '%N', 'P', 'Q Trắng', '%N ghi'), style: _mono.copyWith(color: Colors.white54)),
      ),
      for (final c in visited)
        InkWell(
          onTap: c.terminal ? null : () => _open([..._path, c.move]),
          child: Container(
            width: double.infinity,
            color: _path.isEmpty && c.move == widget.nextPlayed ? const Color(0x33FFC107) : null,
            padding: const EdgeInsets.symmetric(vertical: 3),
            child: FittedBox(
              fit: BoxFit.scaleDown,
              alignment: Alignment.centerLeft,
              child: Text(
                row(
                  c.move,
                  '${c.n}',
                  sumN == 0 ? '' : (100 * c.n / sumN).toStringAsFixed(1),
                  c.p.toStringAsFixed(4),
                  _sign(white ? c.q : -c.q),
                  recTotal == null || recTotal == 0 || !recN.containsKey(c.move) ? '' : (100 * recN[c.move]! / recTotal).toStringAsFixed(1),
                ) + (c.terminal ? '  kết thúc' : ''),
                style: _mono,
              ),
            ),
          ),
        ),
      const SizedBox(height: 6),
      Text(
        '${unvisited > 0 ? '$unvisited nước chưa được thăm. ' : ''}Chạm một nước để đi xuống. Q theo phía Trắng; P = prior trong cây '
        '(không nhiễu); %N = phần lượt của nút này.'
        '${rec != null ? ' %N ghi = tỉ lệ lượt thăm trong dữ liệu huấn luyện ở cùng thế (có nhiễu, ${recTotal ?? '?'} lượt).' : ''}'
        '${widget.nextPlayed != null && _path.isEmpty ? ' Dòng tô vàng = nước ván đã đi (${widget.nextPlayed}).' : ''}',
        style: const TextStyle(color: Colors.white54, fontSize: 12),
      ),
    ]);
  }
}
