// Đổi .pt -> trọng số của khung mạng bằng Dart (lib/mang): phải cho ĐÚNG từng byte như custom_engine/python/khung_mang.py.
//
// Luôn chạy: bộ đọc pickle với một .pt nhỏ dựng tay (zip + data.pkl giao thức 2).
// Chạy thêm khi đặt biến môi trường (so một mạng thật; bản chuẩn ghi bằng `py khung_mang.py kiem gen201.pt --thu-muc <thư mục>`):
//   FZ_PT=<gen201.pt>  FZ_PT_REF=<thư mục chứa trong_so.bin do Python ghi>
//   FZ_GPU_REF=<gen201_gpu.tflite do `khung_gpu.py va --tu <FZ_PT_REF>` ghi>   (mạng GPU)
import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:fairyzero_gui/mang/doi_gpu.dart';
import 'package:fairyzero_gui/mang/doi_pt.dart';
import 'package:fairyzero_gui/mang/kho_mang.dart' show doiPtNen;
import 'package:fairyzero_gui/mang/pt_doc.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('đọc state_dict nhỏ dựng tay', () {
    // data.pkl giao thức 2 của OrderedDict{'a': tensor 2x3 ở storage '0', 'b': tensor 4 ở storage '1' từ phần tử 2};
    // mỗi tensor = REDUCE(_rebuild_tensor_v2, (storage, off, size, stride, False, ())).
    final o = BytesBuilder();
    void s(String x) { final b = Uint8List.fromList(x.codeUnits); o.addByte(0x58); o.add((ByteData(4)..setUint32(0, b.length, Endian.little)).buffer.asUint8List()); o.add(b); }
    o.add([0x80, 0x02]);
    o.add('ccollections\nOrderedDict\n'.codeUnits); o.addByte(0x29); o.addByte(0x52); o.add([0x71, 0x00]);
    o.addByte(0x28);
    for (final (name, key, off, size, stride) in [('a', '0', 0, [2, 3], [3, 1]), ('b', '1', 2, [4], [1])]) {
      s(name);
      o.add('ctorch._utils\n_rebuild_tensor_v2\n'.codeUnits);
      o.addByte(0x28);
      o.addByte(0x28); s('storage'); o.add('ctorch\nFloatStorage\n'.codeUnits); s(key); s('cpu'); o.add([0x4b, 6]); o.addByte(0x74); o.addByte(0x51);
      o.add([0x4b, off]);
      o.addByte(0x28); for (final d in size) { o.add([0x4b, d]); } o.addByte(0x74);
      o.addByte(0x28); for (final d in stride) { o.add([0x4b, d]); } o.addByte(0x74);
      o.addByte(0x89); o.addByte(0x29);
      o.addByte(0x74); o.addByte(0x52);
    }
    o.addByte(0x75); o.addByte(0x2e);
    final f0 = Float32List.fromList([1, 2, 3, 4, 5, 6]), f1 = Float32List.fromList([9, 9, 7, 8, 10, 11]);
    final z = Archive()
      ..addFile(ArchiveFile.bytes('m/data.pkl', o.toBytes()))
      ..addFile(ArchiveFile.bytes('m/byteorder', 'little'.codeUnits))
      ..addFile(ArchiveFile.bytes('m/data/0', f0.buffer.asUint8List()))
      ..addFile(ArchiveFile.bytes('m/data/1', f1.buffer.asUint8List()));
    final sd = PtStateDict.decode(Uint8List.fromList(ZipEncoder().encode(z)));
    expect(sd.tensors.keys.toList(), ['a', 'b']);
    expect(sd.tensors['a']!.shape, [2, 3]);
    expect(Float32List.sublistView(Uint8List.fromList(sd.bytesOf('a'))), f0);
    expect(Float32List.sublistView(Uint8List.fromList(sd.bytesOf('b'))).toList(), [7, 8, 10, 11]);
  });

  test('từ chối tên toàn cục lạ (không chạy mã trong tệp)', () {
    final o = BytesBuilder()..add([0x80, 0x02])..add('cos\nsystem\n'.codeUnits);
    final z = Archive()..addFile(ArchiveFile.bytes('m/data.pkl', o.toBytes()));
    expect(() => PtStateDict.decode(Uint8List.fromList(ZipEncoder().encode(z))), throwsA(isA<PtFormatException>()));
  });

  final pt = Platform.environment['FZ_PT'], ref = Platform.environment['FZ_PT_REF'];
  test('mạng thật: trong_so.bin giống từng byte bản Python', () {
    final bang = BangGhep.fromJson(File('assets/mang/bang_ghep.json').readAsStringSync());
    final w = trongSoTuPt(PtStateDict.decode(File(pt!).readAsBytesSync()), bang);
    final want = File('$ref/${bang.tepTrongSo}').readAsBytesSync();
    expect(w.length, want.length);
    var diff = -1;
    for (var i = 0; i < w.length; i++) {
      if (w[i] != want[i]) { diff = i; break; }
    }
    expect(diff, -1, reason: 'byte đầu tiên khác ở $diff');
  }, skip: pt == null || ref == null ? 'đặt FZ_PT và FZ_PT_REF để so mạng thật' : false);

  test('mạng thật: đổi trong isolate như app (doiPtNen) ra đủ thư mục mạng', () async {
    final tmp = Directory.systemTemp.createTempSync('fz_doi_');
    try {
      final dst = '${tmp.path}/gen201';
      await doiPtNen(
        ptPath: pt!,
        dich: dst,
        khung: File('assets/mang/$kTenKhung').readAsBytesSync(),
        bangGhepJson: File('assets/mang/bang_ghep.json').readAsStringSync(),
      );
      final bang = BangGhep.fromJson(File('assets/mang/bang_ghep.json').readAsStringSync());
      expect(File('$dst/$kTenXong').existsSync(), isTrue);
      expect(File('$dst/${bang.tepTrongSo}').readAsBytesSync(), File('$ref/${bang.tepTrongSo}').readAsBytesSync());
      expect(Directory('$dst.tam').existsSync(), isFalse);
    } finally {
      tmp.deleteSync(recursive: true);
    }
  }, skip: pt == null || ref == null ? 'đặt FZ_PT và FZ_PT_REF để so mạng thật' : false);

  final gpuRef = Platform.environment['FZ_GPU_REF'];
  test('mạng GPU: giống từng byte khung_gpu.py va', () {
    final bang = File('assets/mang/bang_ghep.json').readAsStringSync();
    final got = mangGpu(
      File('assets/mang/khung_gpu_b16.tflite').readAsBytesSync(),
      BangGhepGpu.fromJson(File('assets/mang/bang_ghep_gpu_b16.json').readAsStringSync()),
      File('$ref/trong_so.bin').readAsBytesSync(),
      BangGhep.fromJson(bang),
    );
    final want = File(gpuRef!).readAsBytesSync();
    expect(got.length, want.length);
    var diff = -1;
    for (var i = 0; i < got.length; i++) {
      if (got[i] != want[i]) { diff = i; break; }
    }
    expect(diff, -1, reason: 'byte đầu tiên khác ở $diff');
  }, skip: ref == null || gpuRef == null ? 'đặt FZ_PT_REF và FZ_GPU_REF để so mạng GPU' : false);
}
