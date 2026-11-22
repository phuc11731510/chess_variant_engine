// Đổi dữ liệu huấn luyện sang nhật ký xem lại BẰNG DART (cùng việc của custom_engine/python/xem_du_lieu.py --xuat).
// Dùng để kiểm bản Dart so với bản Python (so từng byte) và để thử tốc độ:
//   dart run tool/doi_du_lieu.dart <nguồn> <thư mục ra> --engine <custom_engine.exe> [--khong-nhat-ky]
import 'dart:io';

import 'package:fairyzero_gui/data/final_oracle.dart';
import 'package:fairyzero_gui/data/game_library.dart';

Future<void> main(List<String> args) async {
  String? engine;
  bool nhatKy = true;
  final pos = <String>[];
  for (int i = 0; i < args.length; i++) {
    if (args[i] == '--engine') {
      engine = args[++i];
    } else if (args[i] == '--khong-nhat-ky') {
      nhatKy = false;
    } else {
      pos.add(args[i]);
    }
  }
  if (pos.length != 2) {
    stderr.writeln('cách dùng: dart run tool/doi_du_lieu.dart <nguồn> <thư mục ra> --engine <exe> [--khong-nhat-ky]');
    exit(2);
  }
  final sw = Stopwatch()..start();
  final ds = listGames(pos[0]);
  stdout.writeln('${ds.length} ván (${sw.elapsedMilliseconds} ms để liệt kê)');
  final out = Directory(pos[1])..createSync(recursive: true);
  final oracle = engine == null ? null : await ProcessFinalOracle.start(engine);
  final reader = GameReader();
  final rows = <IndexRow>[];
  try {
    for (int i = 0; i < ds.length; i++) {
      rows.add(await indexRowOf(i, ds.length, ds[i], reader, oracle,
          log: nhatKy ? (t) => File('${out.path}/${tenLogOf(i)}').writeAsStringSync(t) : null));
      if ((i + 1) % 200 == 0) stdout.writeln('${i + 1}/${ds.length} ván… ${sw.elapsedMilliseconds} ms');
    }
  } finally {
    await oracle?.close();
  }
  File('${out.path}/chi_muc.tsv').writeAsStringSync(indexTsv(rows));
  final xau = rows.where((r) => r.ghiChu.isNotEmpty).length;
  stdout.writeln('ghi ${rows.length} dòng chỉ mục${nhatKy ? ' + nhật ký' : ''} trong ${sw.elapsedMilliseconds} ms'
      '${xau > 0 ? '; $xau ván có ghi chú lỗi' : ''}');
}
