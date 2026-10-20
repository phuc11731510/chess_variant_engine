import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart' show PointerScrollEvent;
import 'package:flutter/services.dart' show LogicalKeyboardKey;

import 'config/launch_config.dart';
import 'config/replay_loader.dart';
import 'domain/game_controller.dart';
import 'engine/engine_service.dart';
import 'engine/uci_process_engine.dart';
import 'engine/native_ffi_engine.dart';
import 'ui/board_view.dart';
import 'ui/move_strip.dart';

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

  /// Tạo engine (mặc định theo nền tảng, [_makeEngine]); test truyền engine giả.
  final EngineService Function(LaunchConfig)? engineFactory;
  const BoardScreen({super.key, required this.config, this.engineFactory});

  @override
  State<BoardScreen> createState() => _BoardScreenState();
}

class _BoardScreenState extends State<BoardScreen> {
  late final GameController controller;

  @override
  void initState() {
    super.initState();
    controller = GameController(
      engine: (widget.engineFactory ?? _makeEngine)(widget.config),
      humanIsWhite: widget.config.humanPlaysWhite,
      selfPlay: widget.config.selfPlay,
      replay: widget.config.replayPath != null,
      maxPlies: widget.config.selfPlay ? LaunchConfig.selfPlayMaxPlies : 0,
    );
    _start();
  }

  Future<void> _start() async {
    final path = widget.config.replayPath;
    if (path != null) {
      try {
        final g = readReplayFile(path);
        await controller.initReplay(g.moves, startFen: g.startFen);
      } catch (e) {
        controller.status = 'Không đọc được biên bản $path: $e';
        controller.notifyListeners();
      }
      return;
    }
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

  /// Tự đấu: dòng trạng thái trên cùng (số nước, bên đang nghĩ, tạm dừng).
  String _selfPlayLine() {
    final c = controller;
    final ply = c.moves.length;
    final moveNo = ply ~/ 2 + 1;
    if (widget.config.replayPath != null) {
      return 'Xem lại ván: nửa nước ${c.shownPly}/$ply · '
          '${c.autoPlaying ? "đang tự chạy (Space = dừng)" : "Space = tự chạy"} '
          '· ← → / lăn chuột / bấm nước';
    }
    final side = c.board.whiteToMove ? 'Trắng' : 'Đen';
    if (c.gameOver) return 'Hết ván sau $ply nửa nước';
    if (c.inReview) {
      return 'Đang xem lại: sau nửa nước ${c.shownPly}/$ply · ván vẫn tiếp tục '
          '(End = về nước mới nhất, Space = tạm dừng)';
    }
    if (c.paused && !c.engineThinking) {
      return 'Nước $moveNo · $side · tạm dừng (Space để tiếp)';
    }
    if (c.paused) {
      return 'Nước $moveNo · $side đang nghĩ… (sẽ dừng sau nước này)';
    }
    return 'Nước $moveNo · $side đang nghĩ… (${widget.config.thinkSummary})';
  }

  void _back10() => controller.goToPly(controller.shownPly - 10);
  void _forward10() => controller.goToPly(controller.shownPly + 10);

  @override
  Widget build(BuildContext context) {
    final flipped = !widget.config.humanPlaysWhite;
    final replay = widget.config.replayPath != null;
    final selfPlay = widget.config.selfPlay || replay; // giao diện xem lại nước đi dùng chung
    return Scaffold(
      backgroundColor: const Color(0xFF302E2B),
      body: CallbackShortcuts(
        bindings: <ShortcutActivator, VoidCallback>{
          const SingleActivator(LogicalKeyboardKey.space):
              controller.togglePause,
          // Tự đấu: xem lại các nước đã đi trong khi ván vẫn tiếp tục.
          if (selfPlay) ...{
            const SingleActivator(LogicalKeyboardKey.arrowLeft):
                controller.stepBack,
            const SingleActivator(LogicalKeyboardKey.arrowRight):
                controller.stepForward,
            const SingleActivator(LogicalKeyboardKey.arrowUp):
                controller.stepBack,
            const SingleActivator(LogicalKeyboardKey.arrowDown):
                controller.stepForward,
            const SingleActivator(LogicalKeyboardKey.home): controller.goStart,
            const SingleActivator(LogicalKeyboardKey.end): controller.goLive,
            const SingleActivator(LogicalKeyboardKey.pageUp): _back10,
            const SingleActivator(LogicalKeyboardKey.pageDown): _forward10,
          },
        },
        child: Focus(
          autofocus: true,
          child: ListenableBuilder(
            listenable: controller,
            builder: (context, _) {
              final stack = Stack(
                children: [
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      // Tự đấu: lăn chuột trên bàn = lùi / tiến từng nước.
                      child: Listener(
                        onPointerSignal: selfPlay
                            ? (e) {
                                if (e is PointerScrollEvent &&
                                    e.scrollDelta.dy != 0) {
                                  e.scrollDelta.dy > 0
                                      ? controller.stepForward()
                                      : controller.stepBack();
                                }
                              }
                            : null,
                        child: AspectRatio(
                          aspectRatio: 1,
                          child: BoardView(
                            board: controller.shownBoard,
                            flipped: flipped,
                            selectedFlat: controller.selected?.flat,
                            targetFlats: controller.targets,
                            lastMoveFlats: controller.shownLastMoveFlats,
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
                  ),
                  if (controller.engineThinking && !selfPlay)
                    const Positioned(
                      top: 10,
                      left: 0,
                      right: 0,
                      child: Center(
                        child: Text(
                          'Máy đang nghĩ…',
                          style: TextStyle(color: Colors.white70, fontSize: 14),
                        ),
                      ),
                    ),
                  if (selfPlay &&
                      (replay
                          ? !(controller.gameOver && !controller.inReview)
                          : !controller.gameOver))
                    Positioned(
                      top: 0,
                      left: 0,
                      right: 0,
                      child: Center(
                        child: Text(
                          _selfPlayLine(),
                          style: const TextStyle(
                            color: Colors.white70,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ),
                  if (controller.gameOver && !(replay && controller.inReview))
                    Positioned(
                      top: 10,
                      left: 0,
                      right: 0,
                      child: Center(
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.black54,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            controller.plyCutoff
                                ? 'Hòa (đủ ${LaunchConfig.selfPlayMaxPlies} nửa nước, như self-play)'
                                : '${_resultText(controller.result)} · ${controller.moves.length} nửa nước',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
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
                        child: Text(
                          controller.status!,
                          style: const TextStyle(
                            color: Colors.orangeAccent,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ),
                ],
              );
              if (!selfPlay) return stack;
              // Tự đấu: bàn ở trên, thanh nước đi (bấm / mũi tên / lăn chuột để xem lại) ở dưới.
              return Column(
                children: [
                  Expanded(child: stack),
                  MoveStrip(
                    moves: controller.moves,
                    shownPly: controller.shownPly,
                    live: !controller.inReview,
                    onSelect: controller.goToPly,
                    onFirst: controller.goStart,
                    onPrev: controller.stepBack,
                    onNext: controller.stepForward,
                    onLast: controller.goLive,
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
