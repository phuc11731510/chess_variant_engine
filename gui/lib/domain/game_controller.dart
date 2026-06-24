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

  GameController({required this.engine, required this.humanIsWhite});

  BoardState board = BoardState.fromFen(kVariantStartposFen);
  List<String> legal = [];
  GameResult result = GameResult.undecided;

  Sq? selected; // ô nguồn đang chọn
  Set<int> targets = {}; // flat các ô đích hợp lệ của ô đang chọn
  bool engineThinking = false;
  String? status;

  // Phong cấp đang chờ người chọn quân.
  List<UciMove> _promoCands = [];

  bool get gameOver => result != GameResult.undecided;
  bool get humansTurn => board.whiteToMove == humanIsWhite;
  bool get busy => engineThinking;

  /// Ô đích phong cấp (flat) khi đang chờ chọn quân; null nếu không.
  int? get promoSquare => _promoCands.isEmpty ? null : _promoCands.first.to.flat;

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
      final cand =
          _legalParsed().where((x) => x.from == m.from && x.to == m.to).toList();
      if (cand.isEmpty) return;
      u = cand.first.uci;
    }
    selected = null;
    targets = {};
    await _playHuman(u);
  }

  // --- nội bộ ---

  static const _promoOrder = ['h', 'v', 'm', 'y', 'n', 'b'];

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
    await _refresh();
    await _maybeEngineMove();
  }

  Future<void> _maybeEngineMove() async {
    if (gameOver || humansTurn) return;
    engineThinking = true;
    notifyListeners();
    try {
      final mv = await engine.bestMove();
      if (mv != '0000') await engine.applyMove(mv);
    } finally {
      engineThinking = false;
    }
    await _refresh();
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
  void dispose() {
    engine.dispose();
    super.dispose();
  }
}
