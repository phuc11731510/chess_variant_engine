import 'dart:async';
import 'dart:convert';
import 'dart:io';

import '../config/launch_config.dart';
import 'engine_service.dart';

/// Hiện thực [EngineService] cho DESKTOP: spawn `custom_engine.exe --uci-nn`,
/// trao đổi bằng văn bản UCI qua stdin/stdout (Kiểu A trong kế hoạch).
///
/// Mọi output engine được đọc **bất đồng bộ** qua một Stream (không khựng UI).
/// Mẫu request→response: gửi lệnh rồi `await` dòng phản hồi thoả điều kiện. Vì
/// engine xử lý lệnh tuần tự trên một luồng đọc, ta gửi/đợi tuần tự là an toàn.
class UciProcessEngine implements EngineService {
  final LaunchConfig config;

  Process? _proc;
  StreamSubscription<String>? _outSub;
  StreamSubscription<String>? _errSub;
  bool _started = false;

  /// Lịch sử nước (UCI thật) tính từ thế gốc — luôn gửi lại đầy đủ để engine
  /// tận dụng tree-reuse (xem kế hoạch §5.3).
  final List<String> _moves = [];
  String _basePositionCmd = 'position startpos';

  /// Các yêu cầu đang chờ một dòng output khớp predicate (xử lý tuần tự).
  final List<_Pending> _pending = [];

  /// Bật để in mọi dòng engine ra log khi gỡ lỗi.
  final bool verbose;

  UciProcessEngine(this.config, {this.verbose = false});

  @override
  Future<void> start() async {
    if (_started) return;
    final exeFile = File(config.enginePath);
    if (!exeFile.existsSync()) {
      throw EngineException('Khong tim thay engine: ${config.enginePath}');
    }
    // workingDirectory = thư mục engine để DLL (onnxruntime...) + model tương
    // đối resolve đúng.
    _proc = await Process.start(
      exeFile.absolute.path,
      const ['--uci-nn'],
      workingDirectory: exeFile.parent.absolute.path,
    );

    _outSub = _proc!.stdout
        .transform(const Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen(_onLine);
    _errSub = _proc!.stderr
        .transform(const Utf8Decoder(allowMalformed: true))
        .transform(const LineSplitter())
        .listen((l) {
      // ignore: avoid_print
      print('[engine:stderr] $l');
    });

    // --- Handshake UCI ---
    _send('uci');
    await _expect((l) => l.trim() == 'uciok',
        timeout: const Duration(seconds: 10), what: 'uciok');

    if (config.modelPath != null) {
      _send('setoption name WeightsFile value ${config.modelPath}');
    }
    _send('setoption name Provider value ${config.provider}');
    if (config.visits != null) {
      _send('setoption name Visits value ${config.visits}');
    }

    // isready: engine (re)dựng backend nếu có model -> chờ lâu hơn.
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
    final line = await _expect((l) => l.startsWith('legalmoves'), what: 'legalmoves');
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
    try {
      _send('quit');
    } catch (_) {}
    await _outSub?.cancel();
    await _errSub?.cancel();
    _proc?.kill();
    _proc = null;
    _started = false;
    // Hủy mọi yêu cầu đang chờ.
    for (final p in _pending) {
      if (!p.completer.isCompleted) {
        p.completer.completeError(EngineException('Engine da dong'));
      }
    }
    _pending.clear();
  }

  // ----------------- nội bộ -----------------

  void _ensureStarted() {
    if (!_started) throw EngineException('Engine chua start()');
  }

  void _sendPosition() {
    final mv = _moves.isEmpty ? '' : ' moves ${_moves.join(' ')}';
    _send('$_basePositionCmd$mv');
  }

  /// Rào đồng bộ: `position`/`ucinewgame` không có phản hồi, dùng isready/readyok
  /// để chắc engine đã xử lý xong trước khi đi tiếp.
  Future<void> _syncReady() async {
    _send('isready');
    await _expect((l) => l.trim() == 'readyok',
        timeout: const Duration(seconds: 30), what: 'readyok');
  }

  void _send(String cmd) {
    if (verbose) {
      // ignore: avoid_print
      print('[engine:<<] $cmd');
    }
    _proc?.stdin.writeln(cmd);
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

class EngineException implements Exception {
  final String message;
  EngineException(this.message);
  @override
  String toString() => 'EngineException: $message';
}
