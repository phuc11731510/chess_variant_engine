import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';

import 'final_oracle.dart';

typedef _CreateC = Pointer<Void> Function(Pointer<Utf8>, Pointer<Utf8>);
typedef _CreateD = Pointer<Void> Function(Pointer<Utf8>, Pointer<Utf8>);
typedef _SendC = Void Function(Pointer<Void>, Pointer<Utf8>);
typedef _SendD = void Function(Pointer<Void>, Pointer<Utf8>);
typedef _PollC = Int32 Function(Pointer<Void>, Pointer<Uint8>, Int32);
typedef _PollD = int Function(Pointer<Void>, Pointer<Uint8>, int);
typedef _DestroyC = Void Function(Pointer<Void>);
typedef _DestroyD = void Function(Pointer<Void>);

/// Bộ luật cờ qua `libfairyzero.so` (Android, trong tiến trình): trả lời ĐỒNG BỘ, không cần mạng và không qua
/// bộ đếm giờ. Các lệnh `position / fen / legalmoves / result` của engine chạy ngay trong `fz_send` nên dòng trả lời
/// đã nằm sẵn trong hàng đợi khi `fz_poll`. Dùng được ở isolate nền (mỗi isolate một tay cầm engine riêng).
class FfiFinalOracle implements FinalOracle {
  late final _SendD _send;
  late final _PollD _poll;
  late final _DestroyD _destroy;
  Pointer<Void> _h = nullptr;
  final Pointer<Uint8> _buf = malloc.allocate<Uint8>(_bufCap);
  static const int _bufCap = 65536;

  FfiFinalOracle({String libName = 'libfairyzero.so'}) {
    final lib = DynamicLibrary.open(libName);
    final create = lib.lookupFunction<_CreateC, _CreateD>('fz_create');
    _send = lib.lookupFunction<_SendC, _SendD>('fz_send');
    _poll = lib.lookupFunction<_PollC, _PollD>('fz_poll');
    _destroy = lib.lookupFunction<_DestroyC, _DestroyD>('fz_destroy');
    final model = ''.toNativeUtf8();
    final provider = 'cpu'.toNativeUtf8();
    try {
      _h = create(model, provider);
    } finally {
      malloc.free(model);
      malloc.free(provider);
    }
    if (_h == nullptr) throw StateError('fz_create thất bại');
    _sendLine('uci');
    _until((l) => l == 'uciok');
  }

  void _sendLine(String s) {
    final p = s.toNativeUtf8();
    try {
      _send(_h, p);
    } finally {
      malloc.free(p);
    }
  }

  String _until(bool Function(String) ok) {
    final end = DateTime.now().add(const Duration(seconds: 30));
    while (true) {
      final n = _poll(_h, _buf, _bufCap);
      if (n > 0) {
        final l = _buf.cast<Utf8>().toDartString(length: n).trim();
        if (ok(l)) return l;
        continue;
      }
      if (DateTime.now().isAfter(end)) throw StateError('engine không trả lời');
      sleep(const Duration(microseconds: 200));
    }
  }

  @override
  Future<FinalInfo> query(String fen, List<String> moves) async {
    _sendLine('ucinewgame');
    _sendLine(
      'position fen $fen${moves.isEmpty ? '' : ' moves ${moves.join(' ')}'}',
    );
    _sendLine('fen');
    final f = _until((l) => l.startsWith('fen '));
    _sendLine('legalmoves');
    final lm = _until((l) => l.startsWith('legalmoves'));
    _sendLine('result');
    final r = _until((l) => l.startsWith('result '));
    return FinalInfo(
      f.substring(4),
      lm.split(RegExp(r'\s+')).length - 1,
      r.split(RegExp(r'\s+'))[1],
    );
  }

  @override
  Future<void> close() async {
    if (_h != nullptr) {
      try {
        _sendLine('quit');
      } catch (_) {}
      _destroy(_h);
      _h = nullptr;
      malloc.free(_buf);
    }
  }
}
