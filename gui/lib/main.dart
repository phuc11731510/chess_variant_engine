import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart' show PointerScrollEvent;
import 'package:flutter/services.dart' show LogicalKeyboardKey;

import 'config/launch_config.dart';
import 'config/replay_library.dart';
import 'config/replay_loader.dart';
import 'data/generation_cache.dart';
import 'domain/game_controller.dart';
import 'engine/engine_service.dart';
import 'engine/uci_process_engine.dart';
import 'engine/native_ffi_engine.dart';
import 'ui/android_home.dart';
import 'ui/board_view.dart';
import 'ui/game_picker.dart';
import 'ui/move_strip.dart';
import 'ui/search_panel.dart';

/// Chọn engine theo nền tảng: desktop spawn tiến trình UCI; Android nạp
/// libfairyzero.so qua dart:ffi ([NativeFfiEngine], M4) — chơi ngay trên máy.
EngineService _makeEngine(LaunchConfig config) {
  if (Platform.isAndroid) {
    // Xem lại ván chỉ cần luật cờ của engine (không mạng, không tìm kiếm).
    final viewOnly = config.replayPath != null || config.replayDir != null;
    return NativeFfiEngine(config, rulesOnly: viewOnly);
  }
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
      // Android: danh sách các đời dữ liệu huấn luyện trên máy, bấm một đời để xem ván (không chơi với máy).
      home: Platform.isAndroid
          ? AndroidHome(
              openViewer: (cacheDir) {
                final preparer = GameFilePreparer(cacheDir);
                return BoardScreen(
                  config: LaunchConfig(enginePath: '', replayDir: cacheDir),
                  prepareGame: (e) => preparer.ensure(e.id),
                );
              },
            )
          : BoardScreen(config: config),
    );
  }
}

class BoardScreen extends StatefulWidget {
  final LaunchConfig config;

  /// Tạo engine (mặc định theo nền tảng, [_makeEngine]); test truyền engine giả.
  final EngineService Function(LaunchConfig)? engineFactory;

  /// Xem lại nhiều ván: gọi trước khi mở nhật ký của một ván (Android: ghi nhật ký của ván đó khi cần).
  final void Function(ReplayEntry e)? prepareGame;

  /// Giao diện cho màn hình cảm ứng: thanh công cụ trên đầu (về, danh sách ván, tự chạy, bảng tìm kiếm), vuốt ngang
  /// trên bàn để lùi / tiến nước, bảng chọn ván và bảng tìm kiếm là ngăn kéo khi không đủ chỗ cạnh bàn.
  /// Null = tự nhận (Android).
  final bool? touchUi;
  const BoardScreen({
    super.key,
    required this.config,
    this.engineFactory,
    this.prepareGame,
    this.touchUi,
  });

  @override
  State<BoardScreen> createState() => _BoardScreenState();
}

class _BoardScreenState extends State<BoardScreen> {
  late final GameController controller;

  /// Tự đấu / xem lại: hiện bảng tìm kiếm bên phải (phím L bật / tắt).
  bool _showSearch = true;

  /// Cột %N thứ hai của bảng tìm kiếm: luỹ thừa 1/T (1 = không hiện; 2 = T 0,5...). Rê chuột vào tiêu đề %N để chọn.
  double _pctExp = 1;

  /// Xem lại nhiều ván (--replay-dir): bảng các ván, ván đang mở, và bảng chọn ván bên trái (phím G bật / tắt).
  ReplayLibrary? _library;
  ReplayEntry? _current;
  bool _showPicker = true;
  final GlobalKey<GamePickerState> _pickerKey = GlobalKey<GamePickerState>();

  /// Chế độ xem lại (một ván: --replay, nhiều ván: --replay-dir).
  bool get _isReplay =>
      widget.config.replayPath != null || widget.config.replayDir != null;

  /// Bảng chọn ván chỉ hiện khi cửa sổ đủ rộng (bàn vuông + bảng này).
  static const _pickerWidth = 330.0;

  /// Bảng tìm kiếm chỉ hiện khi cửa sổ đủ rộng: phần rộng hơn chiều cao (bàn vuông) >= mức này.
  static const _minSearchWidth = 300.0;

  /// Màn hình dọc (cảm ứng): bàn rộng hết bề ngang; phần cao còn lại phía dưới bàn (sau thanh nước đi) từ mức này
  /// trở lên thì đặt bảng tìm kiếm ở đó thay vì ngăn kéo.
  static const _minSearchHeight = 170.0;
  static const _maxSearchWidth = 520.0;

  @override
  void initState() {
    super.initState();
    controller = GameController(
      engine: (widget.engineFactory ?? _makeEngine)(widget.config),
      humanIsWhite: widget.config.humanPlaysWhite,
      selfPlay: widget.config.selfPlay,
      replay: _isReplay,
      maxPlies: widget.config.selfPlay ? LaunchConfig.selfPlayMaxPlies : 0,
    );
    _start();
  }

  Future<void> _start() async {
    final dir = widget.config.replayDir;
    if (dir != null) {
      try {
        final lib = ReplayLibrary.load(dir, prepare: widget.prepareGame);
        setState(() => _library = lib);
        final want = widget.config.replayGame;
        final first = lib.entries.firstWhere(
          (e) => e.id == want,
          orElse: () => lib.entries.first,
        );
        await _openEntry(first);
      } catch (e) {
        controller.status = 'Không đọc được thư mục xem lại $dir: $e';
        controller.notifyListeners();
      }
      return;
    }
    final path = widget.config.replayPath;
    if (path != null) {
      await _openFile(path);
      return;
    }
    await controller.init();
    final demo = widget.config.demoMove;
    if (demo != null) await controller.playHumanUci(demo);
  }

  /// Nạp một nhật ký ván vào bộ điều khiển (xem lại).
  Future<void> _openFile(String path) async {
    try {
      final g = readReplayFile(path);
      await controller.initReplay(
        g.moves,
        startFen: g.startFen,
        replaySearches: g.searches,
      );
    } catch (e) {
      controller.status = 'Không đọc được biên bản $path: $e';
      controller.notifyListeners();
    }
  }

  /// Mở một ván trong bảng chọn.
  Future<void> _openEntry(ReplayEntry e) async {
    setState(() => _current = e);
    try {
      _library!.prepare?.call(e);
    } catch (err) {
      controller.status = 'Không dựng được nhật ký ván #${e.id}: $err';
      controller.notifyListeners();
      return;
    }
    await _openFile(_library!.pathOf(e));
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
    if (_isReplay) {
      final (w, b) = c.shownBoard.pieceCounts();
      final cur = _current;
      final game = cur == null ? '' : ' #${cur.id}';
      final end = c.end;
      final fin = end == null
          ? ''
          : ' · kết cục: ${_resultText(end.result)}, ${end.reasonText}';
      return 'Xem lại ván$game: nửa nước ${c.shownPly}/$ply · quân T$w + Đ$b · '
          '${c.autoPlaying ? "đang tự chạy (Space = dừng)" : "Space = tự chạy"}$fin';
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

  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  final GlobalKey<GamePickerState> _drawerPickerKey =
      GlobalKey<GamePickerState>();
  static const _toolbarHeight = 48.0;
  static const _stripHeight = 34.0; // chiều cao thanh nước đi (MoveStrip)

  /// Vuốt ngang trên bàn: sang trái = tiến một nước, sang phải = lùi một nước (màn hình cảm ứng).
  Widget _swipe(bool on, Widget child) {
    if (!on) return child;
    return GestureDetector(
      onHorizontalDragEnd: (d) {
        final v = d.primaryVelocity ?? 0;
        if (v < -250) {
          controller.stepForward();
        } else if (v > 250) {
          controller.stepBack();
        }
      },
      child: child,
    );
  }

  Widget _searchPanel() {
    final ply = controller.shownPly;
    return SearchPanel(
      exponent: _pctExp,
      onExponentChanged: (e) => setState(() => _pctExp = e),
      record: controller.shownSearch,
      ply: ply,
      played: ply == 0 ? null : controller.moves[ply - 1],
      whiteMoved: ply == 0 || controller.whiteMovedAt(ply - 1),
      compact: widget.touchUi ?? Platform.isAndroid,
    );
  }

  Widget _picker(ReplayLibrary lib, {Key? key, VoidCallback? afterSelect}) =>
      GamePicker(
        key: key,
        library: lib,
        selectedId: _current?.id,
        onSelect: (e) {
          _openEntry(e);
          afterSelect?.call();
        },
      );

  /// Thanh công cụ của màn hình cảm ứng: về danh sách đời, mở danh sách ván / bảng tìm kiếm (khi không đủ chỗ
  /// cạnh bàn), tự chạy.
  Widget _toolbar(ReplayLibrary? lib, bool pickerInline, bool searchInline) {
    final cur = _current;
    final title = cur == null
        ? 'Xem ván'
        : 'Ván #${cur.id} · ${cur.resultText} · ${cur.plies} nửa nước';
    return Container(
      height: _toolbarHeight,
      color: const Color(0xFF262421),
      child: Row(
        children: [
          IconButton(
            tooltip: 'Về danh sách đời dữ liệu',
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.of(context).maybePop(),
          ),
          if (lib != null && !pickerInline)
            TextButton.icon(
              onPressed: () => _scaffoldKey.currentState?.openDrawer(),
              icon: const Icon(Icons.view_list),
              label: const Text('Ván'),
            ),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
          ),
          IconButton(
            tooltip: controller.autoPlaying
                ? 'Dừng tự chạy'
                : 'Tự chạy (1 giây / nước)',
            icon: Icon(controller.autoPlaying ? Icons.pause : Icons.play_arrow),
            onPressed: controller.toggleAutoPlay,
          ),
          if (!searchInline)
            IconButton(
              tooltip: 'Bảng tìm kiếm của nước đang xem',
              icon: const Icon(Icons.analytics_outlined),
              onPressed: () => _scaffoldKey.currentState?.openEndDrawer(),
            ),
        ],
      ),
    );
  }

  void _back10() => controller.goToPly(controller.shownPly - 10);
  void _forward10() => controller.goToPly(controller.shownPly + 10);

  @override
  Widget build(BuildContext context) {
    final flipped = !widget.config.humanPlaysWhite;
    final replay = _isReplay;
    final selfPlay =
        widget.config.selfPlay ||
        replay; // giao diện xem lại nước đi dùng chung
    final touch = widget.touchUi ?? Platform.isAndroid;
    final drawerWidth = (MediaQuery.of(context).size.width * 0.9)
        .clamp(0.0, 380.0)
        .toDouble();
    final lib0 = _library;
    return Scaffold(
      key: _scaffoldKey,
      backgroundColor: const Color(0xFF302E2B),
      drawer: touch && lib0 != null
          ? Drawer(
              width: drawerWidth,
              backgroundColor: const Color(0xFF262421),
              child: SafeArea(
                child: _picker(
                  lib0,
                  key: _drawerPickerKey,
                  afterSelect: () => _scaffoldKey.currentState?.closeDrawer(),
                ),
              ),
            )
          : null,
      endDrawer: touch && selfPlay
          ? Drawer(
              width: drawerWidth,
              backgroundColor: const Color(0xFF262421),
              child: SafeArea(
                child: ListenableBuilder(
                  listenable: controller,
                  builder: (context, _) => _searchPanel(),
                ),
              ),
            )
          : null,
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
            const SingleActivator(LogicalKeyboardKey.keyL): () =>
                setState(() => _showSearch = !_showSearch),
            if (_library != null) ...{
              const SingleActivator(LogicalKeyboardKey.bracketLeft): () =>
                  _pickerKey.currentState?.selectRelative(-1),
              const SingleActivator(LogicalKeyboardKey.bracketRight): () =>
                  _pickerKey.currentState?.selectRelative(1),
              const SingleActivator(LogicalKeyboardKey.keyG): () =>
                  setState(() => _showPicker = !_showPicker),
            },
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
                        child: _swipe(
                          touch && selfPlay,
                          AspectRatio(
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
                              onDragStart: replay ? null : controller.beginDrag,
                              onDragEnd: replay ? null : controller.endDrag,
                              onDragCancel: replay
                                  ? null
                                  : controller.cancelDrag,
                            ),
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
                                : (controller.end != null
                                      ? '${_resultText(controller.result)} · ${controller.end!.reasonText} · '
                                            'còn ${controller.end!.pieces} quân · ${controller.moves.length} nửa nước'
                                      : '${_resultText(controller.result)} · ${controller.moves.length} nửa nước'),
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
              // Xem lại / tự đấu: bàn vuông chiếm hết chiều cao còn lại (trừ thanh nước đi và, trên cảm ứng, thanh công
              // cụ); phần rộng thừa là chỗ cho bảng chọn ván (trái) và bảng tìm kiếm (phải). Không đủ chỗ thì hai bảng
              // thành ngăn kéo (cảm ứng) hoặc ẩn (máy tính, phím G / L bật tắt).
              return LayoutBuilder(
                builder: (context, box) {
                  final lib = _library;
                  final tb = touch ? _toolbarHeight : 0.0;
                  final boardSide = (box.maxHeight - tb - _stripHeight)
                      .clamp(0.0, box.maxWidth)
                      .toDouble();
                  final spare = box.maxWidth - boardSide;
                  final pickerInline =
                      lib != null &&
                      _showPicker &&
                      spare - _minSearchWidth >= _pickerWidth;
                  final searchW = (spare - (pickerInline ? _pickerWidth : 0.0))
                      .clamp(0.0, _maxSearchWidth)
                      .toDouble();
                  final searchBeside =
                      _showSearch && searchW >= _minSearchWidth;
                  // Màn hình dọc: bàn vuông rộng hết bề ngang, bảng tìm kiếm ở khoảng trống phía dưới bàn.
                  final searchBelow =
                      touch &&
                      !searchBeside &&
                      _showSearch &&
                      box.maxHeight - tb - _stripHeight - box.maxWidth >=
                          _minSearchHeight;
                  final searchInline = searchBeside || searchBelow;
                  final boardArea = searchBeside
                      ? Row(
                          children: [
                            Expanded(child: stack),
                            SizedBox(width: searchW, child: _searchPanel()),
                          ],
                        )
                      : stack;
                  final strip = MoveStrip(
                    moves: controller.moves,
                    shownPly: controller.shownPly,
                    live: !controller.inReview,
                    checks: controller.checksGiven,
                    onSelect: controller.goToPly,
                    onFirst: controller.goStart,
                    onPrev: controller.stepBack,
                    onNext: controller.stepForward,
                    onLast: controller.goLive,
                  );
                  final main = searchBelow
                      ? Column(
                          children: [
                            SizedBox(height: box.maxWidth, child: stack),
                            strip,
                            Expanded(child: _searchPanel()),
                          ],
                        )
                      : Column(children: [Expanded(child: boardArea), strip]);
                  final body = pickerInline
                      ? Row(
                          children: [
                            SizedBox(
                              width: _pickerWidth,
                              child: ExcludeFocus(
                                child: _picker(lib, key: _pickerKey),
                              ),
                            ),
                            Expanded(child: main),
                          ],
                        )
                      : main;
                  if (!touch) return body;
                  return SafeArea(
                    child: Column(
                      children: [
                        _toolbar(lib, pickerInline, searchInline),
                        Expanded(child: body),
                      ],
                    ),
                  );
                },
              );
            },
          ),
        ),
      ),
    );
  }
}
