import 'dart:async';

import 'package:flutter/foundation.dart';

import '../engine/engine_service.dart';
import 'board_state.dart';
import 'search_record.dart';
import 'uci_move.dart';

/// Máy trạng thái một ván: điều phối lượt NGƯỜI ↔ MÁY qua [EngineService].
///
/// M4: nhập nước kiểu chạm-chạm. M6 (đưa lên sớm): bảng chọn phong cấp.
class GameController extends ChangeNotifier {
  final EngineService engine;
  final bool humanIsWhite;

  /// Máy tự đấu cả hai bên (--self-play): người chỉ xem, có thể tạm dừng.
  final bool selfPlay;

  /// Chỉ xem lại một ván đã có ([initReplay]): không chơi, không tìm kiếm; engine chỉ để áp
  /// từng nước và cho thế cờ sau nước đó.
  final bool replay;

  GameController({
    required this.engine,
    required this.humanIsWhite,
    this.selfPlay = false,
    this.replay = false,
    this.maxPlies = 0,
  });

  /// Nước vừa đi (để tô ô đi/đến) và toàn bộ nước đã đi (UCI thật).
  UciMove? lastMove;
  final List<String> moves = [];

  /// FEN sau mỗi nửa nước: fens[0] = thế xuất phát, fens[k] = thế sau nước thứ k
  /// (độ dài = moves.length + 1). Để XEM LẠI các nước trước trong khi ván vẫn tiếp tục.
  final List<String> fens = [];

  /// Nửa nước đang xem lại (0 = thế xuất phát); null = xem trực tiếp (thế mới nhất).
  /// Xem lại chỉ đổi cái HIỆN trên bàn: engine và ván vẫn đi tiếp.
  int? viewPly;
  BoardState? _viewBoard;
  int _viewBoardPly = -1;

  /// Tự đấu: đang tạm dừng (nước đang nghĩ vẫn đi nốt, sau đó dừng).
  bool paused = false;
  bool _disposed = false;

  Set<int> get lastMoveFlats =>
      lastMove == null ? const {} : {lastMove!.from.flat, lastMove!.to.flat};

  /// Đang xem lại một thế cũ (không phải thế mới nhất).
  bool get inReview => viewPly != null;

  /// Nửa nước đang hiện trên bàn (0 = thế xuất phát).
  int get shownPly => viewPly ?? moves.length;

  /// Bàn đang hiện: thế mới nhất, hoặc thế đang xem lại.
  BoardState get shownBoard {
    final v = viewPly;
    if (v == null || v >= fens.length) return board;
    if (_viewBoardPly != v) {
      _viewBoard = BoardState.fromFen(fens[v]);
      _viewBoardPly = v;
    }
    return _viewBoard!;
  }

  /// Tự đấu / xem lại: lần tìm kiếm đã chọn từng nước (khoá = chỉ số nước, 0 = nước đầu).
  /// Tự đấu ghi khi engine đi; xem lại nạp từ nhật ký ([SearchRecord.parseLog]).
  final Map<int, SearchRecord> searches = {};

  /// Lần tìm đã chọn nước dẫn tới thế đang hiện (null ở thế xuất phát / không có nhật ký).
  SearchRecord? get shownSearch => shownPly == 0 ? null : searches[shownPly - 1];

  /// Trắng là bên đi nước thứ [index] (0 = nước đầu): đọc bên đi trong FEN trước nước đó.
  bool whiteMovedAt(int index) {
    if (index >= 0 && index < fens.length) {
      final parts = fens[index].split(' ');
      if (parts.length > 1) return parts[1] == 'w';
    }
    return index.isEven;
  }

  /// Ô đi/đến của nước dẫn tới thế đang hiện (để tô).
  Set<int> get shownLastMoveFlats {
    final v = viewPly;
    if (v == null) return lastMoveFlats;
    if (v == 0 || v > moves.length) return const {};
    final m = UciMove.tryParse(moves[v - 1]);
    return m == null ? const {} : {m.from.flat, m.to.flat};
  }

  /// Xem thế sau [ply] nửa nước (0 = xuất phát). Tới nước mới nhất thì quay về xem trực tiếp.
  void goToPly(int ply) {
    final n = moves.length;
    final p = ply < 0 ? 0 : (ply > n ? n : ply);
    viewPly = p >= n ? null : p;
    notifyListeners();
  }

  void stepBack() => goToPly(shownPly - 1);
  void stepForward() => goToPly(shownPly + 1);
  void goStart() => goToPly(0);
  void goLive() => goToPly(moves.length);

  BoardState board = BoardState.fromFen(kVariantStartposFen);
  List<String> legal = [];
  GameResult result = GameResult.undecided;

  Sq? selected; // ô nguồn đang chọn
  Set<int> targets = {}; // flat các ô đích hợp lệ của ô đang chọn
  bool engineThinking = false;
  String? status;

  // Phong cấp đang chờ người chọn quân.
  List<UciMove> _promoCands = [];

  /// Tự đấu: số nửa nước tối đa, tới đó tính hoà như self-play (--max-moves).
  /// 0 = không giới hạn.
  final int maxPlies;

  /// Ván bị cắt vì đủ [maxPlies] (kết quả hiển thị là hoà).
  bool plyCutoff = false;

  bool get gameOver => result != GameResult.undecided || plyCutoff;
  bool get humansTurn =>
      !selfPlay && !replay && board.whiteToMove == humanIsWhite;
  bool get busy => engineThinking;

  /// Ô đích phong cấp (flat) khi đang chờ chọn quân; null nếu không.
  int? get promoSquare =>
      _promoCands.isEmpty ? null : _promoCands.first.to.flat;

  /// Các ký tự quân được phép phong (theo thứ tự hiển thị).
  List<String> get promoOptions =>
      _orderPromos(_promoCands.map((m) => m.promo ?? '').toList());

  Future<void> init() async {
    try {
      await engine.start();
      await engine.newGame();
      await _refresh();
      await _maybeEngineMove(); // người cầm Đen thì máy (Trắng) đi trước
    } catch (e) {
      status = 'Loi engine: $e';
      board = BoardState.fromFen(kVariantStartposFen);
      notifyListeners();
    }
  }

  // --- xử lý chạm ---

  void onTapSquare(int r, int f) {
    if (busy || gameOver || !humansTurn || inReview || _promoCands.isNotEmpty) {
      return;
    }
    final tapped = Sq(f, r);
    final piece = board.at(r, f);

    if (selected == null) {
      _trySelect(tapped, piece);
      return;
    }

    if (targets.contains(tapped.flat)) {
      final candidates = _legalParsed()
          .where((m) => m.from == selected && m.to == tapped)
          .toList();
      if (candidates.length > 1) {
        // Phong cấp: hiện bảng chọn, CHƯA đi.
        _promoCands = candidates;
        selected = null;
        targets = {};
        notifyListeners();
        return;
      }
      if (candidates.length == 1) {
        final uci = candidates.first.uci;
        selected = null;
        targets = {};
        _playHuman(uci);
        return;
      }
    }

    if (piece != null && piece.isWhite == humanIsWhite) {
      _trySelect(tapped, piece);
    } else {
      selected = null;
      targets = {};
      notifyListeners();
    }
  }

  // --- kéo-thả (dùng chung logic chọn/đi với chạm-chạm) ---

  /// Nhấc quân ở (r,f) để kéo. true nếu được phép (quân mình + có nước hợp lệ).
  bool beginDrag(int r, int f) {
    if (busy || gameOver || !humansTurn || inReview || _promoCands.isNotEmpty) {
      return false;
    }
    _trySelect(Sq(f, r), board.at(r, f));
    return selected == Sq(f, r);
  }

  /// Thả quân vào (r,f): hợp lệ thì đi (hoặc hiện bảng phong cấp), sai thì bỏ chọn.
  void endDrag(int r, int f) {
    if (selected == null) return;
    final tapped = Sq(f, r);
    if (targets.contains(tapped.flat)) {
      final candidates = _legalParsed()
          .where((m) => m.from == selected && m.to == tapped)
          .toList();
      if (candidates.length > 1) {
        _promoCands = candidates;
        selected = null;
        targets = {};
        notifyListeners();
        return;
      }
      if (candidates.length == 1) {
        final uci = candidates.first.uci;
        selected = null;
        targets = {};
        _playHuman(uci);
        return;
      }
    }
    selected = null;
    targets = {};
    notifyListeners();
  }

  void cancelDrag() {
    selected = null;
    targets = {};
    notifyListeners();
  }

  /// Người chọn quân phong cấp (letter rỗng = huỷ phong cấp).
  void choosePromotion(String letter) {
    if (_promoCands.isEmpty) return;
    if (letter.isEmpty) {
      _promoCands = [];
      notifyListeners();
      return;
    }
    final match = _promoCands.where((m) => m.promo == letter).toList();
    _promoCands = [];
    notifyListeners();
    if (match.isNotEmpty) _playHuman(match.first.uci);
  }

  /// Chơi một nước người theo UCI (tap đã build sẵn / --demo-move).
  Future<void> playHumanUci(String uci) async {
    if (busy || gameOver || !humansTurn) return;
    var u = uci;
    if (!legal.contains(u)) {
      final m = UciMove.tryParse(u);
      if (m == null) return;
      final cand = _legalParsed()
          .where((x) => x.from == m.from && x.to == m.to)
          .toList();
      if (cand.isEmpty) return;
      u = cand.first.uci;
    }
    selected = null;
    targets = {};
    await _playHuman(u);
  }

  // --- nội bộ ---

  // Đổi luật: bỏ Archbishop 'h', thêm Rook 'r'. Thứ tự hiển thị bảng chọn phong cấp.
  static const _promoOrder = ['r', 'v', 'm', 'y', 'n', 'b'];

  List<String> _orderPromos(List<String> letters) {
    final ls = letters.where((s) => s.isNotEmpty).toSet().toList();
    ls.sort((a, b) {
      int ia = _promoOrder.indexOf(a), ib = _promoOrder.indexOf(b);
      if (ia < 0) ia = 99;
      if (ib < 0) ib = 99;
      return ia.compareTo(ib);
    });
    return ls;
  }

  List<UciMove> _legalParsed() =>
      legal.map(UciMove.tryParse).whereType<UciMove>().toList();

  void _trySelect(Sq sq, Piece? piece) {
    if (piece == null || piece.isWhite != humanIsWhite) {
      selected = null;
      targets = {};
      notifyListeners();
      return;
    }
    final t = <int>{};
    for (final m in _legalParsed()) {
      if (m.from == sq) t.add(m.to.flat);
    }
    if (t.isEmpty) {
      selected = null;
      targets = {};
    } else {
      selected = sq;
      targets = t;
    }
    notifyListeners();
  }

  Future<void> _playHuman(String uci) async {
    await engine.applyMove(uci);
    _recordMove(uci);
    await _refresh();
    await _maybeEngineMove();
  }

  void _recordMove(String uci) {
    moves.add(uci);
    lastMove = UciMove.tryParse(uci);
  }

  /// Máy đi khi tới lượt máy. Ở chế độ tự đấu: đi liên tục cả hai bên tới khi
  /// hết ván, bị tạm dừng hoặc cửa sổ đóng.
  Future<void> _maybeEngineMove() async {
    while (!_disposed && !gameOver && !humansTurn && !(selfPlay && paused)) {
      engineThinking = true;
      notifyListeners();
      String mv;
      try {
        mv = await engine.bestMove();
        if (_disposed) return;
        final Object e = engine; // SearchLogSource không phải kiểu con của EngineService
        if (e is SearchLogSource) {
          final s = e.lastSearch;
          if (s != null) searches[moves.length] = s;
        }
        if (mv != '0000') {
          await engine.applyMove(mv);
          _recordMove(mv);
          if (selfPlay && maxPlies > 0 && moves.length >= maxPlies) {
            plyCutoff = true;
          }
        }
      } catch (e) {
        if (_disposed) return;
        status = 'Loi engine: $e';
        engineThinking = false;
        notifyListeners();
        return;
      } finally {
        engineThinking = false;
      }
      try {
        await _refresh();
      } catch (e) {
        if (_disposed) return; // cửa sổ đóng giữa chừng: engine đã tắt
        rethrow;
      }
      if (mv == '0000') return; // engine không có nước (không nên xảy ra)
      if (!selfPlay) return; // chơi với người: máy đi đúng một nước
    }
  }

  /// Xem lại: đang tự chạy tiến từng nước (mỗi [autoStep]).
  Timer? _autoTimer;
  static const autoStep = Duration(milliseconds: 1000);
  bool get autoPlaying => _autoTimer != null;

  /// Xem lại: nạp [replayMoves] (từ thế [startFen], null = thế đầu của biến thể) và dừng ở thế xuất phát.
  /// Mỗi nước được kiểm là hợp lệ; gặp nước sai thì dừng ở đó và báo ở [status].
  Future<void> initReplay(List<String> replayMoves, {String? startFen}) async {
    try {
      await engine.start();
      await engine.newGame(fen: startFen);
      fens.add(await engine.currentFen());
      for (final m in replayMoves) {
        final lg = await engine.legalMoves();
        if (_disposed) return;
        if (!lg.contains(m)) {
          status =
              'Nước thứ ${moves.length + 1} ($m) không hợp lệ trong thế này — chỉ xem được ${moves.length} nước đầu';
          break;
        }
        await engine.applyMove(m);
        _recordMove(m);
        fens.add(await engine.currentFen());
      }
      board = BoardState.fromFen(fens.last);
      legal = [];
      result = await engine.gameResult();
      goToPly(0);
    } catch (e) {
      if (_disposed) return;
      status = 'Loi engine: $e';
      notifyListeners();
    }
  }

  /// Xem lại: bật/tắt tự chạy. Đang ở nước cuối thì chạy lại từ đầu.
  void toggleAutoPlay() {
    if (_autoTimer != null) {
      _stopAuto();
      notifyListeners();
      return;
    }
    if (shownPly >= moves.length) goToPly(0);
    _autoTimer = Timer.periodic(autoStep, (_) {
      stepForward();
      if (shownPly >= moves.length) {
        _stopAuto();
        notifyListeners();
      }
    });
    notifyListeners();
  }

  void _stopAuto() {
    _autoTimer?.cancel();
    _autoTimer = null;
  }

  /// Tự đấu: bật/tắt tạm dừng. Tiếp tục thì máy đi tiếp ngay.
  void togglePause() {
    if (replay) {
      toggleAutoPlay();
      return;
    }
    if (!selfPlay || gameOver) return;
    paused = !paused;
    notifyListeners();
    if (!paused && !engineThinking) _maybeEngineMove();
  }

  Future<void> _refresh() async {
    final fen = await engine.currentFen();
    if (fens.length == moves.length) {
      fens.add(fen); // thế vừa tới (hoặc thế xuất phát)
    }
    board = BoardState.fromFen(fen);
    legal = await engine.legalMoves();
    result = await engine.gameResult();
    selected = null;
    targets = {};
    notifyListeners();
  }

  @override
  void notifyListeners() {
    if (!_disposed) super.notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _stopAuto();
    engine.dispose();
    super.dispose();
  }
}
