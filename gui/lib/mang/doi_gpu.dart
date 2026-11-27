import 'dart:convert';
import 'dart:io';
import 'dart:isolate';
import 'dart:typed_data';

import 'doi_pt.dart';

/// Mạng GPU (TFLite, lô cố định) của một mạng đã đổi, cạnh `khung.onnx` trong `<kho>/gen<N>/`.
const String kTenGpu = 'gpu_b16.tflite';

/// Bảng ghép GPU do `custom_engine/python/khung_gpu.py dung` viết (asset `assets/mang/bang_ghep_gpu_b16.json`): mỗi chỗ ghép
/// là byte [viTri, viTri + soByte) của khung `.tflite`, lấy từ tensor [ten] qua phép [phep]: `id` (giữ nguyên), `T` (chuyển
/// vị ma trận) hay `relb` (bảng thiên lệch vị trí tương đối [6,361] lấy thành [6,100,100]).
class BangGhepGpu {
  final String tep;
  final int coTep;
  final List<({String ten, String phep, int viTri, int soByte})> ghep;
  BangGhepGpu._(this.tep, this.coTep, this.ghep);

  factory BangGhepGpu.fromJson(String text) {
    final j = jsonDecode(text) as Map<String, dynamic>;
    return BangGhepGpu._(j['tep'] as String, j['co_tep'] as int, [
      for (final r in (j['ghep'] as List).cast<Map<String, dynamic>>())
        (ten: r['ten'] as String, phep: r['phep'] as String, viTri: r['vi_tri'] as int, soByte: r['so_byte'] as int),
    ]);
  }
}

/// Chỉ số của bảng thiên lệch vị trí tương đối (model._relative_index): ô truy vấn i, ô khoá j (= hàng * 10 + cột) ->
/// hàng của bảng 19 x 19 cho độ lệch (hàng j - hàng i, cột j - cột i).
int _relIndex(int i, int j) => ((j ~/ 10) - (i ~/ 10) + 9) * 19 + ((j % 10) - (i % 10) + 9);

/// Byte float32 của tensor [t] (hình [hinh]) sau phép [phep].
Uint8List _bienDoi(Float32List t, List<int> hinh, String phep) {
  switch (phep) {
    case 'id':
      return Uint8List.sublistView(t);
    case 'T':
      if (hinh.length != 2) throw FormatException('phép T cần ma trận, tensor có hình $hinh');
      final r = hinh[0], c = hinh[1];
      final out = Float32List(r * c);
      for (var i = 0; i < r; i++) {
        for (var j = 0; j < c; j++) {
          out[j * r + i] = t[i * c + j];
        }
      }
      return Uint8List.sublistView(out);
    case 'relb':
      final heads = hinh[0], cot = hinh[1];
      final out = Float32List(heads * 100 * 100);
      for (var h = 0; h < heads; h++) {
        for (var i = 0; i < 100; i++) {
          for (var j = 0; j < 100; j++) {
            out[(h * 100 + i) * 100 + j] = t[h * cot + _relIndex(i, j)];
          }
        }
      }
      return Uint8List.sublistView(out);
  }
  throw FormatException('phép ghép lạ: $phep');
}

/// Byte của mạng GPU: khung [khung] với mọi chỗ ghép thay bằng trọng số trong [trongSo] (tệp trọng số của khung ONNX, theo
/// [bang]). Giống từng byte `khung_gpu.py va`.
Uint8List mangGpu(Uint8List khung, BangGhepGpu gpu, Uint8List trongSo, BangGhep bang) {
  if (khung.length != gpu.coTep) throw FormatException('khung GPU ${khung.length} byte, bảng ghép ghi ${gpu.coTep}');
  final theoTen = {for (final t in bang.tensor) t.ten: t};
  final out = Uint8List.fromList(khung);
  for (final r in gpu.ghep) {
    final t = theoTen[r.ten];
    if (t == null) throw FormatException('bảng ghép GPU cần ${r.ten}, khung ONNX không có');
    final f = Float32List.sublistView(trongSo, t.viTri, t.viTri + t.soByte);
    final b = _bienDoi(f, t.hinh, r.phep);
    if (b.length != r.soByte) throw FormatException('${r.ten} (${r.phep}): ${b.length} byte, chỗ ghép cần ${r.soByte}');
    out.setRange(r.viTri, r.viTri + r.soByte, b);
  }
  return out;
}

/// Tạo `gpu_b16.tflite` trong thư mục mạng [dir] (đã có tệp trọng số của khung ONNX). Ghi tệp tạm rồi đổi tên.
Future<void> taoMangGpu({
  required String dir,
  required Uint8List khungGpu,
  required String bangGpuJson,
  required String bangGhepJson,
}) async {
  final bang = BangGhep.fromJson(bangGhepJson);
  final w = await File('$dir/${bang.tepTrongSo}').readAsBytes();
  final bytes = mangGpu(khungGpu, BangGhepGpu.fromJson(bangGpuJson), w, bang);
  final tam = File('$dir/$kTenGpu.tam');
  await tam.writeAsBytes(bytes, flush: true);
  tam.renameSync('$dir/$kTenGpu');
}

/// [taoMangGpu] trong một isolate riêng (hàm đứng riêng: bao đóng chỉ mang các tham số).
Future<void> taoMangGpuNen({
  required String dir,
  required Uint8List khungGpu,
  required String bangGpuJson,
  required String bangGhepJson,
}) =>
    Isolate.run(() => taoMangGpu(dir: dir, khungGpu: khungGpu, bangGpuJson: bangGpuJson, bangGhepJson: bangGhepJson));
