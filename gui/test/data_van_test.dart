// Đọc dữ liệu huấn luyện bằng Dart (lib/data): phải cho ĐÚNG từng byte như custom_engine/python/xem_du_lieu.py.
//
// Luôn chạy: các ván mẫu trong test/fixtures/v6 (tệp .xz thật của đời 44 + nhật ký do bản Python ghi, tên "<số ván>_van_NNNN.txt").
// Chạy thêm khi đặt biến môi trường (so cả đời dữ liệu; bản chuẩn ghi bằng `py -3 xem_du_lieu.py <nguồn> --xuat <thư mục> --engine ...`):
//   FZ_ENGINE=...\custom_engine.exe  FZ_DATA=<thư mục hoặc gói .zip>  FZ_DATA_REF=<thư mục bản Python>
import 'dart:io';

import 'package:fairyzero_gui/data/final_oracle.dart';
import 'package:fairyzero_gui/data/game_library.dart';
import 'package:fairyzero_gui/data/v6_game.dart';
import 'package:fairyzero_gui/data/van.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('fmt4 giống format(v, ".4f") của Python, kể cả chỗ đúng giữa', () {
    // Giá trị chuẩn do Python 3 in ra (scratchpad/py_tron.py).
    const cases = <(double, String)>[
      (0.03125, '0.0312'),
      (0.09375, '0.0938'),
      (0.15625, '0.1562'),
      (0.5, '0.5000'),
      (-0.03125, '-0.0312'),
      (-0.0, '-0.0000'),
      (0.0, '0.0000'),
      (1.0, '1.0000'),
      (-1.0, '-1.0000'),
      (0.00005, '0.0001'),
      (-0.00005, '-0.0001'),
      (0.99995, '1.0000'),
      (0.12345, '0.1235'),
      (0.12345679104328156, '0.1235'),
      (-0.699999988079071, '-0.7000'),
      (0.46875, '0.4688'),
      (0.28125, '0.2812'),
      (12.5, '12.5000'),
      (0.0000500001, '0.0001'),
      (1e-7, '0.0000'),
      (123456.78125, '123456.7812'),
    ];
    for (final (v, want) in cases) {
      expect(fmt4(v), want, reason: 'fmt4($v)');
    }
  });

  test('pyRound làm tròn về số chẵn khi đúng giữa như round() của Python', () {
    const cases = <(double, int)>[
      (0.5, 0),
      (1.5, 2),
      (2.5, 2),
      (3.5, 4),
      (0.49999, 0),
      (0.5000001, 1),
      (0.0, 0),
      (10.5, 10),
      (999.5, 1000),
      (1000.5, 1000),
      (123.4, 123),
      (0.4999999999, 0),
    ];
    for (final (v, want) in cases) {
      expect(pyRound(v), want, reason: 'pyRound($v)');
    }
  });

  test(
    'nuocTuChiSo: nước thường, Mã, lạc đà, phong cấp, khung nhìn của Đen',
    () {
      expect(nuocTuChiSo(0 * 100 + 11, false), 'b2b3'); // hướng Bắc, 1 bước
      expect(nuocTuChiSo(0 * 100 + 11, true), 'b9b8'); // Đen: hàng lật
      expect(nuocTuChiSo(72 * 100 + 0, false), 'a1b3'); // Mã (1, 2)
      expect(nuocTuChiSo(80 * 100 + 0, false), 'a1b4'); // lạc đà (1, 3)
      expect(nuocTuChiSo(89 * 100 + 88, false), 'i9i10n'); // phong Mã, đi thẳng
      expect(
        nuocTuChiSo(88 * 100 + 88, false),
        'i9h10n',
      ); // phong Mã, ăn chéo trái
      expect(() => nuocTuChiSo(115 * 100, false), throwsFormatException);
    },
  );

  test('lyDo cùng thứ tự kiểm với engine', () {
    String fen(String ck, int r50) => 'x w - - $ck $r50 1';
    expect(lyDo(fen('0+3', 0), 'black', 5, 40, 'B'), 'checks');
    expect(lyDo(fen('3+0', 0), 'white', 5, 40, 'W'), 'checks');
    expect(lyDo(fen('3+3', 100), 'draw', 5, 40, 'D'), 'rule50');
    expect(lyDo(fen('3+3', 100), 'white', 0, 40, 'W'), 'no_moves');
    expect(lyDo(fen('3+3', 4), 'draw', 5, 40, 'D'), 'repetition');
    expect(lyDo(fen('3+3', 4), 'white', 0, 40, 'W'), 'no_moves');
    expect(lyDo(fen('3+3', 4), 'white', 7, 40, 'W'), 'unknown');
    expect(lyDo(fen('3+3', 4), 'undecided', 7, 400, 'D'), 'cut');
    expect(lyDo(fen('3+3', 4), 'undecided', 7, 90, 'W'), 'adjudicated');
  });

  final fixDir = Directory('test/fixtures/v6');
  final games =
      fixDir
          .listSync()
          .whereType<File>()
          .where((f) => f.path.endsWith('.xz'))
          .toList()
        ..sort((a, b) => a.path.compareTo(b.path));

  test('có ván mẫu', () => expect(games.length, greaterThanOrEqualTo(4)));

  // Số ván (theo thứ tự tên tệp của đời 44, như bản Python) của các ván mẫu; bản chuẩn là ref/<số ván>_van_<số ván>.txt.
  const soVanCua = {
    '261_game_80.xz': 519,
    '1016_game_29.xz': 201,
    '1016_game_0.xz': 0,
    '1016_game_131.xz': 37,
    '1016_game_268.xz': 188,
  };
  for (final g in games) {
    final name = g.uri.pathSegments.last;
    test('ván mẫu $name: nhật ký giống bản Python từng byte, giải mã đúng', () {
      final soVan = soVanCua[name]!;
      final tag = soVan.toString().padLeft(4, '0');
      final ref = File('test/fixtures/v6/ref/${tag}_van_$tag.txt');
      final van = Van(decodeV6Game(g.readAsBytesSync(), name), name);
      expect(
        van.kiem(),
        isEmpty,
        reason: 'giải mã phải khớp bàn cờ bản ghi kế tiếp',
      );
      expect(nhatKy(van, soVan: soVan, tong: 1016), ref.readAsStringSync());
    });
  }

  test('tệp hỏng: ném FormatException, không sập', () {
    final bytes = games.first.readAsBytesSync();
    final bad = bytes.sublist(0, bytes.length ~/ 2);
    expect(() => decodeV6Game(bad, 'hỏng'), throwsA(anything));
    expect(() => decodeV6Game(bytes.sublist(0, 10), 'cụt'), throwsA(anything));
  });

  final engine = Platform.environment['FZ_ENGINE'];
  final data = Platform.environment['FZ_DATA'];
  final ref = Platform.environment['FZ_DATA_REF'];
  if (engine != null && data != null && ref != null) {
    test(
      'cả đời dữ liệu ($data) giống bản Python từng byte (nhật ký + chi_muc.tsv)',
      () async {
        final ds = listGames(data);
        final oracle = await ProcessFinalOracle.start(engine);
        final reader = GameReader();
        final rows = <IndexRow>[];
        final bad = <String>[];
        try {
          for (int i = 0; i < ds.length; i++) {
            String? text;
            rows.add(
              await indexRowOf(
                i,
                ds.length,
                ds[i],
                reader,
                oracle,
                log: (t) => text = t,
              ),
            );
            final want = File('$ref/${tenLogOf(i)}').readAsStringSync();
            if (text != want) bad.add(tenLogOf(i));
          }
        } finally {
          await oracle.close();
        }
        expect(bad, isEmpty, reason: 'nhật ký khác bản Python');
        expect(indexTsv(rows), File('$ref/chi_muc.tsv').readAsStringSync());
      },
      timeout: const Timeout(Duration(minutes: 10)),
    );
  }
}
