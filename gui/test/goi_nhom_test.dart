// Nhóm gói của vòng lặp liên tục (`goi/goi_<số>_n<đời>_<ván>_<thế>.zip`): app gom các gói cùng đời mạng thành MỘT nguồn.
// Kiểm: liệt kê ván theo thứ tự tên gói, bỏ qua gói hỏng, dấu vân tay đổi khi thêm / bỏ gói, và đổi sang bảng ván
// (chi_muc.tsv + nhật ký từng ván) chạy hết rồi mở lại ngay khi nguồn không đổi.
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:fairyzero_gui/config/replay_library.dart';
import 'package:fairyzero_gui/data/game_library.dart';
import 'package:fairyzero_gui/data/generation_cache.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final fixtures =
      Directory(
          'test/fixtures/v6',
        ).listSync().whereType<File>().where((f) => f.path.endsWith('.xz')).toList()
        ..sort((a, b) => a.path.compareTo(b.path));

  late Directory tmp;
  setUp(() => tmp = Directory.systemTemp.createTempSync('goi_nhom_'));
  tearDown(() => tmp.deleteSync(recursive: true));

  /// Ghi một gói zip trong [tmp]/goi gồm các ván [games] (thành viên `games_gen7/<tên>`).
  String writeZip(String name, List<File> games) {
    final arch = Archive();
    for (final g in games) {
      final bytes = g.readAsBytesSync();
      arch.addFile(
        ArchiveFile(
          'games_gen7/${g.path.split(RegExp(r'[\\/]')).last}',
          bytes.length,
          bytes,
        ),
      );
    }
    final f = File('${tmp.path}/goi/$name')..createSync(recursive: true);
    f.writeAsBytesSync(ZipEncoder().encode(arch));
    return f.path;
  }

  test('có đủ ván mẫu', () => expect(fixtures.length, greaterThanOrEqualTo(4)));

  test('liệt kê ván theo thứ tự tên gói, bỏ qua gói hỏng và gói không còn', () {
    final a = writeZip('goi_00001_n7_2_100.zip', fixtures.sublist(0, 2));
    final bad = File('${tmp.path}/goi/goi_00002_n7_1_50.zip')
      ..writeAsBytesSync(List<int>.filled(300, 7));
    final b = writeZip('goi_00003_n7_2_100.zip', fixtures.sublist(2, 4));
    final gone = '${tmp.path}/goi/goi_00004_n7_1_50.zip';
    // Truyền cố tình lộn thứ tự: kết quả vẫn theo tên gói.
    final ds = listGames(groupSource([b, gone, bad.path, a]));
    expect(ds.length, 4);
    expect(ds.map((g) => g.path).toList(), [a, a, b, b]);
    expect(ds[0].name, startsWith('goi_00001_n7_2_100.zip:games_gen7/'));
  });

  test('nguồn đơn là gói hỏng: không có ván nào (hoặc báo lỗi), không sập', () {
    final bad = File('${tmp.path}/x.zip')
      ..writeAsBytesSync(List<int>.filled(300, 7));
    var ds = <GameSource>[];
    try {
      ds = listGames(bad.path);
    } catch (_) {
      // báo lỗi cũng được
    }
    expect(ds, isEmpty);
  });

  test('dấu vân tay nhóm đổi khi thêm gói, và không phải mở gói', () {
    final a = writeZip('goi_00001_n7_2_100.zip', fixtures.sublist(0, 2));
    final f1 = groupFingerprint([a]);
    expect(f1, groupFingerprint([a]));
    final b = writeZip('goi_00002_n7_2_100.zip', fixtures.sublist(2, 4));
    expect(groupFingerprint([a, b]), isNot(f1));
    // Gói không còn thì bị bỏ khỏi dấu (không ném lỗi).
    expect(groupFingerprint([a, '${tmp.path}/goi/khong_co.zip']), f1);
  });

  test('đổi nhóm gói sang bảng ván, mở lại ngay, thêm gói thì đổi lại', () async {
    final a = writeZip('goi_00001_n7_2_100.zip', fixtures.sublist(0, 2));
    final src1 = groupSource([a]);
    final cache = '${tmp.path}/xem/goi_n7';
    expect(isCurrent(src1, cache), isFalse);

    Future<ConvertEvent> run(String src) async {
      ConvertEvent? last;
      await for (final e in convert(src, cache, oracle: 'none')) {
        expect(e.error, isNull, reason: e.error);
        last = e;
      }
      return last!;
    }

    var end = await run(src1);
    expect(end.finished, isTrue);
    expect(end.total, 2);
    expect(isCurrent(src1, cache), isTrue);
    var rows = File('$cache/chi_muc.tsv').readAsLinesSync();
    expect(rows.length, 3); // dòng tiêu đề + 2 ván

    // Vòng lặp gửi thêm một gói của cùng đời mạng: chỉ mục cũ hết đúng, đổi lại thì đủ 4 ván.
    final b = writeZip('goi_00002_n7_2_100.zip', fixtures.sublist(2, 4));
    final src2 = groupSource([a, b]);
    expect(isCurrent(src2, cache), isFalse);
    end = await run(src2);
    expect(end.finished, isTrue);
    expect(end.total, 4);
    expect(isCurrent(src2, cache), isTrue);
    rows = File('$cache/chi_muc.tsv').readAsLinesSync();
    expect(rows.length, 5);

    // Nhật ký từng ván ghi khi mở, đọc được thành viên của gói nào cũng được.
    final prep = GameFilePreparer(cache);
    for (final i in [0, 3]) {
      prep.ensure(i);
      final text = File('$cache/${tenLogOf(i)}').readAsStringSync();
      expect(text, isNotEmpty);
    }
  });

  group('số ván cố định + dọn đệm', soVanVaDonDem);
}

// Số ván cố định theo gói + dọn bộ nhớ đệm không còn khớp dữ liệu.
void soVanVaDonDem() {
  late Directory tmp;
  setUp(() => tmp = Directory.systemTemp.createTempSync('goi_nhan_'));
  tearDown(() => tmp.deleteSync(recursive: true));

  test('nhãn ván = <số gói>.<thứ tự trong gói từ 1>, ổn định khi gói cũ bị dọn', () {
    const p = '/storage/emulated/0/Download/FairyZero/goi';
    final dayDu = [
      '$p/goi_00985_n103_2_100.zip\tgames_gen103/a.xz',
      '$p/goi_00985_n103_2_100.zip\tgames_gen103/b.xz',
      '$p/goi_00992_n103_3_100.zip\tgames_gen103/c.xz',
      '$p/goi_00992_n103_3_100.zip\tgames_gen103/d.xz',
      '$p/goi_00992_n103_3_100.zip\tgames_gen103/e.xz',
    ];
    final a = ReplayLibrary.labelsFromSources(dayDu);
    expect(a, {0: '985.1', 1: '985.2', 2: '992.1', 3: '992.2', 4: '992.3'});
    // Vòng lặp dọn gói 985: số thứ tự (id) của các ván còn lại đổi (0, 1, 2) nhưng nhãn vẫn là 992.x.
    final saukhidon = ReplayLibrary.labelsFromSources(dayDu.skip(2));
    expect(saukhidon, {0: '992.1', 1: '992.2', 2: '992.3'});
    // Nguồn không phải gói của vòng lặp: không nhãn (app hiện #id như cũ).
    expect(
      ReplayLibrary.labelsFromSources(['/x/games_gen5/van1.xz\t', '/x/games_gen5_7.zip\tm.xz']),
      isEmpty,
    );
  });

  test('ReplayLibrary.load gắn nhãn từ nguon.txt, thiếu nguon.txt thì #id', () {
    const tsv = 'so\ttep\tnua_nuoc\tket_qua\tquan_trang\tquan_den\tly_do\tghi_chu\n'
        '0\tvan_0000.txt\t16\tB\t29\t29\tno_moves\t\n'
        '1\tvan_0001.txt\t20\tW\t30\t28\tchecks\t\n';
    File('${tmp.path}/chi_muc.tsv').writeAsStringSync(tsv);
    var lib = ReplayLibrary.load(tmp.path);
    expect(lib.entries.map((e) => e.tag).toList(), ['#0', '#1']);
    File('${tmp.path}/nguon.txt').writeAsStringSync(
      'g1|1|1|1|1\n'
      '/d/goi/goi_00992_n103_2_100.zip\tgames_gen103/c.xz\n'
      '/d/goi/goi_00992_n103_2_100.zip\tgames_gen103/d.xz\n',
    );
    lib = ReplayLibrary.load(tmp.path);
    expect(lib.entries.map((e) => e.tag).toList(), ['992.1', '992.2']);
    expect(lib.entries[1].id, 1); // id nội bộ vẫn là vị trí trong bảng
  });

  test('purgeStaleCaches chỉ xoá thư mục đệm không nằm trong danh sách giữ', () {
    final xem = '${tmp.path}/xem';
    for (final n in ['goi_n103', 'goi_n64', 'games_gen45', 'games_gen55_723.zip']) {
      Directory('$xem/$n').createSync(recursive: true);
      File('$xem/$n/van_0001.txt').writeAsStringSync('x' * 1000);
    }
    File('$xem/tep_le.txt').writeAsStringSync('giữ'); // tệp lẻ không bị đụng
    final removed = purgeStaleCaches(xem, {'goi_n103', 'games_gen55_723.zip'});
    expect(removed, 2);
    expect(Directory('$xem/goi_n103').existsSync(), isTrue);
    expect(Directory('$xem/games_gen55_723.zip').existsSync(), isTrue);
    expect(Directory('$xem/goi_n64').existsSync(), isFalse);
    expect(Directory('$xem/games_gen45').existsSync(), isFalse);
    expect(File('$xem/tep_le.txt').existsSync(), isTrue);
    // Chạy lại: không còn gì để xoá; thư mục không có thì 0, không ném lỗi.
    expect(purgeStaleCaches(xem, {'goi_n103', 'games_gen55_723.zip'}), 0);
    expect(purgeStaleCaches('${tmp.path}/khong_co', {}), 0);
  });

  test('cacheNameOf bỏ ký tự lạ, giữ tên đời', () {
    expect(cacheNameOf('goi_n103'), 'goi_n103');
    expect(cacheNameOf('games_gen55_723.zip'), 'games_gen55_723.zip');
    expect(cacheNameOf('a b/c'), 'a_b_c');
  });
}
