// Unit test M2/M3/M4: parse cờ lệnh, parse FEN, parse UCI, logic GameController.

import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/config/launch_config.dart';
import 'package:fairyzero_gui/domain/board_state.dart';
import 'package:fairyzero_gui/domain/uci_move.dart';
import 'package:fairyzero_gui/domain/game_controller.dart';
import 'package:fairyzero_gui/engine/engine_service.dart';

const _startPlacement =
    'vrhbakberv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRHBAKBERV';

/// Engine giả: bàn cố định, lật lượt khi applyMove; ghi lại các lệnh.
class FakeEngine implements EngineService {
  bool whiteToMove = true;
  final List<String> legalList;
  final String bestReply;
  final GameResult res;
  final List<String> applied = [];
  int bestCalls = 0;

  FakeEngine({
    required this.legalList,
    this.bestReply = '0000',
    this.res = GameResult.undecided,
  });

  String _fen() => '$_startPlacement ${whiteToMove ? "w" : "b"} - - 7+7 0 1';

  @override
  Future<void> start() async {}
  @override
  Future<void> newGame({String? fen}) async {}
  @override
  Future<void> applyMove(String uci) async {
    applied.add(uci);
    whiteToMove = !whiteToMove;
  }

  @override
  Future<List<String>> legalMoves() async => legalList;
  @override
  Future<String> currentFen() async => _fen();
  @override
  Future<GameResult> gameResult() async => res;
  @override
  Future<String> bestMove() async {
    bestCalls++;
    return bestReply;
  }

  @override
  Future<void> dispose() async {}
}

void main() {
  test('LaunchConfig parse co lenh', () {
    final c = LaunchConfig.fromArgs(
      '--engine e.exe --model m.onnx --provider dml --visits 800 --black --demo-move b3b4'
          .split(' '),
    );
    expect(c.enginePath, 'e.exe');
    expect(c.provider, 'dml');
    expect(c.visits, 800);
    expect(c.humanPlaysWhite, false);
    expect(c.demoMove, 'b3b4');

    final d = LaunchConfig.fromArgs(const []);
    expect(d.provider, 'cpu');
    expect(d.movetimeMs, LaunchConfig.defaultMovetimeMs);
    expect(d.humanPlaysWhite, true);

    // Dạng --dart-entrypoint-args "cụm nhiều cờ" (cả cụm là MỘT phần tử).
    final packed = LaunchConfig.fromArgs(const ['--engine e.exe --provider dml']);
    expect(packed.enginePath, 'e.exe');
    expect(packed.provider, 'dml');
  });

  test('BoardState.fromFen startpos dung o + luot + check', () {
    final b = BoardState.fromFen(kVariantStartposFen);
    expect(b.at(0, 5)!.letter, 'K'); // f1 vua Trắng
    expect(b.at(9, 5)!.letter, 'k'); // f10 vua Đen
    expect(b.whiteToMove, true);
    expect(b.checksWhite, 7);
    expect(b.checksBlack, 7);

    int count = 0;
    for (int r = 0; r < 10; r++) {
      for (int f = 0; f < 10; f++) {
        if (b.at(r, f) != null) count++;
      }
    }
    expect(count, 60);
  });

  test('UciMove.tryParse', () {
    final m = UciMove.tryParse('b3b5')!;
    expect(m.from, const Sq(1, 2)); // b3
    expect(m.to, const Sq(1, 4)); // b5
    expect(m.promo, isNull);

    final p = UciMove.tryParse('f2f1h')!;
    expect(p.from, const Sq(5, 1));
    expect(p.to, const Sq(5, 0));
    expect(p.promo, 'h');

    final ten = UciMove.tryParse('e10i6')!;
    expect(ten.from, const Sq(4, 9)); // e10
    expect(ten.to, const Sq(8, 5)); // i6

    expect(UciMove.tryParse('xx'), isNull);
    expect(const Sq(4, 9).name, 'e10');
  });

  test('GameController: chon quan tô đúng ô đích', () async {
    final fake = FakeEngine(legalList: ['b3b4', 'b3b5', 'c3c4']);
    final c = GameController(engine: fake, humanIsWhite: true);
    await c.init();

    // chạm b3 (rank=2, file=1) = tốt Trắng
    c.onTapSquare(2, 1);
    expect(c.selected, const Sq(1, 2));
    expect(c.targets.contains(const Sq(1, 3).flat), true); // b4
    expect(c.targets.contains(const Sq(1, 4).flat), true); // b5
    expect(c.targets.length, 2);

    // chạm ô trống không phải đích -> bỏ chọn
    c.onTapSquare(5, 5);
    expect(c.selected, isNull);
  });

  test('GameController: đi nước người -> máy đáp', () async {
    final fake = FakeEngine(legalList: ['b3b4', 'b3b5'], bestReply: 'i8i7');
    final c = GameController(engine: fake, humanIsWhite: true);
    await c.init();
    expect(fake.bestCalls, 0); // người (Trắng) đi trước

    await c.playHumanUci('b3b4');

    expect(fake.applied, ['b3b4', 'i8i7']); // người rồi máy
    expect(fake.bestCalls, 1);
    expect(c.humansTurn, true); // tới lượt người lại
    expect(c.engineThinking, false);
  });
}
