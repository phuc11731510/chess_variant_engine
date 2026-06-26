import 'dart:io' show Platform;

import 'package:flutter/material.dart';

import 'config/launch_config.dart';
import 'domain/game_controller.dart';
import 'engine/engine_service.dart';
import 'engine/uci_process_engine.dart';
import 'engine/native_ffi_engine.dart';
import 'ui/board_view.dart';

/// Chọn engine theo nền tảng: desktop spawn tiến trình UCI; Android nạp
/// libfairyzero.so qua dart:ffi ([NativeFfiEngine], M4) — chơi ngay trên máy.
EngineService _makeEngine(LaunchConfig config) {
  if (Platform.isAndroid) return NativeFfiEngine(config);
  return UciProcessEngine(config);
}

/// FairyZero GUI — điểm vào.
///
/// M4: chơi với máy bằng chạm-chạm. Chạm quân mình → tô ô đích hợp lệ → chạm ô
/// đích → đi nước → máy đáp. (Kéo-thả M5, bảng phong cấp M6.)
void main(List<String> args) {
  final config = LaunchConfig.fromArgs(args);
  // ignore: avoid_print
  print(config.toString());
  runApp(FairyZeroApp(config: config));
}

class FairyZeroApp extends StatelessWidget {
  final LaunchConfig config;
  const FairyZeroApp({super.key, required this.config});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FairyZero',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(useMaterial3: true, brightness: Brightness.dark),
      home: BoardScreen(config: config),
    );
  }
}

class BoardScreen extends StatefulWidget {
  final LaunchConfig config;
  const BoardScreen({super.key, required this.config});

  @override
  State<BoardScreen> createState() => _BoardScreenState();
}

class _BoardScreenState extends State<BoardScreen> {
  late final GameController controller;

  @override
  void initState() {
    super.initState();
    controller = GameController(
      engine: _makeEngine(widget.config),
      humanIsWhite: widget.config.humanPlaysWhite,
    );
    _start();
  }

  Future<void> _start() async {
    await controller.init();
    final demo = widget.config.demoMove;
    if (demo != null) await controller.playHumanUci(demo);
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  String _resultText(GameResult r) {
    switch (r) {
      case GameResult.white:
        return 'Trắng thắng';
      case GameResult.black:
        return 'Đen thắng';
      case GameResult.draw:
        return 'Hòa';
      case GameResult.undecided:
        return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    final flipped = !widget.config.humanPlaysWhite;
    return Scaffold(
      backgroundColor: const Color(0xFF302E2B),
      body: ListenableBuilder(
        listenable: controller,
        builder: (context, _) {
          return Stack(
            children: [
              Center(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: AspectRatio(
                    aspectRatio: 1,
                    child: BoardView(
                      board: controller.board,
                      flipped: flipped,
                      selectedFlat: controller.selected?.flat,
                      targetFlats: controller.targets,
                      onTapSquare: controller.onTapSquare,
                      promoSquare: controller.promoSquare,
                      promoOptions: controller.promoOptions,
                      playerIsWhite: widget.config.humanPlaysWhite,
                      onPickPromotion: controller.choosePromotion,
                      onDragStart: controller.beginDrag,
                      onDragEnd: controller.endDrag,
                      onDragCancel: controller.cancelDrag,
                    ),
                  ),
                ),
              ),
              if (controller.engineThinking)
                const Positioned(
                  top: 10,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: Text('Máy đang nghĩ…',
                        style: TextStyle(color: Colors.white70, fontSize: 14)),
                  ),
                ),
              if (controller.gameOver)
                Positioned(
                  top: 10,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: Container(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        _resultText(controller.result),
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                ),
              if (controller.status != null)
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 8,
                  child: Center(
                    child: Text(controller.status!,
                        style: const TextStyle(
                            color: Colors.orangeAccent, fontSize: 12)),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}
