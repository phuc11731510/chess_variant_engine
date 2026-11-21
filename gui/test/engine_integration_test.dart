// Nối với engine THẬT (không cần mạng .onnx): thế xuất phát của GUI phải khớp engine, mọi nước
// engine đưa ra đều đọc được, và mọi quân trên bàn đều có ảnh. Chỉ chạy khi đặt biến môi trường:
//   $env:FZ_ENGINE = "D:\chess_variant\custom_engine\build\custom_engine.exe"; flutter test test/engine_integration_test.dart

import 'dart:io';
import 'dart:math';

import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/config/launch_config.dart';
import 'package:fairyzero_gui/domain/board_state.dart';
import 'package:fairyzero_gui/domain/uci_move.dart';
import 'package:fairyzero_gui/engine/uci_process_engine.dart';
import 'package:fairyzero_gui/ui/piece_assets.dart';

void main() {
  final exe = Platform.environment['FZ_ENGINE'];

  test(
    'engine thật: thế xuất phát khớp GUI, nước đi đọc được, mọi quân có ảnh',
    () async {
      final engine = UciProcessEngine(LaunchConfig(enginePath: exe!, visits: 1));
      await engine.start();
      try {
        await engine.newGame();
        final fen = await engine.currentFen();
        expect(fen, kVariantStartposFen, reason: 'GUI và engine lệch thế xuất phát');

        final rng = Random(7);
        var seen = 0;
        for (int ply = 0; ply < 120; ply++) {
          final legal = await engine.legalMoves();
          if (legal.isEmpty) break;
          for (final m in legal) {
            expect(UciMove.tryParse(m), isNotNull, reason: 'GUI không đọc được nước $m');
          }
          final board = BoardState.fromFen(await engine.currentFen());
          for (int r = 0; r < 10; r++) {
            for (int f = 0; f < 10; f++) {
              final p = board.at(r, f);
              if (p == null) continue;
              expect(PieceAssets.pieceTypes, contains(p.type), reason: 'quân ${p.letter} không có ảnh');
              seen++;
            }
          }
          await engine.applyMove(legal[rng.nextInt(legal.length)]);
        }
        expect(seen, greaterThan(1000));
      } finally {
        await engine.dispose();
      }
    },
    skip: exe == null ? 'đặt FZ_ENGINE=đường dẫn custom_engine.exe để chạy' : false,
    timeout: const Timeout(Duration(minutes: 3)),
  );
}
