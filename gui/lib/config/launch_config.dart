/// Cấu hình khởi động, đọc MỘT LẦN từ cờ lệnh terminal lúc mở app (bất biến).
///
/// M0: mới chỉ parse + in ra. Các mốc sau sẽ truyền object này xuống lớp nối
/// engine (EngineService) và lớp vẽ bàn cờ. Thêm tính năng sau này = thêm
/// trường vào đây, không phá cấu trúc.
///
/// Cờ lệnh hỗ trợ (M0):
/// ```
///   --engine <path>     đường dẫn custom_engine.exe        (mặc định engine/custom_engine.exe)
///   --model <onnx>      file trọng số .onnx                (mặc định: chưa đặt -> engine tự lo)
///   --provider <p>      cpu | dml | cuda                   (mặc định cpu)
///   --movetime <ms>     thời gian máy nghĩ mỗi nước (ms)   (mặc định 5000)
///   --visits <N>        hoặc số visits cố định mỗi nước    (ưu tiên hơn movetime nếu có)
///   --black             người chơi cầm Đen (lật bàn)       (mặc định cầm Trắng)
///   --white             người chơi cầm Trắng               (mặc định)
///   --start-fen <FEN>   thế cờ bắt đầu tuỳ chọn            (mặc định: startpos của biến thể)
/// ```
class LaunchConfig {
  /// Đường dẫn tới engine UCI (custom_engine.exe, chạy với --uci-nn).
  final String enginePath;

  /// File .onnx. Null = để engine dùng mặc định của nó.
  final String? modelPath;

  /// 'cpu' | 'dml' | 'cuda'. Quyết định engine lượng giá bằng CPU hay GPU.
  final String provider;

  /// Thời gian máy nghĩ mỗi nước (ms). Null nếu dùng [visits].
  final int? movetimeMs;

  /// Số visits (nodes) cố định mỗi nước. Null nếu dùng [movetimeMs].
  final int? visits;

  /// true = người cầm Trắng (quân Trắng ở đáy). false = cầm Đen (lật bàn).
  final bool humanPlaysWhite;

  /// FEN bắt đầu tuỳ chọn. Null = dùng startpos mặc định của biến thể.
  final String? startFen;

  const LaunchConfig({
    required this.enginePath,
    this.modelPath,
    this.provider = 'cpu',
    this.movetimeMs,
    this.visits,
    this.humanPlaysWhite = true,
    this.startFen,
  });

  static const String defaultEngine = 'engine/custom_engine.exe';
  static const int defaultMovetimeMs = 5000;
  static const Set<String> validProviders = {'cpu', 'dml', 'cuda'};

  /// Parse danh sách đối số dòng lệnh thành [LaunchConfig]. Đối số lạ bị bỏ qua
  /// (vd wrapper của `flutter run --dart-entrypoint-args`).
  factory LaunchConfig.fromArgs(List<String> args) {
    String engine = defaultEngine;
    String? model;
    String provider = 'cpu';
    int? movetime;
    int? visits;
    bool humanWhite = true;
    String? fen;

    String? valueAfter(int i) => (i + 1 < args.length) ? args[i + 1] : null;

    for (int i = 0; i < args.length; i++) {
      switch (args[i]) {
        case '--engine':
          final v = valueAfter(i);
          if (v != null) { engine = v; i++; }
          break;
        case '--model':
          final v = valueAfter(i);
          if (v != null) { model = v; i++; }
          break;
        case '--provider':
          final v = valueAfter(i);
          if (v != null) { provider = v.toLowerCase(); i++; }
          break;
        case '--movetime':
          final v = valueAfter(i);
          if (v != null) { movetime = int.tryParse(v); i++; }
          break;
        case '--visits':
          final v = valueAfter(i);
          if (v != null) { visits = int.tryParse(v); i++; }
          break;
        case '--black':
          humanWhite = false;
          break;
        case '--white':
          humanWhite = true;
          break;
        case '--start-fen':
          final v = valueAfter(i);
          if (v != null) { fen = v; i++; }
          break;
        default:
          break; // bỏ qua đối số không nhận diện
      }
    }

    if (!validProviders.contains(provider)) provider = 'cpu';
    // Nếu không đặt cả visits lẫn movetime -> dùng movetime mặc định.
    if (movetime == null && visits == null) movetime = defaultMovetimeMs;

    return LaunchConfig(
      enginePath: engine,
      modelPath: model,
      provider: provider,
      movetimeMs: movetime,
      visits: visits,
      humanPlaysWhite: humanWhite,
      startFen: fen,
    );
  }

  /// Mô tả ngắn gọn cách giới hạn suy nghĩ của máy (để hiển thị/log).
  String get thinkSummary => visits != null
      ? '$visits visits/nuoc'
      : '${movetimeMs ?? defaultMovetimeMs} ms/nuoc';

  @override
  String toString() => [
        'LaunchConfig:',
        '  engine   = $enginePath',
        '  model    = ${modelPath ?? "(chua dat --model)"}',
        '  provider = $provider',
        '  think    = $thinkSummary',
        '  human    = ${humanPlaysWhite ? "White (quan o day)" : "Black (lat ban)"}',
        '  startFen = ${startFen ?? "(startpos mac dinh)"}',
      ].join('\n');
}
