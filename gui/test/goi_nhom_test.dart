// Nhóm gói của vòng lặp liên tục (`goi/goi_<số>_n<đời>_<ván>_<thế>.zip`): app gom các gói cùng đời mạng thành MỘT nguồn.
// Kiểm: liệt kê ván theo thứ tự tên gói, bỏ qua gói hỏng, dấu vân tay đổi khi thêm / bỏ gói, và đổi sang bảng ván
// (chi_muc.tsv + nhật ký từng ván) chạy hết rồi mở lại ngay khi nguồn không đổi.
import 'dart:io';

import 'package:archive/archive.dart';
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
}
