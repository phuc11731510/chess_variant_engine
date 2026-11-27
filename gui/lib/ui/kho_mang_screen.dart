import 'dart:async';

import 'package:flutter/material.dart';

import '../mang/kho_mang.dart';

/// Màn "Kho mạng": tải `gen<N>.pt` từ Release (đổi ngay trên máy thành mạng engine chạy được), xem dung lượng, xoá.
class KhoMangScreen extends StatefulWidget {
  const KhoMangScreen({super.key});

  @override
  State<KhoMangScreen> createState() => _KhoMangScreenState();
}

class _KhoMangScreenState extends State<KhoMangScreen> {
  KhoMang? _kho;
  List<MangDaTai> _local = [];
  List<MangTrenRelease>? _remote;
  String? _error;
  bool _loadingRemote = false;
  bool _showAll = false;

  /// Lỗi của lần tải sau cùng: giữ trên màn hình tới khi người dùng đóng.
  String? _downloadError;

  /// Đời đang tải -> tiến độ mới nhất; chỉ tải một mạng một lúc.
  int? _busyGen;
  TaiTienDo? _progress;
  StreamSubscription<TaiTienDo>? _sub;

  @override
  void initState() {
    super.initState();
    _init();
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  Future<void> _init() async {
    try {
      _kho = await KhoMang.open();
      _refreshLocal();
      await _loadRemote();
    } catch (e) {
      setState(() => _error = '$e');
    }
  }

  void _refreshLocal() {
    if (_kho == null) return;
    setState(() => _local = _kho!.local());
  }

  Future<void> _loadRemote() async {
    setState(() {
      _loadingRemote = true;
      _error = null;
    });
    try {
      final r = await _kho!.remote();
      if (mounted) setState(() => _remote = r);
    } catch (e) {
      if (mounted) setState(() => _error = 'Không lấy được danh sách mạng trên Release: $e');
    } finally {
      if (mounted) setState(() => _loadingRemote = false);
    }
  }

  void _download(MangTrenRelease r) {
    if (_busyGen != null) return;
    setState(() {
      _busyGen = r.gen;
      _progress = const TaiTienDo();
      _downloadError = null;
    });
    _sub = _kho!.download(r).listen(
      (p) {
        if (!mounted) return;
        setState(() {
          _progress = p;
          if (p.error != null) _downloadError = 'Tải / đổi gen${r.gen} lỗi: ${p.error}';
        });
      },
      onDone: () {
        if (!mounted) return;
        setState(() {
          _busyGen = null;
          _progress = null;
        });
        _refreshLocal();
      },
    );
  }

  Future<void> _cancel() async {
    await _sub?.cancel();
    setState(() {
      _busyGen = null;
      _progress = null;
    });
  }

  Future<void> _delete(MangDaTai m) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Xoá gen${m.gen}?'),
        content: Text('Giải phóng ${coTep(m.bytes)}. Cần lại thì tải lại từ Release.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Thôi')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Xoá')),
        ],
      ),
    );
    if (ok != true) return;
    _kho!.delete(m.gen);
    _refreshLocal();
  }

  @override
  Widget build(BuildContext context) {
    final have = {for (final m in _local) m.gen};
    final remote = _remote ?? const <MangTrenRelease>[];
    final newest = remote.isEmpty ? null : remote.first;
    final shown = _showAll ? remote : remote.take(12).toList();
    final total = _local.fold<int>(0, (a, m) => a + m.bytes);
    return Scaffold(
      backgroundColor: const Color(0xFF302E2B),
      appBar: AppBar(
        backgroundColor: const Color(0xFF262421),
        title: const Text('Kho mạng'),
        actions: [
          IconButton(tooltip: 'Hỏi lại Release', icon: const Icon(Icons.refresh), onPressed: _loadingRemote ? null : _loadRemote),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          if (_error != null) Padding(padding: const EdgeInsets.only(bottom: 8), child: Text(_error!, style: const TextStyle(color: Colors.orangeAccent))),
          if (newest != null)
            FilledButton.icon(
              icon: const Icon(Icons.download),
              label: Text(have.contains(newest.gen) ? 'Mạng mới nhất gen${newest.gen} đã có' : 'Tải mạng mới nhất (gen${newest.gen}, ${coTep(newest.bytes)})'),
              onPressed: have.contains(newest.gen) || _busyGen != null ? null : () => _download(newest),
            ),
          if (_busyGen != null && _progress != null) _progressCard(),
          if (_downloadError != null)
            Card(
              color: const Color(0xFF4A2A1A),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Expanded(child: SelectableText(_downloadError!, style: const TextStyle(color: Colors.orangeAccent))),
                  IconButton(tooltip: 'Đóng', icon: const Icon(Icons.close), onPressed: () => setState(() => _downloadError = null)),
                ]),
              ),
            ),
          const SizedBox(height: 12),
          Text('Đã tải: ${_local.length} mạng, ${coTep(total)}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          if (_local.isEmpty)
            const Padding(padding: EdgeInsets.symmetric(vertical: 8), child: Text('Chưa có mạng nào.', style: TextStyle(color: Colors.white54))),
          for (final m in _local)
            Card(
              color: const Color(0xFF3A3835),
              child: ListTile(
                leading: const Icon(Icons.memory),
                title: Text('gen${m.gen}', style: const TextStyle(fontWeight: FontWeight.w600)),
                subtitle: Text('${coTep(m.bytes)} · tải ${_when(m.when)}'),
                trailing: IconButton(tooltip: 'Xoá', icon: const Icon(Icons.delete_outline), onPressed: _busyGen == m.gen ? null : () => _delete(m)),
              ),
            ),
          const SizedBox(height: 16),
          Row(children: [
            const Expanded(child: Text('Trên Release', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600))),
            if (_loadingRemote) const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
          ]),
          for (final r in shown)
            ListTile(
              dense: true,
              title: Text('gen${r.gen}'),
              subtitle: Text('${coTep(r.bytes)} · ${_when(r.updated)}'),
              trailing: have.contains(r.gen)
                  ? const Icon(Icons.check, color: Colors.lightGreen)
                  : IconButton(tooltip: 'Tải', icon: const Icon(Icons.download), onPressed: _busyGen != null ? null : () => _download(r)),
            ),
          if (!_showAll && remote.length > shown.length)
            TextButton(onPressed: () => setState(() => _showAll = true), child: Text('Hiện cả ${remote.length} đời')),
        ],
      ),
    );
  }

  Widget _progressCard() {
    final p = _progress!;
    final frac = p.converting || p.total == 0 ? null : p.done / p.total;
    final text = p.converting ? 'Đang đổi gen$_busyGen sang mạng engine…' : 'Đang tải gen$_busyGen: ${coTep(p.done)} / ${coTep(p.total)}';
    return Card(
      color: const Color(0xFF2E3B2A),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text(text)),
            if (!p.converting) TextButton(onPressed: _cancel, child: const Text('Huỷ')),
          ]),
          const SizedBox(height: 6),
          LinearProgressIndicator(value: frac),
        ]),
      ),
    );
  }

  String _when(DateTime t) {
    String two(int x) => x.toString().padLeft(2, '0');
    return '${two(t.hour)}:${two(t.minute)} ${two(t.day)}/${two(t.month)}';
  }
}
