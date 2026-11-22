import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';

import '../data/generation_cache.dart';
import '../platform/android_paths.dart';

/// Màn hình đầu của app Android: các đời dữ liệu huấn luyện tìm thấy trên máy (vòng lặp Termux ghi vào
/// `Download/FairyZero/games_genN`), bấm một đời để xem các ván trong đó. Lần đầu mỗi đời được đổi sang bảng ván
/// (vài chục giây, có thanh tiến độ); các lần sau mở ngay.
class AndroidHome extends StatefulWidget {
  /// Màn hình xem ván của một đời dữ liệu đã đổi trong [cacheDir] (main.dart dựng BoardScreen).
  final Widget Function(String cacheDir) openViewer;
  const AndroidHome({super.key, required this.openViewer});

  @override
  State<AndroidHome> createState() => _AndroidHomeState();
}

class _Source {
  final String name;
  final String path;
  final bool isZip;
  final int? games; // số ván (thư mục); null với gói zip
  final DateTime modified;
  final int? gen;
  bool cached;
  _Source(
    this.name,
    this.path,
    this.isZip,
    this.games,
    this.modified,
    this.gen,
    this.cached,
  );

  String get title => gen != null && !isZip ? 'Đời $gen' : name;
}

class _AndroidHomeState extends State<AndroidHome> with WidgetsBindingObserver {
  String? _root; // thư mục chứa games_gen*
  String? _filesDir;
  bool _access = true;
  bool _loading = true;
  String? _error;
  List<_Source> _sources = [];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _init();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Người dùng vừa gạt công tắc quyền trong Cài đặt rồi quay lại: quét lại.
    if (state == AppLifecycleState.resumed) _scan();
  }

  Future<void> _init() async {
    _filesDir = await AndroidPaths.externalFilesDir();
    final saved = _readSetting();
    final dl = await AndroidPaths.downloadDir();
    _root = saved ?? '${dl ?? '/storage/emulated/0/Download'}/FairyZero';
    await _scan();
  }

  File get _settingFile => File('$_filesDir/cau_hinh.txt');

  String? _readSetting() {
    try {
      final f = _settingFile;
      if (!f.existsSync()) return null;
      for (final l in f.readAsLinesSync()) {
        if (l.startsWith('goc=') && l.length > 4) return l.substring(4);
      }
    } on Exception {
      // dùng mặc định
    }
    return null;
  }

  String _cacheDirOf(String name) =>
      '$_filesDir/xem/${name.replaceAll(RegExp(r'[^A-Za-z0-9_.-]'), '_')}';

  Future<void> _scan() async {
    final root = _root;
    if (root == null) return;
    // Thư mục nằm trong chỗ riêng của app (Android/data/<gói>) thì đọc được không cần quyền gì; ngoài đó (Download)
    // cần "Truy cập mọi tệp".
    final appDir = _filesDir == null ? null : File(_filesDir!).parent.path;
    final access =
        (appDir != null && root.startsWith(appDir)) ||
        await AndroidPaths.hasAllFilesAccess();
    final out = <_Source>[];
    String? err;
    if (access) {
      try {
        final dir = Directory(root);
        if (!dir.existsSync()) {
          err = 'Không có thư mục $root';
        } else {
          for (final e in dir.listSync(followLinks: false)) {
            final name = e.path.split('/').last;
            final m = RegExp(r'^games_gen(\d+)').firstMatch(name);
            final gen = m == null ? null : int.parse(m.group(1)!);
            if (e is Directory && gen != null) {
              final n = e
                  .listSync(followLinks: false)
                  .where((f) => f.path.endsWith('.xz'))
                  .length;
              if (n == 0) continue;
              out.add(
                _Source(
                  name,
                  e.path,
                  false,
                  n,
                  e.statSync().modified,
                  gen,
                  false,
                ),
              );
            } else if (e is File && e.path.endsWith('.zip') && gen != null) {
              out.add(
                _Source(
                  name,
                  e.path,
                  true,
                  null,
                  e.statSync().modified,
                  gen,
                  false,
                ),
              );
            }
          }
        }
      } on Exception catch (e) {
        err = 'Không đọc được $root: $e';
      }
    }
    // Mới nhất trước: đời lớn hơn lên trên; cùng đời thì thư mục trước gói zip.
    out.sort((a, b) {
      final c = (b.gen ?? 0).compareTo(a.gen ?? 0);
      if (c != 0) return c;
      if (a.isZip != b.isZip) return a.isZip ? 1 : -1;
      return b.name.compareTo(a.name);
    });
    for (final s in out) {
      if (!s.isZip) s.cached = isCurrent(s.path, _cacheDirOf(s.name));
    }
    if (!mounted) return;
    setState(() {
      _access = access;
      _sources = out;
      _error = err;
      _loading = false;
    });
  }

  Future<void> _open(_Source s) async {
    final cacheDir = _cacheDirOf(s.name);
    final ok = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) =>
          _ConvertDialog(source: s.path, cacheDir: cacheDir, title: s.title),
    );
    if (ok != true || !mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => widget.openViewer(cacheDir)),
    );
    if (mounted) _scan();
  }

  Future<void> _changeRoot() async {
    final ctl = TextEditingController(text: _root);
    final v = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Thư mục dữ liệu huấn luyện'),
        content: TextField(
          controller: ctl,
          decoration: const InputDecoration(
            helperText: 'Thư mục chứa các games_genN',
          ),
          autocorrect: false,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Huỷ'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, ctl.text.trim()),
            child: const Text('Lưu'),
          ),
        ],
      ),
    );
    if (v == null || v.isEmpty) return;
    try {
      _settingFile.writeAsStringSync('goc=$v\n');
    } on Exception {
      // vẫn dùng cho lần chạy này
    }
    setState(() {
      _root = v;
      _loading = true;
    });
    await _scan();
  }

  Future<void> _clearCache() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Xoá bộ nhớ đệm?'),
        content: const Text(
          'Xoá bảng ván đã đổi của mọi đời (dữ liệu huấn luyện không bị động tới). Lần mở sau sẽ đổi lại.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Huỷ'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Xoá'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      final d = Directory('$_filesDir/xem');
      if (d.existsSync()) d.deleteSync(recursive: true);
    } on Exception {
      // bỏ qua
    }
    await _scan();
  }

  String _when(DateTime t) {
    String two(int x) => x.toString().padLeft(2, '0');
    return '${two(t.hour)}:${two(t.minute)} ${two(t.day)}/${two(t.month)}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF302E2B),
      appBar: AppBar(
        backgroundColor: const Color(0xFF262421),
        title: const Text('Xem ván huấn luyện'),
        actions: [
          IconButton(
            tooltip: 'Quét lại',
            icon: const Icon(Icons.refresh),
            onPressed: _scan,
          ),
          PopupMenuButton<String>(
            onSelected: (v) => v == 'goc' ? _changeRoot() : _clearCache(),
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'goc', child: Text('Đổi thư mục dữ liệu')),
              PopupMenuItem(value: 'xoa', child: Text('Xoá bộ nhớ đệm')),
            ],
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(12),
              children: [
                Text(
                  _root ?? '',
                  style: const TextStyle(color: Colors.white54, fontSize: 12),
                ),
                const SizedBox(height: 8),
                if (!_access) _permissionCard(),
                if (_access && _error != null) _note(_error!),
                if (_access && _error == null && _sources.isEmpty)
                  _note(
                    'Chưa thấy đời dữ liệu nào (games_genN) trong thư mục này. Vòng lặp Termux ghi vào '
                    'Download/FairyZero; có thể đổi thư mục ở menu ⋮.',
                  ),
                for (final s in _sources) _tile(s),
              ],
            ),
    );
  }

  Widget _note(String text) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 12),
    child: Text(text, style: const TextStyle(color: Colors.orangeAccent)),
  );

  Widget _permissionCard() => Card(
    color: const Color(0xFF4A3B1A),
    child: Padding(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Cần quyền truy cập tệp',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          const SizedBox(height: 6),
          const Text(
            'Dữ liệu huấn luyện do Termux ghi trong bộ nhớ chung; Android chỉ cho app đọc khi bạn bật '
            '"Cho phép truy cập mọi tệp" cho app này (một lần). Bật xong, quay lại app.',
          ),
          const SizedBox(height: 10),
          FilledButton(
            onPressed: AndroidPaths.requestAllFilesAccess,
            child: const Text('Mở cài đặt quyền'),
          ),
        ],
      ),
    ),
  );

  Widget _tile(_Source s) {
    final sub = s.isZip
        ? 'gói zip · ${_when(s.modified)}'
        : '${s.games} ván · ${_when(s.modified)}${s.cached ? ' · đã đổi' : ''}';
    return Card(
      color: const Color(0xFF3A3835),
      child: ListTile(
        leading: Icon(
          s.isZip ? Icons.folder_zip_outlined : Icons.folder_outlined,
          size: 32,
        ),
        title: Text(
          s.title,
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        ),
        subtitle: Text(sub),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => _open(s),
      ),
    );
  }
}

/// Hộp thoại tiến độ: đổi nguồn sang bảng ván (nếu chưa có hoặc nguồn đã đổi), rồi đóng với `true`.
class _ConvertDialog extends StatefulWidget {
  final String source;
  final String cacheDir;
  final String title;
  const _ConvertDialog({
    required this.source,
    required this.cacheDir,
    required this.title,
  });

  @override
  State<_ConvertDialog> createState() => _ConvertDialogState();
}

class _ConvertDialogState extends State<_ConvertDialog> {
  StreamSubscription<ConvertEvent>? _sub;
  int _done = 0;
  int _total = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    _sub = convert(widget.source, widget.cacheDir).listen((e) {
      if (!mounted) return;
      if (e.error != null) {
        setState(() => _error = e.error);
      } else if (e.finished) {
        Navigator.of(context).pop(true);
      } else {
        setState(() {
          _done = e.done;
          _total = e.total;
        });
      }
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final p = _total > 0 ? _done / _total : null;
    return AlertDialog(
      title: Text(widget.title),
      content: _error != null
          ? SingleChildScrollView(
              child: Text(
                _error!,
                style: const TextStyle(color: Colors.orangeAccent),
              ),
            )
          : Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _total == 0
                      ? 'Đang đọc danh sách ván…'
                      : 'Đang đổi sang bảng ván: $_done / $_total',
                ),
                const SizedBox(height: 12),
                LinearProgressIndicator(value: p),
                const SizedBox(height: 8),
                const Text(
                  'Chỉ làm một lần cho mỗi đời dữ liệu.',
                  style: TextStyle(color: Colors.white54, fontSize: 12),
                ),
              ],
            ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: Text(_error != null ? 'Đóng' : 'Huỷ'),
        ),
      ],
    );
  }
}
