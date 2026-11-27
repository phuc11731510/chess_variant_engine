import 'package:flutter/foundation.dart';

import '../engine/phan_tich.dart';
import '../mang/kho_mang.dart';

/// Trạng thái phân tích của màn xem ván (Android): mạng đang chọn trong Kho mạng, engine phân tích của mạng đó, và prior
/// thô của thế mà bảng tìm kiếm đang nói tới (chỉ tính khi bật, chỉ cho thế đang xem; thế đã tính thì giữ lại).
class PhanTichCtl extends ChangeNotifier {
  /// Đời mạng đã sinh dữ liệu đang xem (null nếu không biết): mạng mặc định khi đã tải.
  final int? dataGen;
  PhanTichCtl({this.dataGen});

  KhoMang? _kho;
  List<MangDaTai> nets = [];
  int? netGen;
  PhanTich? _pt;
  int _ruleSet = 0;

  bool priorOn = false;
  bool priorBusy = false;
  String? priorError;
  final Map<String, DanhGiaTho?> _cache = {};
  String? _wantKey;
  String? _errKey; // thế vừa tính lỗi: không tự thử lại (bật lại nút để thử)
  bool _disposed = false;

  /// Engine đang chạy mạng bằng 'GPU' / 'CPU' (null khi chưa khởi động).
  String? get dangDung => _pt?.dangDung;

  /// Prior thô của thế [key] (đã tính), hoặc null.
  DanhGiaTho? rawFor(String? key) => key == null ? null : _cache[key];

  Future<void> init() async {
    try {
      _kho = await KhoMang.open();
    } catch (_) {
      return;
    }
    refreshNets(keepChoice: false);
  }

  /// Đọc lại danh sách mạng đã tải (sau khi quay về từ màn Kho mạng).
  void refreshNets({bool keepChoice = true}) {
    final k = _kho;
    if (k == null) return;
    nets = k.local();
    final have = {for (final m in nets) m.gen};
    if (!keepChoice || netGen == null || !have.contains(netGen)) {
      final want = dataGen != null && have.contains(dataGen) ? dataGen : (nets.isEmpty ? null : nets.first.gen);
      if (want != netGen) _switch(want);
    }
    _notify();
  }

  void chooseNet(int gen) {
    if (gen == netGen) return;
    _switch(gen);
    _notify();
  }

  void _switch(int? gen) {
    _pt?.dispose();
    _pt = null;
    netGen = gen;
    _cache.clear();
    priorError = null;
    _errKey = null;
  }

  /// Engine phân tích của mạng đang chọn, cho bộ luật [ruleSet] (dựng khi cần; đổi bộ luật thì dựng lại).
  PhanTich? engineFor(int ruleSet) {
    final gen = netGen;
    if (gen == null) return null;
    final m = _kho?.find(gen);
    if (m == null) return null;
    if (_pt != null && _ruleSet != ruleSet) {
      _pt!.dispose();
      _pt = null;
      _cache.clear();
    }
    _ruleSet = ruleSet;
    final kho = _kho!;
    return _pt ??= PhanTich(gen: gen, onnxPath: m.onnx, ruleSet: ruleSet, gpuModel: () => kho.ensureGpu(m));
  }

  void togglePrior() {
    priorOn = !priorOn;
    priorError = null;
    _errKey = null;
    _notify();
  }

  /// Bảng tìm kiếm đang nói tới thế sau [moves] (khoá [key]): nếu đang bật prior thô và chưa có thì tính.
  Future<void> want(String key, String startFen, List<String> moves, int ruleSet) async {
    _wantKey = key;
    if (!priorOn || _cache.containsKey(key) || priorBusy || key == _errKey) return;
    final pt = engineFor(ruleSet);
    if (pt == null) return;
    priorBusy = true;
    priorError = null;
    _notify();
    try {
      final r = await pt.danhGia(startFen, moves);
      _cache[key] = r;
      _errKey = null;
    } catch (e) {
      priorError = '$e';
      _errKey = key;
    } finally {
      priorBusy = false;
      _notify();
    }
    // Người xem đã sang thế khác trong lúc tính: tính tiếp thế mới nhất họ đang xem (bỏ qua các thế lướt qua).
    final now = _wantKey;
    if (now != null && now != key && priorOn && !_cache.containsKey(now)) _pendingAgain?.call();
  }

  /// Gọi lại [want] cho thế đang xem (do màn hình gắn vào, vì chỉ nó biết thế đang xem).
  VoidCallback? _pendingAgain;
  set onNeedRefresh(VoidCallback? f) => _pendingAgain = f;

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _pt?.dispose();
    _pt = null;
    super.dispose();
  }
}
