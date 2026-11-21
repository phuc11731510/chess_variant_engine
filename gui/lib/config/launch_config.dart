import 'dart:io';

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
///   --start-fen-file <tệp>  như --start-fen nhưng đọc FEN (dòng đầu tiên không rỗng, không bắt đầu bằng #) từ tệp,
///                       vd thế ngẫu nhiên do custom_engine/python/sinh_the_khoi_dau.py --n 1 sinh ra
///   --self-play         máy tự đấu cả hai bên (người chỉ xem; Space = tạm dừng/tiếp;
///                       xem lại nước đã đi: ← → / lăn chuột / bấm nước ở thanh dưới bàn,
///                       Home = về đầu, End = về nước mới nhất, PageUp/PageDown = 10 nước)
///   --replay <tệp>      chỉ XEM LẠI một ván (không chơi, không tìm kiếm): tệp nhật ký tu_dau_log/*.txt
///                       hoặc tệp các nước UCI. Space = tự chạy, phím/lăn chuột/bấm nước như tự đấu.
///                       (đường dẫn không được có khoảng trắng)
///   --replay-dir <thư mục>  XEM LẠI nhiều ván: thư mục có chi_muc.tsv + van_NNNN.txt (xem_du_lieu.py --xuat);
///                       hiện bảng chọn ván (lọc theo kết quả / lý do / số quân còn lại), bấm một dòng để xem ván đó
///   --replay-game <N>   (với --replay-dir) ván mở đầu có `so` = N (mặc định: ván đầu bảng)
///   --temperature <T>   (tự đấu) nhiệt độ chọn nước (mặc định 0.5 như sinh dữ liệu)
///   --temp-cutoff <N>   (tự đấu) chỉ dùng nhiệt độ trong N nửa nước đầu; 0 = cả ván (mặc định 0 như sinh dữ liệu)
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

  /// (Gỡ lỗi) Tự chơi một nước của NGƯỜI ngay khi mở app, vd "--demo-move b3b4".
  final String? demoMove;

  /// Máy tự đấu cả hai bên; người chỉ xem.
  final bool selfPlay;

  /// Chỉ xem lại ván đã lưu trong tệp này (null = không phải chế độ xem lại).
  final String? replayPath;

  /// Thư mục nhiều ván để xem lại ([ReplayLibrary]); [replayPath] là ván đang mở trong thư mục đó.
  final String? replayDir;

  /// Ván mở đầu trong [replayDir] (số thứ tự trong chi_muc.tsv); null = ván đầu bảng.
  final int? replayGame;

  /// Tự đấu: ghi đè Temperature (‰, engine nhận số nghìn) và TempCutoffPly
  /// của [trainingUciOptions]. Null = giữ như sinh dữ liệu.
  final int? temperaturePermille;
  final int? tempCutoffPly;

  const LaunchConfig({
    required this.enginePath,
    this.modelPath,
    this.provider = 'cpu',
    this.movetimeMs,
    this.visits,
    this.humanPlaysWhite = true,
    this.startFen,
    this.demoMove,
    this.selfPlay = false,
    this.replayPath,
    this.replayDir,
    this.replayGame,
    this.temperaturePermille,
    this.tempCutoffPly,
  });

  /// [trainingUciOptions] sau khi áp --temperature / --temp-cutoff.
  List<(String, String)> get selfPlayUciOptions => [
    for (final (name, value) in trainingUciOptions)
      if (name == 'Temperature' && temperaturePermille != null)
        (name, '$temperaturePermille')
      else if (name == 'TempCutoffPly' && tempCutoffPly != null)
        (name, '$tempCutoffPly')
      else
        (name, value),
  ];

  /// --self-play: cùng tham số tìm kiếm với lúc SINH DỮ LIỆU HUẤN LUYỆN (ô 04 +
  /// mặc định self-play của engine, src/app/selfplay_mode.cc), chỉ khác giới hạn
  /// suy nghĩ (--movetime thay cho 800 lượt tìm). Gửi bằng `setoption` trước isready.
  static const List<(String, String)> trainingUciOptions = [
    ('PolicySoftmaxTemp', '1.0'), // --policy-temp 1.0 (UCI mặc định 1.359)
    // Chọn nước theo trọng số (số lượt thăm)^(1/T) với T = 0.5, SUỐT ván (không còn giai đoạn
    // mở đầu / nước tốt nhất): đúng như sinh dữ liệu (--temperature 0.5).
    ('Temperature', '500'),
    ('TempCutoffPly', '0'), // 0 = áp nhiệt độ cả ván
    (
      'ReuseTree',
      'false',
    ), // cây mới mỗi nước (để nhiễu gốc đúng như self-play)
    ('noise-epsilon', '0.25'), // nhiễu Dirichlet ở gốc (tìm kiếm đầy đủ 800 lượt)
    ('noise-alpha', '0.15'), // --noise-alpha 0.15
    ('cpuct', '1.5'), // cố định 1.5 cho tìm kiếm đầy đủ (selfplay_mode.cc)
    ('cpuct-factor', '0'),
    ('fpu-value', '0'),
    ('two-fold-draws', 'false'),
    ('sticky-endgames', 'false'),
    ('task-workers', '0'),
    ('max-prefetch', '0'),
    ('minibatch-size', '32'),
    ('nn-cache-size', '2000000'),
  ];

  /// Self-play cắt ván ở 400 nửa nước = hoà (--max-moves 400).
  static const int selfPlayMaxPlies = 400;

  static const String defaultEngine = 'engine/custom_engine.exe';
  static const int defaultMovetimeMs = 5000;
  static const Set<String> validProviders = {'cpu', 'dml', 'cuda'};

  /// Parse danh sách đối số dòng lệnh thành [LaunchConfig]. Đối số lạ bị bỏ qua
  /// (vd wrapper của `flutter run --dart-entrypoint-args`).
  factory LaunchConfig.fromArgs(List<String> rawArgs) {
    // `flutter run --dart-entrypoint-args "a b c"` gửi cả cụm là MỘT phần tử;
    // tách theo khoảng trắng để cả hai cách truyền đều chạy. (Đường dẫn CHỨA
    // khoảng trắng thì hãy chạy thẳng exe đã build thay vì qua flutter run.)
    // Chỉ tách phần tử bắt đầu bằng `--` (cả cụm cờ của flutter run); một giá trị đứng riêng như FEN
    // (có khoảng trắng, đã bọc nháy ở dòng lệnh) phải giữ nguyên.
    final args = <String>[];
    for (final a in rawArgs) {
      if (a.trimLeft().startsWith('--')) {
        args.addAll(a.split(RegExp(r'\s+')).where((s) => s.isNotEmpty));
      } else if (a.trim().isNotEmpty) {
        args.add(a.trim());
      }
    }

    String engine = defaultEngine;
    String? model;
    String provider = 'cpu';
    int? movetime;
    int? visits;
    bool humanWhite = true;
    String? fen;
    String? demo;
    bool selfPlay = false;
    String? replayPath;
    String? replayDir;
    int? replayGame;
    String? fenFile;
    int? tempPermille;
    int? tempCutoff;

    String? valueAfter(int i) => (i + 1 < args.length) ? args[i + 1] : null;

    for (int i = 0; i < args.length; i++) {
      switch (args[i]) {
        case '--engine':
          final v = valueAfter(i);
          if (v != null) {
            engine = v;
            i++;
          }
          break;
        case '--model':
          final v = valueAfter(i);
          if (v != null) {
            model = v;
            i++;
          }
          break;
        case '--provider':
          final v = valueAfter(i);
          if (v != null) {
            provider = v.toLowerCase();
            i++;
          }
          break;
        case '--movetime':
          final v = valueAfter(i);
          if (v != null) {
            movetime = int.tryParse(v);
            i++;
          }
          break;
        case '--visits':
          final v = valueAfter(i);
          if (v != null) {
            visits = int.tryParse(v);
            i++;
          }
          break;
        case '--black':
          humanWhite = false;
          break;
        case '--white':
          humanWhite = true;
          break;
        case '--start-fen':
          final v = valueAfter(i);
          if (v != null) {
            fen = v;
            i++;
          }
          break;
        case '--start-fen-file':
          final v = valueAfter(i);
          if (v != null) {
            fenFile = v;
            i++;
          }
          break;
        case '--replay-dir':
          final v = valueAfter(i);
          if (v != null) {
            replayDir = v;
            i++;
          }
          break;
        case '--replay-game':
          final v = valueAfter(i);
          if (v != null) {
            replayGame = int.tryParse(v);
            i++;
          }
          break;
        case '--self-play':
          selfPlay = true;
          break;
        case '--replay':
          final v = valueAfter(i);
          if (v != null) {
            replayPath = v;
            i++;
          }
          break;
        case '--temperature':
          final v = valueAfter(i);
          if (v != null) {
            final t = double.tryParse(v);
            if (t != null && t >= 0) tempPermille = (t * 1000).round();
            i++;
          }
          break;
        case '--temp-cutoff':
          final v = valueAfter(i);
          if (v != null) {
            final n = int.tryParse(v);
            if (n != null && n >= 0) tempCutoff = n;
            i++;
          }
          break;
        case '--demo-move':
          final v = valueAfter(i);
          if (v != null) {
            demo = v;
            i++;
          }
          break;
        default:
          break; // bỏ qua đối số không nhận diện
      }
    }

    if (fen == null && fenFile != null) fen = _readFenFile(fenFile);
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
      demoMove: demo,
      selfPlay: selfPlay,
      replayPath: replayPath,
      replayDir: replayDir,
      replayGame: replayGame,
      temperaturePermille: tempPermille,
      tempCutoffPly: tempCutoff,
    );
  }

  /// Dòng FEN đầu tiên (không rỗng, không bắt đầu bằng `#`) của [path]; null nếu không đọc được.
  static String? _readFenFile(String path) {
    try {
      for (final l in File(path).readAsLinesSync()) {
        final t = l.trim();
        if (t.isNotEmpty && !t.startsWith('#')) return t;
      }
    } catch (_) {}
    return null;
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
    '  human    = ${selfPlay
        ? "(may tu dau ca hai ben)"
        : humanPlaysWhite
        ? "White (quan o day)"
        : "Black (lat ban)"}',
    '  startFen = ${startFen ?? "(startpos mac dinh)"}',
    if (replayDir != null) '  replayDir = $replayDir (game ${replayGame ?? "dau bang"})',
  ].join('\n');
}
