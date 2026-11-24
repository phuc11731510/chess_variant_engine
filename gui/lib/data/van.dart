import 'dart:typed_data';

import 'v6_game.dart';

/// Một ván của dữ liệu huấn luyện đã giải mã thành thế xuất phát (FEN), dãy nước UCI và dữ liệu từng nước.
/// Bản Dart của `Van` + `nhat_ky` trong `custom_engine/python/xem_du_lieu.py`: nhật ký ghi ra đúng định dạng
/// của `tu_dau_log/tu_dau_*.txt` nên `readReplayFile` / bảng tìm kiếm đọc được như mọi nhật ký khác.

const String _letters =
    'pnrqkbmvyscg'; // thứ tự loại quân trong mặt phẳng (kPieceKindOrder, encoder.cc)
const String _promo =
    'nbrqmvycg'; // quân phong cấp theo thứ tự ô policy (nn_layout.h)
const List<(int, int)> _slideDirs = [
  (0, 1),
  (1, 1),
  (1, 0),
  (1, -1),
  (0, -1),
  (-1, -1),
  (-1, 0),
  (-1, 1),
];
const List<(int, int)> _knight = [
  (1, 2),
  (2, 1),
  (2, -1),
  (1, -2),
  (-1, -2),
  (-2, -1),
  (-2, 1),
  (-1, 2),
];
const List<(int, int)> _camel = [
  (1, 3),
  (3, 1),
  (3, -1),
  (1, -3),
  (-1, -3),
  (-3, -1),
  (-3, 1),
  (-1, 3),
];
const int _slideTypes = 8 * 9;
const int _knightBase = _slideTypes;
const int _camelBase = _knightBase + 8;
const int _promotionBase = _camelBase + 8;

/// Số nước ứng viên ghi trong nhật ký (như MultiPV 8 của nhật ký tự đấu).
const int topUngVien = 8;

final int _pawn = _letters.indexOf('p') + 1;
final int _sergeant = _letters.indexOf('s') + 1;

/// Chỉ số policy -> nước UCI tuyệt đối. [den]: bên đi là Đen (khung nhìn lật hàng).
String nuocTuChiSo(int idx, bool den) {
  final t = idx ~/ (boardSize * boardSize);
  final frm = idx % (boardSize * boardSize);
  int rk = frm ~/ boardSize;
  final fl = frm % boardSize;
  String promo = '';
  int dx, dy;
  if (t < _slideTypes) {
    final d = _slideDirs[t ~/ 9];
    final k = t % 9 + 1;
    dx = d.$1 * k;
    dy = d.$2 * k;
  } else if (t < _camelBase) {
    final d = _knight[t - _knightBase];
    dx = d.$1;
    dy = d.$2;
  } else if (t < _promotionBase) {
    final d = _camel[t - _camelBase];
    dx = d.$1;
    dy = d.$2;
  } else {
    final p = t - _promotionBase;
    if (p >= _promo.length * 3) {
      throw FormatException('chỉ số nước $idx: loại $t không có');
    }
    promo = _promo[p ~/ 3];
    dx = p % 3 - 1;
    dy = 1;
  }
  int r2 = rk + dy;
  final f2 = fl + dx;
  if (r2 < 0 || r2 >= boardSize || f2 < 0 || f2 >= boardSize) {
    throw FormatException('chỉ số nước $idx: đích ra ngoài bàn');
  }
  if (den) {
    rk = boardSize - 1 - rk;
    r2 = boardSize - 1 - r2;
  }
  return '${String.fromCharCode(97 + fl)}${rk + 1}${String.fromCharCode(97 + f2)}${r2 + 1}$promo';
}

int _ctz(int w) {
  final low = w & -w;
  return low < 0 ? 63 : low.bitLength - 1;
}

/// Bàn cờ tuyệt đối của bản ghi: 100 số (ô = hàng * 10 + cột, hàng 0 = hàng 1), dương = Trắng, âm = Đen,
/// độ lớn = loại quân (1..12 theo thứ tự `pnrqkbmvyscg`).
Int8List banCo(V6Record rec) {
  final den = rec.sideToMove == 1;
  final b = Int8List(boardSize * boardSize);
  for (int j = 0; j < 2 * pieceKinds; j++) {
    final ta = j < pieceKinds; // quân của bên đi
    final kind = j % pieceKinds + 1;
    final trang = ta != den;
    final value = trang ? kind : -kind;
    for (int half = 0; half < 2; half++) {
      int w = rec.planes[2 * j + half];
      while (w != 0) {
        final s = _ctz(w) + 64 * half;
        w ^= w & -w;
        final rk = s ~/ 12; // khoảng cách giữa hai hàng trong mặt nạ là 12
        final fl = s % 12;
        if (rk >= boardSize || fl >= boardSize) continue;
        final rAbs = den ? boardSize - 1 - rk : rk;
        b[rAbs * boardSize + fl] = value;
      }
    }
  }
  return b;
}

/// Trường bố trí quân của FEN (hàng 10 -> hàng 1).
String datQuan(Int8List b) {
  final rows = <String>[];
  for (int r = boardSize - 1; r >= 0; r--) {
    final row = StringBuffer();
    int e = 0;
    for (int f = 0; f < boardSize; f++) {
      final pc = b[r * boardSize + f];
      if (pc == 0) {
        e++;
        continue;
      }
      if (e > 0) {
        row.write(e);
        e = 0;
      }
      final ch = _letters[pc.abs() - 1];
      row.write(pc > 0 ? ch.toUpperCase() : ch);
    }
    if (e > 0) row.write(e);
    rows.add(row.toString());
  }
  return rows.join('/');
}

/// Ô bắt qua đường thấp nhất của mặt nạ 128 bit (chỉ số bit), hoặc -1.
int _lowestBit(int lo, int hi) =>
    lo != 0 ? _ctz(lo) : (hi != 0 ? 64 + _ctz(hi) : -1);

/// FEN của bàn cờ [b] (xem [banCo]) và bản ghi [rec]: lượt, ô bắt qua đường, số chiếu còn lại (Trắng+Đen), luật 50.
String fenViTri(Int8List b, V6Record rec) {
  final den = rec.sideToMove == 1;
  final cu = rec.checksUs, ct = rec.checksThem; // "us" = bên đi
  final trangCk = den ? ct : cu;
  final denCk = den ? cu : ct;
  String ep = '-';
  final s = _lowestBit(rec.epLo, rec.epHi);
  if (s >= 0) {
    final rk = s ~/ 12, fl = s % 12;
    if (rk < boardSize && fl < boardSize) {
      ep = '${String.fromCharCode(97 + fl)}${den ? boardSize - rk : rk + 1}';
    }
  }
  return '${datQuan(b)} ${den ? 'b' : 'w'} - $ep $trangCk+$denCk ${rec.rule50} 1';
}

/// Các ô bắt qua đường (tuyệt đối) của bản ghi: mặt nạ nằm trong khung nhìn của bên đi.
Set<int> epO(V6Record rec) {
  final den = rec.sideToMove == 1;
  final out = <int>{};
  for (int half = 0; half < 2; half++) {
    int w = half == 0 ? rec.epLo : rec.epHi;
    while (w != 0) {
      final s = _ctz(w) + 64 * half;
      w ^= w & -w;
      final rk = s ~/ 12, fl = s % 12;
      if (rk < boardSize && fl < boardSize) {
        out.add((den ? boardSize - 1 - rk : rk) * boardSize + fl);
      }
    }
  }
  return out;
}

bool _isAlpha(int c) => (c >= 65 && c <= 90) || (c >= 97 && c <= 122);

/// 'e2e4' / 'a9a10q' -> (ô đi, ô đến, chữ phong hoặc '').
(int, int, String) tachNuoc(String uci) {
  int i = 1;
  while (!_isAlpha(uci.codeUnitAt(i))) {
    i++;
  }
  int j = i + 1;
  while (j < uci.length && !_isAlpha(uci.codeUnitAt(j))) {
    j++;
  }
  final frm =
      (int.parse(uci.substring(1, i)) - 1) * boardSize + uci.codeUnitAt(0) - 97;
  final to =
      (int.parse(uci.substring(i + 1, j)) - 1) * boardSize +
      uci.codeUnitAt(i) -
      97;
  return (frm, to, uci.substring(j));
}

/// null nếu bàn cờ [b1] đúng là [b0] sau nước [uci], ngược lại lời báo lỗi.
String? kiemNuoc(Int8List b0, Int8List b1, String uci) {
  final (frm, to, promo) = tachNuoc(uci);
  final pc = b0[frm];
  if (pc == 0) return '$uci: ô đi trống';
  final dau = pc > 0 ? 1 : -1;
  final muon = promo.isNotEmpty ? dau * (_letters.indexOf(promo) + 1) : pc;
  if (promo.isNotEmpty && pc.abs() != _pawn && pc.abs() != _sergeant) {
    return '$uci: phong cấp nhưng quân đi không phải Tốt / Sergeant';
  }
  if (b1[frm] != 0 && frm != to) return '$uci: ô đi còn quân sau nước';
  if (b1[to] != muon) return '$uci: ô đến có ${b1[to]}, đáng lẽ $muon';
  final khac = <int>[
    for (int s = 0; s < boardSize * boardSize; s++)
      if (s != frm && s != to && b0[s] != b1[s]) s,
  ];
  if (khac.length > 1 ||
      (khac.isNotEmpty &&
          !(b1[khac[0]] == 0 &&
              b0[khac[0]] * dau < 0 &&
              (b0[khac[0]].abs() == _pawn ||
                  b0[khac[0]].abs() == _sergeant)))) {
    return '$uci: bàn cờ đổi thêm ở [${khac.join(', ')}]';
  }
  return null;
}

/// Một ván đã giải mã.
class Van {
  final String ten;
  final List<V6Record> recs;
  final List<Int8List> boards;
  final List<bool> den;
  final String fen;
  final List<String> nuoc;

  Van._(this.ten, this.recs, this.boards, this.den, this.fen, this.nuoc);

  factory Van(List<V6Record> recs, String ten) {
    if (recs.isEmpty) throw FormatException('$ten: ván rỗng');
    final boards = [for (final r in recs) banCo(r)];
    final den = [for (final r in recs) r.sideToMove == 1];
    final fen = fenViTri(boards[0], recs[0]);
    final nuoc = [
      for (int k = 0; k < recs.length; k++)
        nuocTuChiSo(recs[k].playedIdx, den[k]),
    ];
    return Van._(ten, recs, boards, den, fen, nuoc);
  }

  /// Danh sách lỗi giải mã (rỗng = đúng): so từng nước với bàn cờ của bản ghi kế tiếp.
  List<String> kiem() {
    final loi = <String>[];
    for (int k = 0; k < recs.length - 1; k++) {
      if (den[k] == den[k + 1]) {
        loi.add('nước ${k + 1}: hai bản ghi liền cùng một bên đi');
      }
      final e = kiemNuoc(boards[k], boards[k + 1], nuoc[k]);
      if (e != null) loi.add('nước ${k + 1}: $e');
    }
    return loi;
  }

  /// Bàn cờ sau nước đi cuối (không có bản ghi cho thế này): áp nước cuối lên bản ghi cuối.
  /// Ăn qua đường: nước cuối của Tốt / Sergeant đáp xuống một ô bắt qua đường (ô trống) thì quân bị ăn là quân vừa
  /// bước đôi, đang đứng ở ô ĐẾN của nước ngay trước.
  Int8List banCuoi() {
    final b = Int8List.fromList(boards.last);
    final (frm, to, promo) = tachNuoc(nuoc.last);
    final pc = b[frm];
    final dau = pc > 0 ? 1 : -1;
    bool tot(int x) => x.abs() == _pawn || x.abs() == _sergeant;
    if (tot(pc) &&
        b[to] == 0 &&
        nuoc.length > 1 &&
        epO(recs.last).contains(to)) {
      final nan = tachNuoc(nuoc[nuoc.length - 2]).$2;
      if (b[nan] * dau < 0 && tot(b[nan])) b[nan] = 0;
    }
    b[to] = promo.isNotEmpty ? dau * (_letters.indexOf(promo) + 1) : pc;
    b[frm] = 0;
    return b;
  }

  /// 'Trắng thắng' / 'Đen thắng' / 'Hoà' theo bản ghi cuối (giá trị kết quả tính từ bên đi của bản ghi đó).
  String ketQua() {
    final r = recs.last;
    final q = r.resultQ, d = r.resultD;
    if (d > 0.5 || q.abs() < 0.5) return 'Hoà';
    final thangDi = q > 0;
    final trang = thangDi != den.last;
    return trang ? 'Trắng thắng' : 'Đen thắng';
  }
}

/// Làm tròn như `round()` của Python 3 (về số chẵn khi đúng giữa hai số nguyên). Chỉ dùng cho số >= 0.
int pyRound(double x) {
  final f = x.floorToDouble();
  final d = x - f;
  final i = f.toInt();
  if (d < 0.5) return i;
  if (d > 0.5) return i + 1;
  return i.isEven ? i : i + 1;
}

/// `format(v, '.4f')` của Python: đúng từng chữ số, làm tròn chẵn trên giá trị chính xác của số double.
/// (`toStringAsFixed(4)` của Dart làm tròn lên ở chỗ đúng giữa, vd 0.03125 -> 0.0313 thay vì 0.0312.)
String fmt4(double v) {
  if (v.isNaN) return 'nan';
  if (v.isInfinite) return v < 0 ? '-inf' : 'inf';
  final bd = ByteData(8)..setFloat64(0, v);
  final bits = bd.getInt64(0);
  final neg = bits < 0;
  final exp = (bits >>> 52) & 0x7FF;
  final frac = bits & 0xFFFFFFFFFFFFF;
  final BigInt m;
  final int e;
  if (exp == 0) {
    m = BigInt.from(frac);
    e = -1074;
  } else {
    m = BigInt.from(frac | (1 << 52));
    e = exp - 1075;
  }
  final num = m * BigInt.from(10000);
  BigInt q;
  if (e >= 0) {
    q = num << e;
  } else {
    final sh = -e;
    q = num >> sh;
    final r = num - (q << sh);
    final c = (r << 1).compareTo(BigInt.one << sh);
    if (c > 0 || (c == 0 && q.isOdd)) q += BigInt.one;
  }
  final s = q.toString().padLeft(5, '0');
  return '${neg ? '-' : ''}${s.substring(0, s.length - 4)}.${s.substring(s.length - 4)}';
}

(int, int, int) wdlPhanNghin(double q, double d) {
  final w = (1.0 - d + q) / 2.0;
  final l = (1.0 - d - q) / 2.0;
  int p(double x) {
    final r = pyRound(x * 1000);
    return r < 0 ? 0 : r;
  }

  return (p(w), p(d), p(l));
}

/// Văn bản nhật ký của ván: tiêu đề, rồi mỗi nửa nước một mục (xem `SelfPlayLog` trong GUI).
/// [tatCaNuocCoLuot]: liệt kê MỌI nước có lượt thăm (không chỉ [topUngVien] nước nhiều nhất). Mặc định false để
/// giống từng byte `xem_du_lieu.py`; app Android bật để xem đủ các nước. Q vẫn chỉ có cho nước đã đi và nước tốt
/// nhất: bản ghi huấn luyện không lưu Q của nước nào khác.
String nhatKy(Van van, {int? soVan, int? tong, bool tatCaNuocCoLuot = false}) {
  final nhan = soVan != null ? ' · ván $soVan/$tong' : '';
  final out = StringBuffer();
  out.write(
    '# dữ liệu huấn luyện · ${van.ten}$nhan · ${van.nuoc.length} nửa nước · ${van.ketQua()} '
    '(mỗi nước: số lượt thăm N của ${tatCaNuocCoLuot ? 'mọi nước có lượt thăm' : '$topUngVien nước nhiều nhất'}; '
    'Q chỉ có cho nước đã đi và nước tốt nhất)\n',
  );
  for (int k = 0; k < van.recs.length; k++) {
    final rec = van.recs[k];
    final den = van.den[k];
    out.write(
      '--- nửa nước ${k + 1} (${den ? 'đen' : 'trắng'} đi) → ${van.nuoc[k]}\n',
    );
    out.write('position fen ${van.fen}');
    if (k > 0) out.write(' moves ${van.nuoc.sublist(0, k).join(' ')}');
    out.write('\n');
    final visits = rec.visits;
    final (w, dr, l) = wdlPhanNghin(rec.rootQ, rec.rootD);
    final best = rec.bestIdx != 65535
        ? nuocTuChiSo(rec.bestIdx, den)
        : van.nuoc[k];
    out.write(
      '  depth 1 seldepth 1 multipv 1 wdl $w $dr $l nodes $visits nps 0 time 0 pv $best\n',
    );
    final tot = visits - 1 > 1 ? visits - 1 : 1;
    final ung = <_UngVien>[];
    for (int j = 0; j < rec.legalIdx.length; j++) {
      final i = rec.legalIdx[j];
      ung.add(_UngVien(pyRound(rec.legalPi[j] * tot), nuocTuChiSo(i, den), i));
    }
    ung.sort((a, b) {
      final c = b.n.compareTo(a.n);
      return c != 0 ? c : a.mv.compareTo(b.mv);
    });
    final daDi = rec.playedIdx;
    for (int j = 0; j < ung.length; j++) {
      final u = ung[j];
      final giu = tatCaNuocCoLuot ? (j < topUngVien || u.n > 0) : j < topUngVien;
      if (!(giu || u.i == daDi)) continue;
      String q = '';
      if (u.i == rec.playedIdx) {
        q = ' Q ${fmt4(rec.playedQ)}';
      } else if (u.i == rec.bestIdx) {
        q = ' Q ${fmt4(rec.bestQ)}';
      }
      out.write('    ${u.mv} N ${u.n}$q\n');
    }
  }
  return out.toString();
}

class _UngVien {
  final int n;
  final String mv;
  final int i;
  const _UngVien(this.n, this.mv, this.i);
}

/// Mã lý do kết thúc ván: checks | no_moves | rule50 | repetition | cut | adjudicated.
/// Cùng thứ tự kiểm với `PositionHistory::ComputeGameResult` (position.cc) và `_endReason` của GUI.
String lyDo(
  String fen,
  String ketQua,
  int soHopLe,
  int soNuoc,
  String ketQuaDuLieu,
) {
  final p = fen.trim().split(RegExp(r'\s+'));
  final ck = p[4].split('+');
  final a = int.parse(ck[0]), b = int.parse(ck[1]);
  final ruoc50 = int.parse(p[5]);
  if (ketQua == 'undecided') return ketQuaDuLieu == 'D' ? 'cut' : 'adjudicated';
  if (a <= 0 || b <= 0) return 'checks';
  if (ruoc50 >= 100) return ketQua == 'draw' ? 'rule50' : 'no_moves';
  if (ketQua == 'draw') return 'repetition';
  return soHopLe == 0 ? 'no_moves' : 'unknown';
}

const Map<String, String> maKetQua = {
  'Trắng thắng': 'W',
  'Đen thắng': 'B',
  'Hoà': 'D',
};

/// (quân Trắng, quân Đen) của trường bố trí quân của FEN.
(int, int) demQuan(String placement) {
  int t = 0, d = 0;
  for (final c in placement.runes) {
    if (c >= 65 && c <= 90) t++;
    if (c >= 97 && c <= 122) d++;
  }
  return (t, d);
}
