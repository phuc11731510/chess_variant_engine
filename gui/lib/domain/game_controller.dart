import 'package:flutter/foundation.dart';

import '../engine/engine_service.dart';
import 'board_state.dart';
import 'uci_move.dart';

/// Máy trạng thái một ván: điều phối lượt NGƯỜI ↔ MÁY qua [EngineService].
///
/// M4: nhập nước kiểu chạm-chạm. M6 (đưa lên sớm): bảng chọn phong cấp.
class GameController extends ChangeNotifier {
  final EngineService engine;
  final bool humanIsWhite;

  /// Máy tự đấu cả hai bên (--self-play): người chỉ xem, có thể tạm dừng.
  final bool selfPlay;

  GameController({
    required this.engine,
    required this.humanIsWhite,
    this.selfPlay = false,
    this.maxPlies = 0,
  });

  /// Nước vừa đi (để tô ô đi/đến) và toàn bộ nước đã đi (UCI thật).
  UciMove? lastMove;
  final List<String> moves = [];

  /// Tự đấu: đang tạm dừng (nước đang nghĩ vẫn đi nốt, sau đó dừng).
  bool paused = false;
  bool _disposed = false;

  Set<int> get lastMoveFlats =>
      lastMove == null ? const {} : {lastMove!.from.flat, lastMove!.to.flat};

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
  bool get humansTurn => !selfPlay && board.whiteToMove == humanIsWhite;
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
    if (busy || gameOver || !humansTurn || _promoCands.isNotEmpty) return;
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
    if (busy || gameOver || !humansTurn || _promoCands.isNotEmpty) return false;
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

  /// Tự đấu: bật/tắt tạm dừng. Tiếp tục thì máy đi tiếp ngay.
  void togglePause() {
    if (!selfPlay || gameOver) return;
    paused = !paused;
    notifyListeners();
    if (!paused && !engineThinking) _maybeEngineMove();
  }

  Future<void> _refresh() async {
    final fen = await engine.currentFen();
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
    engine.dispose();
    super.dispose();
  }
}
