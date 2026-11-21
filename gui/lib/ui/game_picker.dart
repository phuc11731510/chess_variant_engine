import 'package:flutter/material.dart';

import '../config/replay_library.dart';

/// Cách sắp xếp danh sách ván.
enum GameSort {
  id('Thứ tự trong dữ liệu'),
  shortest('Ít nửa nước nhất'),
  longest('Nhiều nửa nước nhất'),
  mostPieces('Nhiều quân còn lại nhất'),
  fewestPieces('Ít quân còn lại nhất');

  final String label;
  const GameSort(this.label);
}

/// Bảng chọn ván (xem lại nhiều ván, `--replay-dir`): lọc theo kết quả, lý do kết thúc và số quân còn lại
/// ở cuối ván, sắp xếp, rồi bấm một dòng để xem ván đó. Để tìm ván "thắng thua mà còn gần đủ 60 quân":
/// chọn "Trắng thắng" / "Đen thắng", kéo thanh số quân lên cao, sắp xếp "Ít nửa nước nhất".
///
/// Đặt trong `ExcludeFocus` (main.dart) để bấm vào đây không cướp phím tắt của màn hình chính.
class GamePicker extends StatefulWidget {
  final ReplayLibrary library;

  /// `id` của ván đang mở.
  final int? selectedId;
  final ValueChanged<ReplayEntry> onSelect;

  const GamePicker({
    super.key,
    required this.library,
    required this.selectedId,
    required this.onSelect,
  });

  @override
  State<GamePicker> createState() => GamePickerState();
}

class GamePickerState extends State<GamePicker> {
  static const double _rowHeight = 50;

  String _result = 'all'; // all | W | B | D
  String _reason = 'all';
  int _minPieces = 0;
  GameSort _sort = GameSort.id;
  final ScrollController _sc = ScrollController();

  @override
  void dispose() {
    _sc.dispose();
    super.dispose();
  }

  /// Các ván thoả bộ lọc, theo cách sắp xếp đang chọn.
  List<ReplayEntry> get filtered {
    final out = widget.library.entries.where((e) {
      if (_result != 'all' && e.result != _result) return false;
      if (_reason != 'all' && e.reason != _reason) return false;
      return e.pieces >= _minPieces;
    }).toList();
    int byId(ReplayEntry a, ReplayEntry b) => a.id.compareTo(b.id);
    switch (_sort) {
      case GameSort.id:
        out.sort(byId);
      case GameSort.shortest:
        out.sort((a, b) => a.plies != b.plies ? a.plies.compareTo(b.plies) : byId(a, b));
      case GameSort.longest:
        out.sort((a, b) => a.plies != b.plies ? b.plies.compareTo(a.plies) : byId(a, b));
      case GameSort.mostPieces:
        out.sort((a, b) => a.pieces != b.pieces ? b.pieces.compareTo(a.pieces) : byId(a, b));
      case GameSort.fewestPieces:
        out.sort((a, b) => a.pieces != b.pieces ? a.pieces.compareTo(b.pieces) : byId(a, b));
    }
    return out;
  }

  /// Mở ván kế tiếp ([delta] = 1) hoặc trước đó (-1) trong danh sách đang lọc.
  void selectRelative(int delta) {
    final list = filtered;
    if (list.isEmpty) return;
    var i = list.indexWhere((e) => e.id == widget.selectedId);
    i = i < 0 ? (delta > 0 ? 0 : list.length - 1) : (i + delta).clamp(0, list.length - 1);
    widget.onSelect(list[i]);
    _scrollTo(i);
  }

  void _scrollTo(int index) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_sc.hasClients) return;
      final pos = _sc.position;
      final target = (index * _rowHeight - (pos.viewportDimension - _rowHeight) / 2)
          .clamp(0.0, pos.maxScrollExtent)
          .toDouble();
      _sc.jumpTo(target);
    });
  }

  Widget _chip(String label, bool on, VoidCallback onTap) {
    return InkWell(
      canRequestFocus: false,
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(
          color: on ? const Color(0xFF8A6D1F) : const Color(0xFF34322F),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          label,
          style: TextStyle(color: on ? Colors.white : Colors.white70, fontSize: 12),
        ),
      ),
    );
  }

  Color _resultColor(String r) {
    switch (r) {
      case 'W':
        return const Color(0xFFEDEDED);
      case 'B':
        return const Color(0xFF9A9A9A);
      case 'D':
        return const Color(0xFFD9B04A);
      default:
        return Colors.redAccent;
    }
  }

  Widget _row(ReplayEntry e) {
    final selected = e.id == widget.selectedId;
    return InkWell(
      canRequestFocus: false,
      onTap: () => widget.onSelect(e),
      child: Container(
        height: _rowHeight,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        color: selected ? const Color(0xFF5A4A1A) : Colors.transparent,
        alignment: Alignment.centerLeft,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                SizedBox(
                  width: 52,
                  child: Text('#${e.id}',
                      style: const TextStyle(color: Colors.white54, fontSize: 12, fontFamily: 'Consolas')),
                ),
                Text(e.resultText,
                    style: TextStyle(
                        color: _resultColor(e.result), fontSize: 13, fontWeight: FontWeight.bold)),
                const SizedBox(width: 8),
                Flexible(
                  child: Text('${e.plies} nửa nước',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white70, fontSize: 12)),
                ),
                if (e.note.isNotEmpty) ...[
                  const SizedBox(width: 6),
                  Tooltip(
                    message: e.note,
                    child: const Icon(Icons.warning_amber, size: 14, color: Colors.orangeAccent),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 2),
            Text(
              'còn ${e.pieces} quân (T${e.whitePieces} + Đ${e.blackPieces}) · ${e.reasonText}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white54, fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final list = filtered;
    final lib = widget.library;
    final reasons = <String>{for (final e in lib.entries) e.reason}.toList()..sort();
    final maxPieces = lib.maxPieces;
    return Container(
      color: const Color(0xFF262421),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 8, 10, 4),
            child: Text(
              'Chọn ván · ${list.length}/${lib.entries.length}   ([ ] = ván trước / sau, G = ẩn bảng)',
              style: const TextStyle(color: Colors.white70, fontSize: 12),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                _chip('Tất cả', _result == 'all', () => setState(() => _result = 'all')),
                _chip('Trắng thắng', _result == 'W', () => setState(() => _result = 'W')),
                _chip('Đen thắng', _result == 'B', () => setState(() => _result = 'B')),
                _chip('Hoà', _result == 'D', () => setState(() => _result = 'D')),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 6, 10, 0),
            child: Row(
              children: [
                const Text('Lý do: ', style: TextStyle(color: Colors.white54, fontSize: 12)),
                Expanded(
                  child: DropdownButton<String>(
                    isExpanded: true,
                    isDense: true,
                    value: reasons.contains(_reason) ? _reason : 'all',
                    dropdownColor: const Color(0xFF34322F),
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                    items: [
                      const DropdownMenuItem(value: 'all', child: Text('Mọi lý do')),
                      for (final r in reasons)
                        DropdownMenuItem(value: r, child: Text(ReplayEntry.reasonLabels[r] ?? r)),
                    ],
                    onChanged: (v) => setState(() => _reason = v ?? 'all'),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 4, 10, 0),
            child: Row(
              children: [
                const Text('Xếp: ', style: TextStyle(color: Colors.white54, fontSize: 12)),
                Expanded(
                  child: DropdownButton<GameSort>(
                    isExpanded: true,
                    isDense: true,
                    value: _sort,
                    dropdownColor: const Color(0xFF34322F),
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                    items: [
                      for (final s in GameSort.values) DropdownMenuItem(value: s, child: Text(s.label)),
                    ],
                    onChanged: (v) => setState(() => _sort = v ?? GameSort.id),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 2, 10, 0),
            child: Text(
              'Còn ít nhất $_minPieces quân ở cuối ván',
              style: const TextStyle(color: Colors.white54, fontSize: 12),
            ),
          ),
          SizedBox(
            height: 28,
            child: Slider(
              min: 0,
              max: maxPieces < 1 ? 1 : maxPieces.toDouble(),
              divisions: maxPieces < 1 ? 1 : maxPieces,
              value: _minPieces.clamp(0, maxPieces < 1 ? 1 : maxPieces).toDouble(),
              onChanged: (v) => setState(() => _minPieces = v.round()),
            ),
          ),
          const Divider(height: 1, color: Colors.white12),
          Expanded(
            child: list.isEmpty
                ? const Center(
                    child: Text('Không có ván nào thoả bộ lọc',
                        style: TextStyle(color: Colors.white38, fontSize: 12)),
                  )
                : ListView.builder(
                    controller: _sc,
                    itemExtent: _rowHeight,
                    itemCount: list.length,
                    itemBuilder: (context, i) => _row(list[i]),
                  ),
          ),
        ],
      ),
    );
  }
}
