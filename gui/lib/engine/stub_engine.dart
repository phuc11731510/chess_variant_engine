import 'engine_service.dart';
import '../domain/board_state.dart' show kVariantStartposFen;

/// M0 placeholder engine for mobile (Android/iOS).
///
/// There is no native engine on the phone yet, so the board RENDERS (startpos)
/// but the machine does not move and no legal moves are offered. This keeps the
/// app launchable on Android without spawning a subprocess (which Android
/// forbids). Replaced by `NativeFfiEngine` (dart:ffi -> libfairyzero.so) at M4.
class StubEngine implements EngineService {
  String _fen = kVariantStartposFen;

  @override
  Future<void> start() async {}

  @override
  Future<void> newGame({String? fen}) async {
    _fen = fen ?? kVariantStartposFen;
  }

  @override
  Future<void> applyMove(String uci) async {}

  @override
  Future<List<String>> legalMoves() async => const [];

  @override
  Future<String> currentFen() async => _fen;

  @override
  Future<GameResult> gameResult() async => GameResult.undecided;

  @override
  Future<String> bestMove() async => '0000';

  @override
  Future<void> dispose() async {}
}
