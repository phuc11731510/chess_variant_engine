// Xem lại nhiều ván: bảng chỉ mục (chi_muc.tsv), bảng chọn ván, lý do kết thúc, nạp ván khác, đối số mới.

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fairyzero_gui/config/launch_config.dart';
import 'package:fairyzero_gui/config/replay_library.dart';
import 'package:fairyzero_gui/domain/board_state.dart';
import 'package:fairyzero_gui/domain/game_controller.dart';
import 'package:fairyzero_gui/domain/game_end.dart';
import 'package:fairyzero_gui/domain/search_record.dart';
import 'package:fairyzero_gui/engine/engine_service.dart';
import 'package:fairyzero_gui/engine/uci_process_engine.dart';
import 'package:fairyzero_gui/ui/game_picker.dart';

const _tsv = 'so\ttep\tnua_nuoc\tket_qua\tquan_trang\tquan_den\tly_do\tghi_chu\n'
    '0\tvan_0000.txt\t3\tW\t30\t30\tno_moves\t\n'
    '1\tvan_0001.txt\t120\tB\t12\t15\tchecks\t\n'
    '2\tvan_0002.txt\t9\tB\t30\t30\tno_moves\t\n'
    '3\tvan_0003.txt\t400\tD\t20\t21\tcut\t\n'
    '4\tvan_0004.txt\t57\tW\t29\t30\tchecks\tban co cuoi lech engine\n';

/// Engine giả theo kịch bản: thế sau k nước = fens[k]; nước hợp lệ ở thế k là đúng nước thứ k của [script].
class ScriptedEngine implements EngineService {
  final List<String> fens;
  final List<String> script;
  final GameResult res;
  final int legalAtEnd;
  int applied = 0;
  ScriptedEngine(this.fens, this.script, {this.res = GameResult.white, this.legalAtEnd = 0});

  @override
  Future<void> start() async {}
  @override
  Future<void> newGame({String? fen}) async => applied = 0;
  @override
  Future<void> applyMove(String uci) async => applied++;
  @override
  Future<List<String>> legalMoves() async =>
      applied < script.length ? [script[applied]] : List.filled(legalAtEnd, 'a1a2');
  @override
  Future<String> currentFen() async => fens[applied];
  @override
  Future<GameResult> gameResult() async => applied >= fens.length - 1 ? res : GameResult.undecided;
  @override
  Future<String> bestMove() async => throw StateError('xem lại không tìm nước');
  @override
  Future<void> dispose() async {}
}

const _p = 'k9/10/10/10/10/10/10/10/10/K9';

void main() {
  test('ReplayLibrary.load đọc chi_muc.tsv', () {
    final dir = Directory.systemTemp.createTempSync('fz_lib_');
    File('${dir.path}${Platform.pathSeparator}chi_muc.tsv').writeAsStringSync(_tsv);
    final lib = ReplayLibrary.load(dir.path);
    expect(lib.entries.length, 5);
    expect(lib.entries[1].id, 1);
    expect(lib.entries[1].plies, 120);
    expect(lib.entries[1].resultText, 'Đen thắng');
    expect(lib.entries[1].pieces, 27);
    expect(lib.entries[1].reasonText, 'đủ 7 lần chiếu');
    expect(lib.entries[4].note, isNotEmpty);
    expect(lib.maxPieces, 60);
    expect(lib.pathOf(lib.entries[0]).endsWith('van_0000.txt'), true);
    expect(() => ReplayLibrary.load('${dir.path}${Platform.pathSeparator}khong_co'), throwsA(isA<FileSystemException>()));
    dir.deleteSync(recursive: true);
  });

  test('GameEnd.of: lý do kết thúc theo FEN cuối', () {
    GameEnd e(String fen, GameResult r, int legal) => GameEnd.of(fen, r, legal);
    // Trắng đã chiếu đủ 7 lần (còn 0 lần cho Trắng).
    var g = e('$_p b - - 0+3 5 40', GameResult.white, 12);
    expect(g.reason, EndReason.checks);
    expect(g.reasonText, 'Trắng đủ 7 lần chiếu');
    // Hết nước đi: Đen tới lượt, không còn nước, Trắng thắng.
    g = e('$_p b - - 3+3 5 40', GameResult.white, 0);
    expect(g.reason, EndReason.noMoves);
    expect(g.reasonText, 'Đen hết nước đi (thua)');
    // Luật 50 nước: hoà; ở ply 100 mà hết nước thì là thua (chiếu hết).
    expect(e('$_p w - - 3+3 100 80', GameResult.draw, 5).reason, EndReason.rule50);
    expect(e('$_p w - - 3+3 100 80', GameResult.black, 0).reason, EndReason.noMoves);
    expect(e('$_p w - - 3+3 12 80', GameResult.draw, 5).reason, EndReason.repetition);
    expect(e('$_p w - - 3+3 12 80', GameResult.undecided, 5).reason, EndReason.unfinished);
    // Quân còn lại.
    final h = GameEnd.of('Pp8/10/10/10/10/10/10/10/10/K1k7 w - - 3+3 1 2', GameResult.white, 0);
    expect(h.whitePieces, 2);
    expect(h.blackPieces, 2);
    expect(h.pieces, 4);
  });

  test('GameController.initReplay: nạp ván khác thay hẳn ván cũ; lý do, quân còn lại, số lần chiếu', () async {
    // Ván 1 (3 nước): Trắng chiếu ở nước đầu (6+7) rồi nước thứ ba chiếu nữa (5+7); Đen thua vì hết nước.
    final eng1 = ScriptedEngine([
      '$_p w - - 7+7 0 1',
      '$_p b - - 6+7 0 1',
      '$_p w - - 6+7 1 2',
      '$_p b - - 5+7 2 2',
    ], ['a1a2', 'a10a9', 'a2a3'], legalAtEnd: 0);
    final c = GameController(engine: eng1, humanIsWhite: true, replay: true);
    await c.initReplay(['a1a2', 'a10a9', 'a2a3']);
    expect(c.moves.length, 3);
    expect(c.end?.reason, EndReason.noMoves);
    expect(c.end?.reasonText, 'Đen hết nước đi (thua)');
    expect(c.end?.pieces, 2);
    expect(c.checksGiven, [1, 0, 1]);
    expect(c.checksGivenAt(0), 1);
    expect(c.checksGivenAt(7), 0);

    // Nạp lại cùng bộ điều khiển với một ván khác (engine khác kịch bản): trạng thái cũ bị xoá hẳn.
    final eng2 = ScriptedEngine(['$_p w - - 7+7 0 1', '$_p b - - 7+7 1 1'], ['a1a2'], res: GameResult.draw, legalAtEnd: 4);
    final c2 = GameController(engine: eng2, humanIsWhite: true, replay: true);
    await c2.initReplay(['a1a2']);
    expect(c2.moves, ['a1a2']);
    expect(c2.end?.reason, EndReason.repetition);
    await c2.initReplay(['a1a2', 'a10a9']); // lần 2 dài hơn kịch bản: nước thứ 2 không hợp lệ -> dừng ở nước 1, báo lỗi
    expect(c2.moves, ['a1a2']);
    expect(c2.fens.length, 2);
    expect(c2.shownPly, 0);
    expect(c2.status, contains('không hợp lệ'));
  });

  test('GameController.initReplay: gọi chồng nhau thì chỉ lần sau cùng có hiệu lực', () async {
    final eng = ScriptedEngine(['$_p w - - 7+7 0 1', '$_p b - - 7+7 1 1', '$_p w - - 7+7 2 2'], ['a1a2', 'a10a9'], legalAtEnd: 0);
    final c = GameController(engine: eng, humanIsWhite: true, replay: true);
    final f1 = c.initReplay(['a1a2', 'a10a9']);
    final f2 = c.initReplay(['a1a2']); // không đợi f1
    await Future.wait([f1, f2]);
    expect(c.moves.length, 1, reason: 'ván nạp sau cùng (1 nước) thắng ván nạp trước (2 nước)');
    expect(c.fens.length, 2);
  });

  test('SearchRecord.parseLog: dòng chỉ có N (nhật ký dựng từ dữ liệu huấn luyện), P và Q có thể vắng', () {
    const log = '''
# dữ liệu huấn luyện · van.xz
--- nửa nước 1 (trắng đi) → e2e4
position fen $_p w - - 7+7 0 1
  depth 1 seldepth 1 multipv 1 wdl 300 400 300 nodes 801 nps 0 time 0 pv e2e4
    e2e4 N 500 Q 0.0123
    d2d4 N 200
    c2c4 N 100 P 0.25 Q -0.1000
    b2b4 N 30 P 0.1 Q 0.2 Pnet 0.05
''';
    final r = SearchRecord.parseLog(log)[0]!;
    final c = r.candidates;
    expect(c.length, 4);
    expect(c[0].move, 'e2e4');
    expect(c[0].n, 500);
    expect(c[0].p, isNull);
    expect(c[0].q, closeTo(0.0123, 1e-9));
    expect(c[1].n, 200);
    expect(c[1].q, isNull);
    expect(c[2].p, closeTo(0.25, 1e-9));
    expect(c[3].pnet, closeTo(0.05, 1e-9));
    expect(r.nodes, 801);
  });

  test('LaunchConfig: --start-fen giữ nguyên FEN có khoảng trắng; --start-fen-file; --replay-dir', () {
    const fen = 'vrcbqkbgrv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRCBQKBGRV w - - 7+7 0 1';
    final c = LaunchConfig.fromArgs(['--engine', 'e.exe', '--start-fen', fen, '--self-play']);
    expect(c.startFen, fen);
    expect(c.selfPlay, true);

    final f = File('${Directory.systemTemp.path}${Platform.pathSeparator}fz_fen_test.txt');
    f.writeAsStringSync('# thế ngẫu nhiên\n\n$fen\nkhong dung\n');
    final c2 = LaunchConfig.fromArgs(['--start-fen-file', f.path]);
    expect(c2.startFen, fen);
    f.deleteSync();
    expect(LaunchConfig.fromArgs(['--start-fen-file', f.path]).startFen, isNull); // tệp không có: bỏ qua

    final c3 = LaunchConfig.fromArgs(['--replay-dir', r'D:\x\xem_gen1', '--replay-game', '305']);
    expect(c3.replayDir, r'D:\x\xem_gen1');
    expect(c3.replayGame, 305);
    expect(c3.replayPath, isNull);

    // Dạng gói của flutter run vẫn tách được.
    final c4 = LaunchConfig.fromArgs(['--engine e.exe --provider dml --replay-dir d']);
    expect(c4.provider, 'dml');
    expect(c4.replayDir, 'd');
  });

  testWidgets('GamePicker: lọc theo kết quả / số quân, sắp xếp, bấm dòng chọn ván, [ ] chuyển ván', (tester) async {
    final dir = Directory.systemTemp.createTempSync('fz_pick_');
    File('${dir.path}${Platform.pathSeparator}chi_muc.tsv').writeAsStringSync(_tsv);
    final lib = ReplayLibrary.load(dir.path);
    final picked = <int>[];
    final key = GlobalKey<GamePickerState>();
    await tester.binding.setSurfaceSize(const Size(400, 900));
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: SizedBox(
          width: 330,
          height: 880,
          child: GamePicker(key: key, library: lib, selectedId: 0, onSelect: (e) => picked.add(e.id)),
        ),
      ),
    ));
    expect(find.textContaining('5/5'), findsOneWidget);
    expect(key.currentState!.filtered.map((e) => e.id), [0, 1, 2, 3, 4]);

    await tester.tap(find.text('Đen thắng').first); // chip
    await tester.pump();
    expect(find.textContaining('2/5'), findsOneWidget);
    expect(key.currentState!.filtered.map((e) => e.id), [1, 2]);

    // Chỉ ván thắng thua còn nhiều quân: 4 ván thắng thua, chỉ #0 (60) và #2 (60) và #4 (59) từ 59 quân trở lên.
    await tester.tap(find.text('Tất cả').first);
    await tester.pump();
    final st = key.currentState!;
    st.selectRelative(1); // selectedId = 0 (widget không đổi), ván kế = #1
    expect(picked.last, 1);
    st.selectRelative(-1);
    expect(picked.last, 0, reason: 'lùi từ ván chọn #0 vẫn ở #0 (đầu danh sách)');

    await tester.tap(find.text('#2'));
    await tester.pump();
    expect(picked.last, 2);
    await tester.binding.setSurfaceSize(null);
    dir.deleteSync(recursive: true);
  });

  test('BoardState.pieceCounts', () {
    final b = BoardState.fromFen('vrcbqkbgrv/msysnnsysm/yppppppppy/10/10/10/10/YPPPPPPPPY/MSYSNNSYSM/VRCBQKBGRV w - - 7+7 0 1');
    expect(b.pieceCounts(), (30, 30));
  });

  test('(cần engine) ván trong dữ liệu đời 1: lý do và số quân khớp chi_muc.tsv', () async {
    final exe = Platform.environment['FZ_ENGINE'];
    final dir = Platform.environment['FZ_REPLAY_DIR'];
    if (exe == null || dir == null || !Directory(dir).existsSync()) {
      markTestSkipped('đặt FZ_ENGINE và FZ_REPLAY_DIR (thư mục từ xem_du_lieu.py --xuat) để chạy');
      return;
    }
    final lib = ReplayLibrary.load(dir);
    final pick = [for (final e in lib.entries) if (e.note.isEmpty) e].take(6).toList();
    final engine = UciProcessEngine(LaunchConfig(enginePath: exe, visits: 1));
    final c = GameController(engine: engine, humanIsWhite: true, replay: true);
    for (final e in pick) {
      final text = File(lib.pathOf(e)).readAsStringSync();
      final lines = text.split('\n');
      final posLine = lines.lastWhere((l) => l.startsWith('position fen '));
      final head = posLine.substring('position fen '.length);
      final mi = head.indexOf(' moves ');
      final fen = mi < 0 ? head : head.substring(0, mi);
      final moves = [
        if (mi >= 0) ...head.substring(mi + 7).trim().split(' '),
        RegExp(r'→\s*(\S+)').firstMatch(lines.lastWhere((l) => l.startsWith('--- nửa nước')))!.group(1)!,
      ];
      await c.initReplay(moves, startFen: fen, replaySearches: SearchRecord.parseLog(text));
      expect(c.status, isNull, reason: 'ván #${e.id}: ${c.status}');
      expect(c.moves.length, e.plies, reason: 'ván #${e.id}');
      expect(c.end!.pieces, e.pieces, reason: 'ván #${e.id}: số quân');
      final want = {
        'checks': EndReason.checks,
        'no_moves': EndReason.noMoves,
        'rule50': EndReason.rule50,
        'repetition': EndReason.repetition,
        'cut': EndReason.unfinished,
      }[e.reason];
      expect(c.end!.reason, want, reason: 'ván #${e.id}: lý do ${e.reason}');
      expect(c.checksGiven.length, e.plies);
    }
    c.dispose();
  }, timeout: const Timeout(Duration(minutes: 3)));
}
