import 'dart:async';
import 'dart:convert';
import 'dart:io';

/// Thế cuối của một ván theo engine: FEN, số nước hợp lệ, kết quả (`white` / `black` / `draw` / `undecided`).
/// Dùng để biết LÝ DO ván kết thúc (hết nước đi, đủ số lần chiếu, luật 50 nước, lặp thế...) và số quân còn lại.
class FinalInfo {
  final String fen;
  final int legalCount;
  final String result;
  const FinalInfo(this.fen, this.legalCount, this.result);
}

/// Bộ luật cờ (engine, không cần mạng) trả lời thế cuối của một dãy nước.
abstract class FinalOracle {
  /// Đi hết [moves] từ [fen] rồi hỏi thế cuối. Giống `May.the_cuoi` của `xem_du_lieu.py`.
  Future<FinalInfo> query(String fen, List<String> moves);
  Future<void> close();
}

/// Engine UCI chạy như tiến trình con (`custom_engine --uci-nn`): dùng trên máy tính (kiểm thử, xem_lai).
class ProcessFinalOracle implements FinalOracle {
  final Process _p;
  final List<String> _buf = [];
  Completer<void>? _wake;
  late final StreamSubscription<String> _sub;

  ProcessFinalOracle._(this._p) {
    _sub = _p.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((l) {
          _buf.add(l);
          _wake?.complete();
          _wake = null;
        });
  }

  static Future<ProcessFinalOracle> start(String exe) async {
    final p = await Process.start(exe, [
      '--uci-nn',
    ], workingDirectory: File(exe).parent.path);
    final o = ProcessFinalOracle._(p);
    o._send('uci');
    await o._until((l) => l == 'uciok');
    return o;
  }

  void _send(String s) => _p.stdin.writeln(s);

  Future<String> _until(bool Function(String) ok) async {
    while (true) {
      while (_buf.isNotEmpty) {
        final l = _buf.removeAt(0).trim();
        if (ok(l)) return l;
      }
      _wake = Completer<void>();
      await _wake!.future.timeout(
        const Duration(seconds: 30),
        onTimeout: () => throw StateError('engine không trả lời'),
      );
    }
  }

  @override
  Future<FinalInfo> query(String fen, List<String> moves) async {
    _send('ucinewgame');
    _send(
      'position fen $fen${moves.isEmpty ? '' : ' moves ${moves.join(' ')}'}',
    );
    _send('fen');
    final f = await _until((l) => l.startsWith('fen '));
    _send('legalmoves');
    final lm = await _until((l) => l.startsWith('legalmoves'));
    _send('result');
    final r = await _until((l) => l.startsWith('result '));
    return FinalInfo(
      f.substring(4),
      lm.split(RegExp(r'\s+')).length - 1,
      r.split(RegExp(r'\s+'))[1],
    );
  }

  @override
  Future<void> close() async {
    try {
      _send('quit');
      await _p.exitCode.timeout(const Duration(seconds: 5));
    } catch (_) {
      _p.kill();
    }
    await _sub.cancel();
  }
}
