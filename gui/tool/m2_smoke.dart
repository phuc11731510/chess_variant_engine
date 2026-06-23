// Smoke test M2 (headless, chạy bằng `dart run`): spawn engine thật, làm trình
// tự khởi động, in FEN xuất phát + danh sách nước hợp lệ + kết quả.
//
// Chạy (từ thư mục gui\):
//   dart run tool/m2_smoke.dart --engine <duong_dan_custom_engine.exe> [--model x.onnx --provider dml]
//
// Không cần Flutter — chỉ dùng dart:io qua UciProcessEngine.

// ignore_for_file: avoid_print

import 'package:fairyzero_gui/config/launch_config.dart';
import 'package:fairyzero_gui/engine/uci_process_engine.dart';

Future<void> main(List<String> args) async {
  final cfg = LaunchConfig.fromArgs(args);
  print('== M2 smoke ==');
  print('engine   = ${cfg.enginePath}');
  print('model    = ${cfg.modelPath ?? "(khong nap model — du cho fen/legalmoves)"}');
  print('provider = ${cfg.provider}');

  final eng = UciProcessEngine(cfg, verbose: args.contains('--verbose'));
  try {
    await eng.start();
    print('handshake OK (uciok + readyok)');

    await eng.newGame();
    final fen = await eng.currentFen();
    print('FEN xuat phat: $fen');

    final lm = await eng.legalMoves();
    print('Nuoc hop le (${lm.length}): ${lm.join(' ')}');

    final res = await eng.gameResult();
    print('Ket qua: $res');

    // Bonus: neu co model -> thu duong go->bestmove (de-risk M4).
    if (cfg.modelPath != null) {
      print('Dang cho engine nghi (${cfg.thinkSummary})...');
      final mv = await eng.bestMove();
      print('bestmove: $mv');
    }
  } catch (e) {
    print('LOI: $e');
  } finally {
    await eng.dispose();
    print('done.');
  }
}
