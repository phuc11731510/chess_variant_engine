import 'package:flutter/foundation.dart';

import '../engine/engine_service.dart';
import 'board_state.dart';
import 'uci_move.dart';

/// Máy trạng thái một ván: điều phối lượt NGƯỜI ↔ MÁY qua [EngineService].
///
/// M4: nhập nước kiểu chạm-chạm. Người chạm quân mình → chọn + tô ô đích hợp lệ;
/// chạm ô đích → đi nước → máy đáp. (Kéo-thả là M5, bảng phong cấp là M6.)
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
  String? status; // thông báo lỗi/ghi chú

  bool get gameOver => result != GameResult.undecided;
  bool get humansTurn => board.whiteToMove == humanIsWhite;
  bool get busy => engineThinking;

  Future<void> init() async {
    try {
      await engine.start();
      await engine.newGame();
      await _refresh();
      await _maybeEngineMove(); // nếu người cầm Đen thì máy (Trắng) đi trước
    } catch (e) {
      status = 'Loi engine: $e';
      board = BoardState.fromFen(kVariantStartposFen);
      notifyListeners();
    }
  }

  // --- xử lý chạm ---

  void onTapSquare(int r, int f) {
    if (busy || gameOver || !humansTurn) return;
    final tapped = Sq(f, r);
    final piece = board.at(r, f);

    if (selected == null) {
      _trySelect(tapped, piece);
      return;
    }

    // Đã có ô chọn: nếu chạm ô đích hợp lệ -> đi.
    if (targets.contains(tapped.flat)) {
      final candidates = _legalParsed()
          .where((m) => m.from == selected && m.to == tapped)
          .toList();
      if (candidates.isNotEmpty) {
        // M4: nếu nhiều biến thể (phong cấp) tạm lấy cái đầu (M6 thêm bảng chọn).
        final uci = candidates.first.uci;
        selected = null;
        targets = {};
        _playHuman(uci);
        return;
      }
    }

    // Chạm quân mình khác -> đổi chọn; nếu không -> bỏ chọn.
    if (piece != null && piece.isWhite == humanIsWhite) {
      _trySelect(tapped, piece);
    } else {
      selected = null;
      targets = {};
      notifyListeners();
    }
  }

  /// Chơi một nước của NGƯỜI theo UCI (dùng cho tap đã build sẵn, hoặc --demo-move).
  Future<void> playHumanUci(String uci) async {
    if (busy || gameOver || !humansTurn) return;
    var u = uci;
    if (!legal.contains(u)) {
      // Khớp theo from-to (vd thiếu hậu tố phong) -> lấy biến thể đầu.
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
