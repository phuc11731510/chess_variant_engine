import 'dart:async';

import '../config/launch_config.dart';
import 'native_ffi_engine.dart';

/// Đánh giá thô của mạng ở một thế (một lần chạy mạng, không tìm kiếm), phía BÊN ĐI: q = Thắng − Thua, d = Hoà,
/// m = số nửa nước còn lại; [policy] = prior thô của mọi nước hợp lệ (sau PolicySoftmaxTemp 1,0, không nhiễu), nhiều nhất
/// trước.
class DanhGiaTho {
  final double q, d, m;
  final Map<String, double> policy;
  const DanhGiaTho(this.q, this.d, this.m, this.policy);

  /// Dòng `nneval q <q> d <d> m <m> policy <nước> <P> ...` của engine; null nếu engine trả `nneval none`.
  static DanhGiaTho? parse(String line) {
    final t = line.trim().split(RegExp(r'\s+'));
    if (t.length < 5 || t[1] != 'q' || t[3] != 'd') return null;
    var m = 0.0;
    final pol = <String, double>{};
    var i = 5;
    if (i + 1 < t.length && t[i] == 'm') {
      m = double.parse(t[i + 1]);
      i += 2;
    }
    if (i < t.length && t[i] == 'policy') {
      for (i++; i + 1 < t.length; i += 2) {
        pol[t[i]] = double.parse(t[i + 1]);
      }
    }
    return DanhGiaTho(double.parse(t[2]), double.parse(t[4]), m, pol);
  }
}

/// Một nước con của một nút trong cây tìm kiếm (dòng `treechild`): Q / D phía bên đi ở nút cha.
class NutCon {
  final String move;
  final int n;
  final double p, q, d;
  final bool terminal;
  const NutCon(this.move, this.n, this.p, this.q, this.d, this.terminal);
}

/// Một nút của cây (lệnh `tree <đường đi>`): N, Q / D phía bên đi ở nút, M, và các nước con (nhiều lượt nhất trước).
class NutCay {
  final List<String> path;
  final int n;
  final double q, d, m;
  final bool terminal;
  final List<NutCon> children;
  const NutCay(this.path, this.n, this.q, this.d, this.m, this.terminal, this.children);

  static NutCay parse(List<String> path, List<String> lines) {
    final err = lines.where((l) => l.startsWith('treeerror')).toList();
    if (err.isNotEmpty) throw StateError(err.first.substring('treeerror'.length).trim());
    final head = lines.firstWhere((l) => l.startsWith('treenode '));
    final h = _fields(head);
    final kids = <NutCon>[];
    for (final l in lines) {
      if (!l.startsWith('treechild ')) continue;
      final f = _fields(l);
      kids.add(NutCon(l.split(' ')[1], int.parse(f['N']!), double.parse(f['P']!), double.parse(f['Q']!),
          double.parse(f['D']!), l.endsWith(' T')));
    }
    return NutCay(path, int.parse(h['N']!), double.parse(h['Q']!), double.parse(h['D']!), double.parse(h['M']!),
        head.endsWith(' T'), kids);
  }

  static Map<String, String> _fields(String l) {
    final t = l.split(' ');
    final out = <String, String>{};
    for (var i = 1; i + 1 < t.length; i++) {
      if (const {'N', 'P', 'Q', 'D', 'M'}.contains(t[i])) out[t[i]] = t[i + 1];
    }
    return out;
  }
}

/// Tiến độ một lần tìm: số lượt ở gốc, tốc độ; [done] khi engine trả `bestmove`.
class TienDoTim {
  final int nodes, nps;
  final bool done;
  final String? bestmove;
  const TienDoTim(this.nodes, this.nps, {this.done = false, this.bestmove});
}

/// Thông số tìm kiếm của màn phân tích: như tìm SÂU lúc sinh dữ liệu (ô 04 + selfplay_mode.cc), trừ nhiễu Dirichlet
/// (tắt: xem mạng nghĩ gì, không phải mô phỏng lại một ván) và giữ cây giữa các lần `go` (để "tìm thêm").
const List<(String, String)> kThongSoPhanTich = [
  ('PolicySoftmaxTemp', '1.0'),
  ('cpuct', '1.5'),
  ('cpuct-factor', '0'),
  ('fpu-value', '0'),
  ('two-fold-draws', 'false'),
  ('sticky-endgames', 'false'),
  ('noise-epsilon', '0'),
  ('Temperature', '0'),
  ('ReuseTree', 'true'),
  ('RootStats', 'true'),
  ('task-workers', '0'),
  ('max-prefetch', '0'),
  ('minibatch-size', '16'),
  ('nn-cache-size', '30000'), // mỗi mục giữ prior của mọi nước (vài KB): 30k mục ~ vài chục MB, đủ cho lần tìm 20k lượt
];

/// Engine phân tích của màn xem ván: MỘT engine đã nạp một mạng (gen [gen]), dùng chung cho prior thô của bảng tìm
/// kiếm và cho màn phân tích (tìm kiếm + xem cây). Các lệnh được xếp hàng (engine chỉ trả lời một lệnh một lúc).
/// Cây tìm kiếm là của thế được `position` sau cùng. Tính prior thô ở một thế KHÁC phải đặt thế đó lên engine, nên cây cũ
/// mất: [treePosition] cho biết cây hiện thuộc thế nào, và [cay] báo lỗi khi cây đã bị thay.
///
/// Chạy mạng bằng GPU khi được (TFLite + GPU delegate, FP16, lô 16: ~66 lượt tìm / giây trên SM-X110), không thì CPU (ONNX
/// Runtime 4 luồng, ~19 lượt / giây). Đo 2026-11-27, Helio G99, mạng 10 lớp d 192: ORT CPU ≈ XNNPACK ≈ 15-20 thế / giây;
/// NNAPI (GPU / APU qua trình điều khiển MediaTek) chỉ ~3,8; GPU delegate của TFLite ~80 thế / giây ở lô 16.
class PhanTich {
  final int gen;
  final String onnxPath;

  /// Mạng GPU (TFLite) nếu có: trả đường dẫn (tạo khi cần), null = chỉ dùng CPU.
  final Future<String?> Function()? gpuModel;
  final int threads;
  final int ruleSet;
  NativeFfiEngine? _e;

  /// Engine đang chạy mạng bằng gì: 'GPU' hoặc 'CPU' (null khi chưa khởi động).
  String? dangDung;

  /// Lý do không dùng được GPU (đã lùi về CPU), nếu có.
  String? loiGpu;
  Future<void> _queue = Future.value();
  String? _position; // lệnh position đã gửi sau cùng
  String? _treePosition; // lệnh position của cây hiện có (null = chưa tìm)
  bool _searching = false;

  PhanTich({required this.gen, required this.onnxPath, this.gpuModel, this.threads = 4, this.ruleSet = 0});

  String? get treePosition => _treePosition;
  bool get searching => _searching;

  static String positionCmd(String startFen, List<String> moves) =>
      'position fen $startFen${moves.isEmpty ? '' : ' moves ${moves.join(' ')}'}';

  Future<T> _run<T>(Future<T> Function(NativeFfiEngine e) f) {
    final c = Completer<T>();
    _queue = _queue.then((_) async {
      try {
        c.complete(await f(await _engine()));
      } catch (err, st) {
        c.completeError(err, st);
      }
    });
    return c.future;
  }

  Future<NativeFfiEngine> _engine() async {
    final e = _e;
    if (e != null) return e;
    // GPU trước (TFLite + GPU delegate, ~3,4 lần CPU trên máy bảng); không dựng được thì CPU (ONNX Runtime).
    final gpu = gpuModel;
    if (gpu != null) {
      try {
        final path = await gpu();
        if (path != null) {
          final n = await _start(path, 'gpu', 2);
          // Engine vẫn trả readyok khi không dựng được mạng: hỏi thử một lần chạy mạng.
          n.sendRaw('position startpos');
          final r = await n.collect('nneval', (l) => l.startsWith('nneval'), timeout: const Duration(seconds: 60));
          if (!r.last.startsWith('nneval none')) {
            _position = 'position startpos';
            dangDung = 'GPU';
            return _e = n;
          }
          await n.dispose();
          loiGpu = 'engine không dựng được mạng GPU';
        }
      } catch (err) {
        loiGpu = '$err';
      }
    }
    final n = await _start(onnxPath, 'cpu', threads);
    dangDung = 'CPU';
    return _e = n;
  }

  Future<NativeFfiEngine> _start(String model, String provider, int backendThreads) async {
    final n = NativeFfiEngine(
      LaunchConfig(enginePath: '', modelPath: model, provider: provider),
      ruleSet: ruleSet,
      uciOptions: [('BackendThreads', '$backendThreads'), ...kThongSoPhanTich],
    );
    await n.start();
    return n;
  }

  void _setPosition(NativeFfiEngine e, String cmd) {
    if (cmd == _position) return;
    e.sendRaw(cmd);
    _position = cmd;
  }

  /// Prior thô + giá trị thô ở thế sau [moves] (từ [startFen], đủ lịch sử như lúc sinh ván).
  Future<DanhGiaTho?> danhGia(String startFen, List<String> moves) => _run((e) async {
        _setPosition(e, positionCmd(startFen, moves));
        final lines = await e.collect('nneval policy', (l) => l.startsWith('nneval'), timeout: const Duration(seconds: 60));
        return DanhGiaTho.parse(lines.last);
      });

  /// Tìm [nodes] lượt ở thế sau [moves]. [fresh] = bỏ cây cũ (kể cả khi cùng thế); không thì cùng thế = tìm THÊM vào
  /// cây đang có. [onProgress] nhận tiến độ theo các dòng `info` của engine.
  Future<TienDoTim> tim(String startFen, List<String> moves, int nodes,
          {bool fresh = false, void Function(TienDoTim)? onProgress}) =>
      _run((e) async {
        final cmd = positionCmd(startFen, moves);
        if (fresh || cmd != _treePosition) {
          e.sendRaw('ucinewgame');
          _position = null;
        }
        _setPosition(e, cmd);
        _treePosition = cmd;
        _searching = true;
        var last = const TienDoTim(0, 0);
        try {
          final lines = await e.collect('go nodes $nodes', (l) => l.startsWith('bestmove'),
              timeout: const Duration(hours: 2), onLine: (l) {
            if (!l.startsWith('info ')) return;
            final n = _int(l, 'nodes'), s = _int(l, 'nps');
            if (n == null) return;
            last = TienDoTim(n, s ?? last.nps);
            onProgress?.call(last);
          });
          final bm = lines.last.split(' ');
          return TienDoTim(last.nodes, last.nps, done: true, bestmove: bm.length > 1 ? bm[1] : null);
        } finally {
          _searching = false;
        }
      });

  /// Dừng lần tìm đang chạy (engine vẫn trả `bestmove`, [tim] kết thúc bình thường). Không xếp hàng: gửi ngay.
  void dung() {
    if (_searching) _e?.sendRaw('stop');
  }

  /// Nút của cây hiện có sau các nước [path] tính từ gốc (thế của lần tìm sau cùng).
  Future<NutCay> cay(List<String> path) => _run((e) async {
        if (_treePosition == null) throw StateError('chưa tìm kiếm');
        if (_position != _treePosition) throw StateError('cây đã bị thay (prior thô của thế khác); tìm lại');
        final lines = await e.collect('tree ${path.join(' ')}'.trim(),
            (l) => l.startsWith('treeend') || l.startsWith('treeerror'), timeout: const Duration(seconds: 30));
        return NutCay.parse(path, lines);
      });

  Future<void> dispose() async {
    final e = _e;
    _e = null;
    if (e != null) {
      e.sendRaw('stop');
      await e.dispose();
    }
  }

  static int? _int(String line, String key) {
    final m = RegExp('(?:^| )$key (\\d+)').firstMatch(line);
    return m == null ? null : int.parse(m.group(1)!);
  }
}
