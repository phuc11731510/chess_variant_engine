import 'dart:typed_data';

import 'package:archive/archive.dart' show XZDecoder;

/// Giải mã một ván của DỮ LIỆU HUẤN LUYỆN: tệp `.xz` định dạng v6 (`custom_engine/python/trainingdata_v6.py`
/// là nguồn chuẩn; đây là bản Dart của phần xem ván, để điện thoại đọc thẳng dữ liệu mà không cần Python).
///
/// Chỉ giải mã phần xem ván cần: thế (mặt phẳng quân của ply 0), lượt đi, số chiếu, nước đã đi / nước tốt nhất,
/// số lượt thăm của từng nước hợp lệ, các giá trị Q / WDL. Lịch sử 7 ply trước (chỉ để huấn luyện) được bỏ qua.
/// Kết quả phải GIỐNG HỆT bản Python (test/data_van_test.dart so từng byte nhật ký với `xem_du_lieu.py`).

const int boardSize = 10;
const int pieceKinds = 12;
const int planesPerBoard = 2 * pieceKinds + 1;

// Khớp custom_engine/python/nn_layout.py: 8 hướng x 9 bước trượt + 8 nước Mã + 8 nước lạc đà + 9 quân phong x 3 hướng.
const int _moveTypes = 8 * 9 + 8 + 8 + 9 * 3;
const int policySize = _moveTypes * boardSize * boardSize;

const int _flagFull = 1;
const int _flagFloatPi = 2;
const int _flagDensePi = 4;
const int _containerRevision = 3;
const int _headerSize = 32;

/// Một bản ghi (một nửa nước) của ván.
class V6Record {
  /// Mặt phẳng quân của ply 0, 25 mặt phẳng x (thấp, cao): 12 loại quân của bên đi, 12 của bên kia, mặt phẳng lặp thế.
  /// Mỗi mặt phẳng là mặt nạ 128 bit (12 bit mỗi hàng) nhìn từ phía bên đi.
  final Int64List planes;
  final int rule50;
  final int epLo, epHi;
  final int checksUs, checksThem;

  /// 0 = Trắng đi, 1 = Đen đi.
  final int sideToMove;
  final double resultQ, resultD, rootQ, rootD, bestQ, playedQ;
  final int visits, playedIdx, bestIdx;

  /// Chỉ số policy của các nước hợp lệ (tăng dần) và xác suất đã chuẩn hoá (= lượt thăm / tổng) của chúng.
  final Uint16List legalIdx;
  final Float32List legalPi;

  V6Record({
    required this.planes,
    required this.rule50,
    required this.epLo,
    required this.epHi,
    required this.checksUs,
    required this.checksThem,
    required this.sideToMove,
    required this.resultQ,
    required this.resultD,
    required this.rootQ,
    required this.rootD,
    required this.bestQ,
    required this.playedQ,
    required this.visits,
    required this.playedIdx,
    required this.bestIdx,
    required this.legalIdx,
    required this.legalPi,
  });
}

final Float32List _f32 = Float32List(1);

/// Làm tròn về float32 (như numpy float32).
double toF32(double x) {
  _f32[0] = x;
  return _f32[0];
}

/// Giải nén + giải mã một ván `.xz`. Ném [FormatException] nếu tệp hỏng hoặc không nhất quán
/// (cùng các kiểm tra như `decode_arrays` của Python).
List<V6Record> decodeV6Game(Uint8List xz, String where) {
  final Uint8List buf;
  try {
    buf = XZDecoder().decodeBytes(xz);
  } catch (e) {
    throw FormatException('damaged v6 game ($where): $e');
  }
  if (buf.length < _headerSize) {
    throw FormatException('truncated v6 game ($where)');
  }
  final bd = ByteData.sublistView(buf);
  final magic = String.fromCharCodes(buf.sublist(0, 4));
  final rev = bd.getUint32(4, Endian.little);
  if (magic != 'FZD6' || rev != _containerRevision) {
    throw FormatException(
      'not a v6 game (magic "$magic", revision $rev) ($where)',
    );
  }
  final n = bd.getUint32(16, Endian.little);
  final lTotal = bd.getUint32(20, Endian.little);
  final lf = bd.getUint32(24, Endian.little);
  final f = bd.getUint32(28, Endian.little);

  int pos = _headerSize;
  int take(int bytes) {
    final at = pos;
    pos += bytes;
    if (pos > buf.length) throw FormatException('truncated v6 game ($where)');
    return at;
  }

  final flagsAt = take(n);
  final nLegalAt = take(2 * n);
  int u8(int base, int i) => buf[base + i];
  int u16(int base, int i) => bd.getUint16(base + 2 * i, Endian.little);

  int sumLegal = 0, nFloatLegal = 0, nFull = 0, nDense = 0;
  for (int k = 0; k < n; k++) {
    final fl = u8(flagsAt, k);
    final nl = u16(nLegalAt, k);
    sumLegal += nl;
    if (fl & _flagFloatPi != 0) nFloatLegal += nl;
    if (fl & _flagFull != 0) nFull++;
    if (fl & _flagDensePi != 0) nDense++;
    if (fl > (_flagFull | _flagFloatPi | _flagDensePi) ||
        (fl & _flagFloatPi != 0 && fl & _flagDensePi != 0) ||
        (fl & _flagDensePi != 0 && nl != 0)) {
      throw FormatException('invalid v6 flags ($where)');
    }
  }
  if (sumLegal != lTotal || lf > lTotal) {
    throw FormatException('inconsistent v6 legal-move counts ($where)');
  }
  if (nFloatLegal != lf || nFull != f) {
    throw FormatException('inconsistent v6 flags ($where)');
  }
  if (n > 0 && u8(flagsAt, 0) & _flagFull == 0) {
    throw FormatException('invalid v6 flags ($where)');
  }

  final deltaAt = take(2 * lTotal);
  final countsAt = take(2 * (lTotal - lf));
  final pifAt = take(4 * lf);
  final pidAt = take(4 * nDense * policySize);
  final curAt = take(8 * n * planesPerBoard * 2);
  take(
    8 * f * 7 * planesPerBoard * 2,
  ); // lịch sử của các bản ghi FULL: chỉ để huấn luyện
  final rule50At = take(n);
  final epAt = take(16 * n);
  final cuAt = take(n);
  final ctAt = take(n);
  final stmAt = take(n);
  final floatsAt = take(4 * 11 * n);
  final visitsAt = take(4 * n);
  final playedAt = take(2 * n);
  final bestAt = take(2 * n);
  take(2 * n); // plies_left
  take(n); // fast_search
  if (pos != buf.length) {
    throw FormatException(
      'v6 game has ${buf.length - pos} trailing bytes ($where)',
    );
  }

  double fl32(int col, int k) =>
      bd.getFloat32(floatsAt + 4 * (col * n + k), Endian.little);
  // Cột số thực theo thứ tự FLOAT_KEYS: result_q, result_d, root_q, root_d, best_q, best_d, played_q, played_d, ...
  const cResultQ = 0,
      cResultD = 1,
      cRootQ = 2,
      cRootD = 3,
      cBestQ = 4,
      cPlayedQ = 6;

  final out = <V6Record>[];
  int legalPos = 0, countPos = 0, floatPos = 0, denseSeen = 0;
  for (int k = 0; k < n; k++) {
    final flags = u8(flagsAt, k);
    final nl = u16(nLegalAt, k);
    late Uint16List idx;
    late Float32List pi;
    if (flags & _flagDensePi != 0) {
      // Cả mảng xác suất được giữ: nước hợp lệ là các ô >= 0 (giống Python: pd >= 0).
      final base = pidAt + 4 * denseSeen * policySize;
      denseSeen++;
      final li = <int>[];
      final lp = <double>[];
      for (int j = 0; j < policySize; j++) {
        final v = bd.getFloat32(base + 4 * j, Endian.little);
        if (v >= 0) {
          li.add(j);
          lp.add(v);
        }
      }
      idx = Uint16List.fromList(li);
      pi = Float32List.fromList(lp);
    } else {
      idx = Uint16List(nl);
      pi = Float32List(nl);
      int cs = 0;
      for (int j = 0; j < nl; j++) {
        final d = u16(deltaAt, legalPos + j);
        if (j > 0 && d == 0) {
          throw FormatException('invalid v6 legal-move indices ($where)');
        }
        cs += d;
        if (cs >= policySize) {
          throw FormatException('invalid v6 legal-move indices ($where)');
        }
        idx[j] = cs;
      }
      if (flags & _flagFloatPi != 0) {
        for (int j = 0; j < nl; j++) {
          pi[j] = bd.getFloat32(pifAt + 4 * (floatPos + j), Endian.little);
        }
        floatPos += nl;
      } else {
        double tot = 0;
        for (int j = 0; j < nl; j++) {
          tot += u16(countsAt, countPos + j);
        }
        final t = toF32(tot);
        for (int j = 0; j < nl; j++) {
          final c = u16(countsAt, countPos + j).toDouble();
          // float32(n) / float32(tổng) như numpy: chia số double rồi làm tròn về float32 cho đúng từng bit.
          pi[j] = t > 0 ? toF32(c / t) : 0.0;
        }
        countPos += nl;
      }
      legalPos += nl;
    }
    final planes = Int64List(planesPerBoard * 2);
    for (int j = 0; j < planes.length; j++) {
      planes[j] = bd.getInt64(
        curAt + 8 * (k * planesPerBoard * 2 + j),
        Endian.little,
      );
    }
    out.add(
      V6Record(
        planes: planes,
        rule50: u8(rule50At, k),
        epLo: bd.getInt64(epAt + 16 * k, Endian.little),
        epHi: bd.getInt64(epAt + 16 * k + 8, Endian.little),
        checksUs: u8(cuAt, k),
        checksThem: u8(ctAt, k),
        sideToMove: u8(stmAt, k),
        resultQ: fl32(cResultQ, k),
        resultD: fl32(cResultD, k),
        rootQ: fl32(cRootQ, k),
        rootD: fl32(cRootD, k),
        bestQ: fl32(cBestQ, k),
        playedQ: fl32(cPlayedQ, k),
        visits: bd.getUint32(visitsAt + 4 * k, Endian.little),
        playedIdx: u16(playedAt, k),
        bestIdx: u16(bestAt, k),
        legalIdx: idx,
        legalPi: pi,
      ),
    );
  }
  return out;
}
