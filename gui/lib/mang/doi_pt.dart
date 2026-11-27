import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'pt_doc.dart';

/// Tên tệp trong thư mục của MỘT mạng đã đổi (`<kho>/gen<N>/`).
const String kTenKhung = 'khung.onnx';
const String kTenXong = 'xong.txt';

/// Bảng ghép do `custom_engine/python/khung_mang.py dung` viết (asset `assets/mang/bang_ghep.json`): mỗi trọng số của khung
/// là đúng một tensor của state_dict, nằm ở [viTri] byte trong tệp trọng số.
class BangGhep {
  final int phienBan;
  final String tepTrongSo;
  final int tongByte;
  final List<({String ten, List<int> hinh, int viTri, int soByte})> tensor;
  BangGhep._(this.phienBan, this.tepTrongSo, this.tongByte, this.tensor);

  factory BangGhep.fromJson(String text) {
    final j = jsonDecode(text) as Map<String, dynamic>;
    return BangGhep._(
      j['phien_ban'] as int,
      j['tep_trong_so'] as String,
      j['tong_byte'] as int,
      [
        for (final r in (j['tensor'] as List).cast<Map<String, dynamic>>())
          (
            ten: r['ten'] as String,
            hinh: (r['hinh'] as List).cast<int>(),
            viTri: r['vi_tri'] as int,
            soByte: r['so_byte'] as int,
          ),
      ],
    );
  }
}

/// Byte của tệp trọng số cho [sd] theo [bang]; .pt lệch (thiếu / thừa tensor, sai hình dạng) thì ném [PtFormatException].
Uint8List trongSoTuPt(PtStateDict sd, BangGhep bang) {
  final out = Uint8List(bang.tongByte);
  final con = sd.tensors.keys.toSet();
  for (final r in bang.tensor) {
    final t = sd.tensors[r.ten];
    if (t == null) throw PtFormatException('thiếu tensor ${r.ten} (mạng khác kiến trúc?)');
    con.remove(r.ten);
    if (t.shape.length != r.hinh.length || !Iterable.generate(r.hinh.length).every((i) => t.shape[i] == r.hinh[i])) {
      throw PtFormatException('${r.ten}: hình ${t.shape}, khung cần ${r.hinh} (mạng khác kiến trúc?)');
    }
    final b = sd.bytesOf(r.ten);
    if (b.length != r.soByte) throw PtFormatException('${r.ten}: ${b.length} byte, khung cần ${r.soByte}');
    out.setRange(r.viTri, r.viTri + r.soByte, b);
  }
  if (con.isNotEmpty) throw PtFormatException('.pt có tensor khung không biết: ${con.take(5).join(', ')}');
  return out;
}

/// Đổi tệp [ptPath] thành thư mục mạng [dich]: `khung.onnx` (chép [khung]) + tệp trọng số + `xong.txt` (đánh dấu đã đủ).
/// Ghi vào `<dich>.tam` rồi đổi tên, nên giữa chừng hỏng (hết pin, hết chỗ) thì không để lại thư mục dở. Chạy được trong
/// isolate (chỉ dùng dart:io).
Future<void> doiPt({
  required String ptPath,
  required String dich,
  required Uint8List khung,
  required String bangGhepJson,
}) async {
  final bang = BangGhep.fromJson(bangGhepJson);
  final sd = PtStateDict.decode(await File(ptPath).readAsBytes());
  final w = trongSoTuPt(sd, bang);
  final tam = Directory('$dich.tam');
  if (tam.existsSync()) tam.deleteSync(recursive: true);
  tam.createSync(recursive: true);
  await File('${tam.path}/$kTenKhung').writeAsBytes(khung, flush: true);
  await File('${tam.path}/${bang.tepTrongSo}').writeAsBytes(w, flush: true);
  await File('${tam.path}/$kTenXong').writeAsString('phien_ban=${bang.phienBan}\nnguon=${ptPath.split('/').last}\n', flush: true);
  final d = Directory(dich);
  if (d.existsSync()) d.deleteSync(recursive: true);
  tam.renameSync(dich);
}
