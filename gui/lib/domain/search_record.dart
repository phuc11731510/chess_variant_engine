/// Lần tìm kiếm của engine đã chọn một nửa nước (tự đấu): đúng các dòng engine in ra
/// cho nước đó — giống một mục trong nhật ký `tu_dau_log/tu_dau_*.txt`.
///
/// Mọi giá trị engine in (`score cp`, `wdl`, `Q`) tính từ phía BÊN ĐI nước này; đổi sang
/// phía Trắng (người xem) bằng [SearchCandidate.forWhite].
class SearchRecord {
  /// Số nửa nước đã đi trước lần tìm này (0 = nước đầu tiên của ván).
  final int ply;

  /// Nước engine trả về (`bestmove`).
  final String bestmove;

  /// Lệnh `position ...` đã gửi trước lần tìm (dựng lại được thế).
  final String positionCmd;

  /// Các dòng `info depth ... multipv k ...` (bỏ tiền tố "info "), theo thứ tự k tăng.
  final List<String> infos;

  /// Các dòng RootStats `<nước> N <lượt> P <prior> Q <giá trị> [Pnet <prior thô>]`, nhiều lượt
  /// nhất trước. P = prior lưu trong cây (tự đấu: đã trộn nhiễu Dirichlet); Pnet = prior của
  /// mạng trước nhiễu (engine từ 2026-10-29; nhật ký cũ không có).
  final List<String> stats;

  const SearchRecord({
    required this.ply,
    required this.bestmove,
    required this.positionCmd,
    required this.infos,
    required this.stats,
  });

  /// Tổng lượt tìm ở gốc, tốc độ, thời gian (lấy từ dòng info đầu; null nếu không có).
  int? get nodes => _intField(infos, 'nodes');
  int? get nps => _intField(infos, 'nps');
  int? get timeMs => _intField(infos, 'time');

  /// Các nước engine cân nhắc: theo thứ tự RootStats (nhiều lượt nhất trước); nhật ký cũ
  /// không có RootStats thì theo thứ tự multipv. Ghép dòng info cùng nước đầu PV.
  List<SearchCandidate> get candidates {
    final byMove = <String, _Info>{};
    final order = <String>[];
    for (final line in infos) {
      final i = _Info.parse(line);
      if (i == null || i.pv.isEmpty) continue;
      byMove.putIfAbsent(i.pv.first, () => i);
      order.add(i.pv.first);
    }
    final out = <SearchCandidate>[];
    final seen = <String>{};
    for (final s in stats) {
      final m = _stat.firstMatch(s.trim());
      if (m == null) continue;
      final mv = m.group(1)!;
      seen.add(mv);
      out.add(SearchCandidate._(
        move: mv,
        n: int.parse(m.group(2)!),
        p: double.parse(m.group(3)!),
        q: double.parse(m.group(4)!),
        pnet: m.group(5) == null ? null : double.parse(m.group(5)!),
        info: byMove[mv],
      ));
    }
    for (final mv in order) {
      if (seen.add(mv)) out.add(SearchCandidate._(move: mv, info: byMove[mv]));
    }
    return out;
  }

  /// Đúng đoạn nhật ký của nước này (như trong tệp `tu_dau_log`, bỏ dòng tiêu đề).
  String get rawText {
    final b = StringBuffer()..writeln(positionCmd);
    for (final l in infos) {
      b.writeln('  $l');
    }
    for (final s in stats) {
      b.writeln('    $s');
    }
    return b.toString().trimRight();
  }

  static final RegExp _stat = RegExp(
      r'^(\S+)\s+N\s+(\d+)\s+P\s+(-?[\d.]+)\s+Q\s+(-?[\d.]+)(?:\s+Pnet\s+(-?[\d.]+))?');
  static final RegExp _header = RegExp(r'^---\s*nửa nước\s+(\d+).*?→\s*(\S+)');

  static int? _intField(List<String> infos, String key) {
    if (infos.isEmpty) return null;
    final m = RegExp('(?:^| )$key (\\d+)').firstMatch(infos.first);
    return m == null ? null : int.parse(m.group(1)!);
  }

  /// Đọc mọi mục của một tệp nhật ký tự đấu: khoá = chỉ số nước (nửa nước k -> k - 1).
  static Map<int, SearchRecord> parseLog(String text) {
    final out = <int, SearchRecord>{};
    int? ply;
    String best = '', pos = '';
    var infos = <String>[], stats = <String>[];
    void flush() {
      if (ply != null) {
        out[ply] = SearchRecord(
          ply: ply,
          bestmove: best,
          positionCmd: pos,
          infos: infos,
          stats: stats,
        );
      }
    }

    for (final line in text.split(RegExp(r'\r?\n'))) {
      final h = _header.firstMatch(line);
      if (h != null) {
        flush();
        ply = int.parse(h.group(1)!) - 1;
        best = h.group(2)!;
        pos = '';
        infos = <String>[];
        stats = <String>[];
        continue;
      }
      if (ply == null) continue;
      final t = line.trim();
      if (t.startsWith('position ')) {
        pos = t;
      } else if (t.startsWith('depth ')) {
        infos.add(t);
      } else if (_stat.hasMatch(t)) {
        stats.add(t);
      }
    }
    flush();
    return out;
  }
}

/// Một nước ở gốc: số lượt tìm N, prior P, giá trị Q (RootStats) và dòng info cùng nước
/// (điểm cp, WDL phần nghìn, biến chính). Giá trị đều từ phía bên đi.
class SearchCandidate {
  final String move;
  final int? n;
  final double? p;

  /// Prior của mạng TRƯỚC nhiễu Dirichlet (null: nhật ký cũ).
  final double? pnet;
  final double? q;
  final int? cp;
  final int? win, draw, loss; // phần nghìn, phía bên đi
  final int? depth;
  final List<String> pv;

  SearchCandidate._({
    required this.move,
    this.n,
    this.p,
    this.pnet,
    this.q,
    _Info? info,
  })  : cp = info?.cp,
        win = info?.w,
        draw = info?.d,
        loss = info?.l,
        depth = info?.depth,
        pv = info?.pv ?? const [];

  /// Cùng nước, đổi giá trị sang phía TRẮNG: dương = Trắng có lợi. [whiteMoved] = Trắng là
  /// bên đi nước này (giá trị engine in theo phía bên đi).
  WhiteView forWhite(bool whiteMoved) => WhiteView(
        q: q == null ? null : (whiteMoved ? q! : -q!),
        cp: cp == null ? null : (whiteMoved ? cp! : -cp!),
        whiteWin: whiteMoved ? win : loss,
        draw: draw,
        blackWin: whiteMoved ? loss : win,
      );
}

/// Giá trị một nước nhìn từ phía Trắng.
class WhiteView {
  final double? q; // Q phía Trắng: +1 = Trắng thắng, -1 = Đen thắng
  final int? cp;
  final int? whiteWin, draw, blackWin; // phần nghìn
  const WhiteView({this.q, this.cp, this.whiteWin, this.draw, this.blackWin});
}

class _Info {
  final int? depth, cp, w, d, l;
  final List<String> pv;
  _Info(this.depth, this.cp, this.w, this.d, this.l, this.pv);

  static final RegExp _depth = RegExp(r'(?:^| )depth (\d+)');
  static final RegExp _cp = RegExp(r' score cp (-?\d+)');
  static final RegExp _wdl = RegExp(r' wdl (\d+) (\d+) (\d+)');
  static final RegExp _pv = RegExp(r' pv (.*)$');

  static _Info? parse(String line) {
    final pv = _pv.firstMatch(line);
    if (pv == null) return null;
    final wdl = _wdl.firstMatch(line);
    int? g(RegExp r) {
      final m = r.firstMatch(line);
      return m == null ? null : int.parse(m.group(1)!);
    }

    return _Info(
      g(_depth),
      g(_cp),
      wdl == null ? null : int.parse(wdl.group(1)!),
      wdl == null ? null : int.parse(wdl.group(2)!),
      wdl == null ? null : int.parse(wdl.group(3)!),
      pv.group(1)!.trim().split(RegExp(r'\s+')),
    );
  }
}
