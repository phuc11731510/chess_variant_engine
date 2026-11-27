import 'dart:async';
import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';
import 'package:flutter/services.dart' show MethodChannel;

import '../config/launch_config.dart';
import 'engine_service.dart';
import 'uci_process_engine.dart' show EngineException;

// --- Chữ ký C ABI (khớp src/app/fairyzero_ffi.h) ---
typedef _FzCreateC = Pointer<Void> Function(Pointer<Utf8>, Pointer<Utf8>);
typedef _FzCreateD = Pointer<Void> Function(Pointer<Utf8>, Pointer<Utf8>);
typedef _FzSendC = Void Function(Pointer<Void>, Pointer<Utf8>);
typedef _FzSendD = void Function(Pointer<Void>, Pointer<Utf8>);
typedef _FzPollC = Int32 Function(Pointer<Void>, Pointer<Uint8>, Int32);
typedef _FzPollD = int Function(Pointer<Void>, Pointer<Uint8>, int);
typedef _FzDestroyC = Void Function(Pointer<Void>);
typedef _FzDestroyD = void Function(Pointer<Void>);

/// Hiện thực [EngineService] cho ANDROID: nạp `libfairyzero.so` và gọi C ABI
/// (`fz_create/send/poll/destroy`) qua `dart:ffi`, thay vì spawn tiến trình con
/// như desktop (Android cấm spawn). Engine chạy IN-PROCESS; search diễn ra trên
/// luồng worker native, output (info/bestmove/legalmoves/...) được đẩy vào hàng
/// đợi và ta DRAIN bằng `fz_poll` định kỳ qua một [Timer].
///
/// Giao thức UCI trao đổi GIỐNG HỆT [UciProcessEngine]; chỉ lớp truyền tải đổi.
class NativeFfiEngine implements EngineService, RuleSetSwitcher {
  final LaunchConfig config;
  final bool verbose;

  /// Chỉ luật cờ (xem lại ván): không nạp mạng, không `isready`, không tìm kiếm. `position / fen / legalmoves /
  /// result` của engine chạy ngay trong `fz_send` nên mỗi câu hỏi được trả lời tức thì (không đợi nhịp của bộ
  /// đếm giờ): mở một ván 150 nước mất vài chục mili-giây thay vì vài giây.
  final bool rulesOnly;

  /// Tuỳ chọn UCI gửi TRƯỚC `isready` (lúc engine nạp mạng), để mạng chỉ dựng một lần (vd PolicySoftmaxTemp).
  final List<(String, String)> uciOptions;

  NativeFfiEngine(
    this.config, {
    this.verbose = false,
    this.rulesOnly = false,
    this.uciOptions = const [],
    int ruleSet = 0,
  }) : _libIdx = ruleSet;

  /// Kênh hỏi đường dẫn hệ thống (xem MainActivity.kt).
  static const MethodChannel _paths = MethodChannel('fairyzero/paths');

  /// Thư viện của từng bộ luật: [0] luật hiện tại, [1] luật trước 2026-11-24 (xem [RuleSetSwitcher]).
  static const List<String> _libNames = ['libfairyzero.so', 'libfzcu.so'];
  int _libIdx;

  /// Bộ luật đang dùng: 0 = luật hiện tại, 1 = luật trước 2026-11-24 (sau [switchRuleSet]).
  int get ruleSet => _libIdx;

  late DynamicLibrary _lib;
  late _FzCreateD _fzCreate;
  late _FzSendD _fzSend;
  late _FzPollD _fzPoll;
  late _FzDestroyD _fzDestroy;

  Pointer<Void> _handle = nullptr;
  bool _started = false;

  // Buffer tái sử dụng cho fz_poll (một dòng UCI; legalmoves có thể dài).
  static const int _bufCap = 65536;
  late Pointer<Uint8> _buf;

  // Lịch sử nước tính từ thế gốc — gửi lại đầy đủ để engine tái dùng cây.
  final List<String> _moves = [];
  String _basePositionCmd = 'position startpos';

  /// Yêu cầu đang chờ một dòng output khớp predicate (xử lý tuần tự).
  final List<_Pending> _pending = [];

  /// Lần gom nhiều dòng đang chạy ([collect]), hoặc null.
  _Collector? _collector;

  /// Timer drain hàng đợi output native. KHÔNG pump ngay trong [_send] để tránh
  /// nuốt phản hồi đồng bộ TRƯỚC khi [_expect] kịp đăng ký pending; thay vào đó
  /// drain qua timer (pending luôn được đăng ký xong trước khi timer chạy lần kế).
  Timer? _pollTimer;

  // ----------------- vòng đời -----------------

  @override
  Future<void> start() async {
    if (_started) return;

    _lib = _openLib();
    _fzCreate = _lib.lookupFunction<_FzCreateC, _FzCreateD>('fz_create');
    _fzSend = _lib.lookupFunction<_FzSendC, _FzSendD>('fz_send');
    _fzPoll = _lib.lookupFunction<_FzPollC, _FzPollD>('fz_poll');
    _fzDestroy = _lib.lookupFunction<_FzDestroyC, _FzDestroyD>('fz_destroy');
    _buf = malloc.allocate<Uint8>(_bufCap);

    final modelPath = rulesOnly ? '' : await _resolveModelPath();
    final provider = config.provider; // 'cpu' trên Android (mặc định)

    final pModel = modelPath.toNativeUtf8();
    final pProvider = provider.toNativeUtf8();
    try {
      _handle = _fzCreate(pModel, pProvider);
    } finally {
      malloc.free(pModel);
      malloc.free(pProvider);
    }
    if (_handle == nullptr) {
      throw EngineException('fz_create that bai (model: $modelPath)');
    }

    // Drain hàng đợi định kỳ (bestmove/info đến bất đồng bộ; phản hồi đồng bộ
    // như legalmoves cũng được nhặt ở nhịp kế).
    _pollTimer = Timer.periodic(
      const Duration(milliseconds: 15),
      (_) => _pump(),
    );

    // --- Handshake UCI ---
    _send('uci');
    await _expect(
      (l) => l.trim() == 'uciok',
      timeout: const Duration(seconds: 10),
      what: 'uciok',
    );

    if (rulesOnly) {
      _started = true;
      return;
    }

    // Tận dụng đa nhân điện thoại cho lượng giá NN (M2: 1→18, 4→62 nps).
    _send('setoption name BackendThreads value 4');
    _send('setoption name Provider value $provider');
    if (config.visits != null) {
      _send('setoption name Visits value ${config.visits}');
    }
    for (final (name, value) in uciOptions) {
      _send('setoption name $name value $value');
    }

    // isready: EnsureBackend nạp model (ĐỒNG BỘ — block ngắn trên isolate lúc
    // khởi động). readyok được đẩy vào hàng đợi rồi timer nhặt.
    _send('isready');
    await _expect(
      (l) => l.trim() == 'readyok',
      timeout: const Duration(seconds: 60),
      what: 'readyok',
    );
    _started = true;
  }

  @override
  Future<void> newGame({String? fen}) async {
    _ensureStarted();
    _send('ucinewgame');
    _moves.clear();
    final base = fen ?? config.startFen;
    _basePositionCmd = (base == null || base.isEmpty)
        ? 'position startpos'
        : 'position fen $base';
    _sendPosition();
    if (!rulesOnly) await _syncReady();
  }

  @override
  Future<void> applyMove(String uci) async {
    _ensureStarted();
    _moves.add(uci);
    _sendPosition();
    if (!rulesOnly) await _syncReady();
  }

  @override
  Future<List<String>> legalMoves() async {
    _ensureStarted();
    final line = await _request(
      'legalmoves',
      (l) => l.startsWith('legalmoves'),
      what: 'legalmoves',
    );
    final parts = line.trim().split(RegExp(r'\s+'));
    return parts.length > 1 ? parts.sublist(1) : <String>[];
  }

  @override
  Future<String> currentFen() async {
    _ensureStarted();
    final line = await _request('fen', (l) => l.startsWith('fen '), what: 'fen');
    return line.substring(4).trim();
  }

  @override
  Future<GameResult> gameResult() async {
    _ensureStarted();
    final line = await _request('result', (l) => l.startsWith('result '), what: 'result');
    switch (line.substring(7).trim()) {
      case 'white':
        return GameResult.white;
      case 'black':
        return GameResult.black;
      case 'draw':
        return GameResult.draw;
      default:
        return GameResult.undecided;
    }
  }

  @override
  Future<String> bestMove() async {
    _ensureStarted();
    if (config.visits != null) {
      _send('go nodes ${config.visits}');
    } else {
      _send(
        'go movetime ${config.movetimeMs ?? LaunchConfig.defaultMovetimeMs}',
      );
    }
    final line = await _expect(
      (l) => l.startsWith('bestmove'),
      timeout: const Duration(minutes: 5),
      what: 'bestmove',
    );
    final parts = line.trim().split(RegExp(r'\s+'));
    return parts.length > 1 ? parts[1] : '0000';
  }

  @override
  Future<void> dispose() async {
    _pollTimer?.cancel();
    _pollTimer = null;
    if (_handle != nullptr) {
      try {
        _send('quit');
      } catch (_) {}
      _fzDestroy(_handle);
      _handle = nullptr;
    }
    if (_started || _buf != nullptr) {
      try {
        malloc.free(_buf);
      } catch (_) {}
    }
    _started = false;
    for (final p in _pending) {
      if (!p.completer.isCompleted) {
        p.completer.completeError(EngineException('Engine da dong'));
      }
    }
    _pending.clear();
    final c = _collector;
    _collector = null;
    if (c != null && !c.completer.isCompleted) {
      c.completer.completeError(EngineException('Engine da dong'));
    }
  }

  // ----------------- lệnh thô (phân tích: nneval / go / tree) -----------------

  /// Gửi một dòng UCI không chờ trả lời (vd `position ...`, `setoption ...`, `stop`).
  void sendRaw(String cmd) {
    _ensureStarted();
    _send(cmd);
  }

  /// Gửi [cmd] rồi gom MỌI dòng engine in ra cho tới dòng [isLast] (tính cả dòng đó); [onLine] thấy từng dòng ngay khi
  /// tới (vd tiến độ `info ... nodes`). Chỉ một lần gom mỗi lúc (người gọi tự xếp hàng); trong lúc gom, các dòng không
  /// đi tới các yêu cầu chờ khác.
  Future<List<String>> collect(
    String cmd,
    bool Function(String) isLast, {
    Duration timeout = const Duration(seconds: 30),
    void Function(String)? onLine,
  }) {
    _ensureStarted();
    if (_collector != null) {
      throw EngineException('Engine dang tra loi lenh khac');
    }
    final c = _Collector(isLast, onLine);
    _collector = c;
    _send(cmd);
    _pump();
    return c.completer.future.timeout(
      timeout,
      onTimeout: () {
        if (identical(_collector, c)) _collector = null;
        throw EngineException('Engine khong tra loi "$cmd" dung han');
      },
    );
  }

  @override
  Future<bool> switchRuleSet() async {
    // Chỉ khi xem lại ván (không mạng, không tìm kiếm) và máy có thư viện luật kia.
    if (!rulesOnly || !Platform.isAndroid) return false;
    final next = (_libIdx + 1) % _libNames.length;
    if (next == _libIdx) return false;
    try {
      DynamicLibrary.open(_libNames[next]);
    } catch (_) {
      return false;
    }
    await dispose();
    _libIdx = next;
    await start();
    return true;
  }

  // ----------------- nội bộ -----------------

  DynamicLibrary _openLib() {
    if (Platform.isAndroid) return DynamicLibrary.open(_libNames[_libIdx]);
    // iOS: liên kết tĩnh vào tiến trình (chưa hỗ trợ ở M4).
    return DynamicLibrary.process();
  }

  /// Đường dẫn model.onnx: ưu tiên --model nếu có & tồn tại; nếu không lấy trong
  /// thư mục external-files RIÊNG của app (adb push vào đây, app luôn đọc được).
  Future<String> _resolveModelPath() async {
    final cfg = config.modelPath;
    if (cfg != null && cfg.isNotEmpty && File(cfg).existsSync()) return cfg;
    final dir = await _paths.invokeMethod<String>('externalFilesDir');
    if (dir != null && dir.isNotEmpty) {
      final p = '$dir/model.onnx';
      if (File(p).existsSync()) return p;
      throw EngineException(
        'Chua thay model: $p\n(adb push <net>.onnx vao thu muc nay)',
      );
    }
    throw EngineException('Khong xac dinh duoc thu muc model tren thiet bi');
  }

  void _ensureStarted() {
    if (!_started) throw EngineException('Engine chua start()');
  }

  void _sendPosition() {
    final mv = _moves.isEmpty ? '' : ' moves ${_moves.join(' ')}';
    _send('$_basePositionCmd$mv');
  }

  Future<void> _syncReady() async {
    _send('isready');
    await _expect(
      (l) => l.trim() == 'readyok',
      timeout: const Duration(seconds: 30),
      what: 'readyok',
    );
  }

  void _send(String cmd) {
    if (_handle == nullptr) return;
    if (verbose) {
      // ignore: avoid_print
      print('[engine:<<] $cmd');
    }
    final p = cmd.toNativeUtf8();
    try {
      _fzSend(_handle, p);
    } finally {
      malloc.free(p);
    }
  }

  /// Drain TẤT CẢ dòng đang chờ trong hàng đợi native (fz_poll trả 0 khi rỗng).
  void _pump() {
    if (_handle == nullptr) return;
    while (true) {
      final n = _fzPoll(_handle, _buf, _bufCap);
      if (n <= 0) break;
      final line = _buf.cast<Utf8>().toDartString(length: n);
      _onLine(line);
    }
  }

  /// Gửi [cmd] rồi lấy ngay dòng trả lời khớp [match]: đăng ký chờ TRƯỚC khi gửi, rồi rút hàng đợi native tại chỗ
  /// (các lệnh hỏi thế cờ của engine trả lời đồng bộ), không đợi nhịp của bộ đếm giờ.
  Future<String> _request(
    String cmd,
    bool Function(String) match, {
    Duration timeout = const Duration(seconds: 15),
    String what = '',
  }) {
    final f = _expect(match, timeout: timeout, what: what);
    _send(cmd);
    _pump();
    return f;
  }

  Future<String> _expect(
    bool Function(String) match, {
    Duration timeout = const Duration(seconds: 15),
    String what = '',
  }) {
    final p = _Pending(match);
    _pending.add(p);
    return p.completer.future.timeout(
      timeout,
      onTimeout: () {
        _pending.remove(p);
        throw EngineException('Engine khong phan hoi "$what" dung han');
      },
    );
  }

  void _onLine(String line) {
    if (verbose) {
      // ignore: avoid_print
      print('[engine:>>] $line');
    }
    final c = _collector;
    if (c != null) {
      c.lines.add(line);
      c.onLine?.call(line);
      if (c.isLast(line)) {
        _collector = null;
        if (!c.completer.isCompleted) c.completer.complete(c.lines);
      }
      return;
    }
    for (var i = 0; i < _pending.length; i++) {
      if (_pending[i].match(line)) {
        final p = _pending.removeAt(i);
        if (!p.completer.isCompleted) p.completer.complete(line);
        return;
      }
    }
  }
}

class _Collector {
  final bool Function(String) isLast;
  final void Function(String)? onLine;
  final List<String> lines = [];
  final Completer<List<String>> completer = Completer<List<String>>();
  _Collector(this.isLast, this.onLine);
}

class _Pending {
  final bool Function(String) match;
  final Completer<String> completer = Completer<String>();
  _Pending(this.match);
}
