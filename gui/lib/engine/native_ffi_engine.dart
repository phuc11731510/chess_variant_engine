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
class NativeFfiEngine implements EngineService {
  final LaunchConfig config;
  final bool verbose;

  NativeFfiEngine(this.config, {this.verbose = false});

  /// Kênh hỏi đường dẫn hệ thống (xem MainActivity.kt).
  static const MethodChannel _paths = MethodChannel('fairyzero/paths');

  late final DynamicLibrary _lib;
  late final _FzCreateD _fzCreate;
  late final _FzSendD _fzSend;
  late final _FzPollD _fzPoll;
  late final _FzDestroyD _fzDestroy;

  Pointer<Void> _handle = nullptr;
  bool _started = false;

  // Buffer tái sử dụng cho fz_poll (một dòng UCI; legalmoves có thể dài).
  static const int _bufCap = 65536;
  late final Pointer<Uint8> _buf;

  // Lịch sử nước tính từ thế gốc — gửi lại đầy đủ để engine tái dùng cây.
  final List<String> _moves = [];
  String _basePositionCmd = 'position startpos';

  /// Yêu cầu đang chờ một dòng output khớp predicate (xử lý tuần tự).
  final List<_Pending> _pending = [];

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

    final modelPath = await _resolveModelPath();
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
    _pollTimer = Timer.periodic(const Duration(milliseconds: 15), (_) => _pump());

    // --- Handshake UCI ---
    _send('uci');
    await _expect((l) => l.trim() == 'uciok',
        timeout: const Duration(seconds: 10), what: 'uciok');

    // Tận dụng đa nhân điện thoại cho lượng giá NN (M2: 1→18, 4→62 nps).
    _send('setoption name BackendThreads value 4');
    _send('setoption name Provider value $provider');
    if (config.visits != null) {
      _send('setoption name Visits value ${config.visits}');
    }

    // isready: EnsureBackend nạp model (ĐỒNG BỘ — block ngắn trên isolate lúc
    // khởi động). readyok được đẩy vào hàng đợi rồi timer nhặt.
    _send('isready');
    await _expect((l) => l.trim() == 'readyok',
        timeout: const Duration(seconds: 60), what: 'readyok');
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
    await _syncReady();
  }

  @override
  Future<void> applyMove(String uci) async {
    _ensureStarted();
    _moves.add(uci);
    _sendPosition();
    await _syncReady();
  }

  @override
  Future<List<String>> legalMoves() async {
    _ensureStarted();
    _send('legalmoves');
    final line =
        await _expect((l) => l.startsWith('legalmoves'), what: 'legalmoves');
    final parts = line.trim().split(RegExp(r'\s+'));
    return parts.length > 1 ? parts.sublist(1) : <String>[];
  }

  @override
  Future<String> currentFen() async {
    _ensureStarted();
    _send('fen');
    final line = await _expect((l) => l.startsWith('fen '), what: 'fen');
    return line.substring(4).trim();
  }

  @override
  Future<GameResult> gameResult() async {
    _ensureStarted();
    _send('result');
    final line = await _expect((l) => l.startsWith('result '), what: 'result');
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
      _send('go movetime ${config.movetimeMs ?? LaunchConfig.defaultMovetimeMs}');
    }
    final line = await _expect((l) => l.startsWith('bestmove'),
        timeout: const Duration(minutes: 5), what: 'bestmove');
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
  }

  // ----------------- nội bộ -----------------

  DynamicLibrary _openLib() {
    if (Platform.isAndroid) return DynamicLibrary.open('libfairyzero.so');
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
          'Chua thay model: $p\n(adb push <net>.onnx vao thu muc nay)');
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
    await _expect((l) => l.trim() == 'readyok',
        timeout: const Duration(seconds: 30), what: 'readyok');
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

  Future<String> _expect(bool Function(String) match,
      {Duration timeout = const Duration(seconds: 15), String what = ''}) {
    final p = _Pending(match);
    _pending.add(p);
    return p.completer.future.timeout(timeout, onTimeout: () {
      _pending.remove(p);
      throw EngineException('Engine khong phan hoi "$what" dung han');
    });
  }

  void _onLine(String line) {
    if (verbose) {
      // ignore: avoid_print
      print('[engine:>>] $line');
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

class _Pending {
  final bool Function(String) match;
  final Completer<String> completer = Completer<String>();
  _Pending(this.match);
}
