import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:isolate';
import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;

import '../platform/android_paths.dart';
import 'doi_pt.dart';

/// Release chứa `gen<N>.pt` của mọi đời (kho công khai: hỏi API không cần đăng nhập, 60 lần / giờ / địa chỉ IP).
const String kReleaseApi = 'https://api.github.com/repos/phuc11731510/chess_variant_engine';
const String kReleaseTag = 'NN_Model';

/// Một mạng đã tải và đổi xong, trong `<kho>/gen<N>/`.
class MangDaTai {
  final int gen;
  final String dir;
  final int bytes;
  final DateTime when;
  const MangDaTai(this.gen, this.dir, this.bytes, this.when);
  String get onnx => '$dir/$kTenKhung';
}

/// Một `gen<N>.pt` trên Release.
class MangTrenRelease {
  final int gen;
  final int bytes;
  final String url;
  final DateTime updated;
  const MangTrenRelease(this.gen, this.bytes, this.url, this.updated);
}

/// Tiến độ tải một mạng: [done]/[total] byte khi đang tải; [converting] khi đang đổi; [error] hoặc [finished] ở cuối.
class TaiTienDo {
  final int done, total;
  final bool converting, finished;
  final String? error;
  const TaiTienDo({this.done = 0, this.total = 0, this.converting = false, this.finished = false, this.error});
}

final RegExp _genDir = RegExp(r'^gen(\d+)$');
final RegExp _genPt = RegExp(r'^gen(\d+)\.pt$');

/// Kho mạng của app: thư mục `mang/` trong chỗ riêng của app (gỡ app là sạch). Mỗi mạng là một thư mục
/// `gen<N>/` gồm khung đồ thị (asset `assets/mang/khung.onnx`), tệp trọng số đổi từ `gen<N>.pt` và dấu `xong.txt`.
class KhoMang {
  final String root;
  KhoMang._(this.root);

  static KhoMang? _shared;

  /// Kho của app (một bản dùng chung); dọn các tệp dở dang của lần tải bị ngắt.
  static Future<KhoMang> open() async {
    if (_shared != null) return _shared!;
    final files = await AndroidPaths.externalFilesDir();
    if (files == null || files.isEmpty) throw const FileSystemException('Không xác định được thư mục riêng của app');
    final k = KhoMang._('$files/mang');
    Directory(k.root).createSync(recursive: true);
    for (final e in Directory(k.root).listSync(followLinks: false)) {
      final n = e.path.split('/').last;
      if (n.endsWith('.tai') || n.endsWith('.tam')) {
        try {
          e.deleteSync(recursive: true);
        } on FileSystemException {
          // để lần sau
        }
      }
    }
    return _shared = k;
  }

  /// Các mạng đã đổi xong, đời mới nhất trước.
  List<MangDaTai> local() {
    final out = <MangDaTai>[];
    final d = Directory(root);
    if (!d.existsSync()) return out;
    for (final e in d.listSync(followLinks: false)) {
      final m = _genDir.firstMatch(e.path.split('/').last);
      if (e is! Directory || m == null) continue;
      final done = File('${e.path}/$kTenXong');
      if (!done.existsSync()) continue;
      var bytes = 0;
      for (final f in e.listSync(followLinks: false)) {
        if (f is File) bytes += f.lengthSync();
      }
      out.add(MangDaTai(int.parse(m.group(1)!), e.path, bytes, done.lastModifiedSync()));
    }
    out.sort((a, b) => b.gen.compareTo(a.gen));
    return out;
  }

  MangDaTai? find(int gen) {
    for (final m in local()) {
      if (m.gen == gen) return m;
    }
    return null;
  }

  int get totalBytes => local().fold(0, (a, m) => a + m.bytes);

  void delete(int gen) {
    final d = Directory('$root/gen$gen');
    if (d.existsSync()) d.deleteSync(recursive: true);
  }

  /// Danh sách `gen<N>.pt` trên Release, đời mới nhất trước (hỏi theo trang 100 tệp).
  Future<List<MangTrenRelease>> remote() async {
    final c = HttpClient()..connectionTimeout = const Duration(seconds: 15);
    try {
      final rel = await _getJson(c, '$kReleaseApi/releases/tags/$kReleaseTag') as Map<String, dynamic>;
      final id = rel['id'];
      final out = <MangTrenRelease>[];
      for (var page = 1;; page++) {
        final list = await _getJson(c, '$kReleaseApi/releases/$id/assets?per_page=100&page=$page') as List;
        for (final a in list.cast<Map<String, dynamic>>()) {
          final m = _genPt.firstMatch(a['name'] as String);
          if (m == null || a['state'] != 'uploaded') continue;
          out.add(MangTrenRelease(int.parse(m.group(1)!), a['size'] as int, a['browser_download_url'] as String,
              DateTime.parse(a['updated_at'] as String).toLocal()));
        }
        if (list.length < 100) break;
      }
      out.sort((a, b) => b.gen.compareTo(a.gen));
      return out;
    } finally {
      c.close(force: true);
    }
  }

  static Future<Object?> _getJson(HttpClient c, String url) async {
    final req = await c.getUrl(Uri.parse(url));
    req.headers.set(HttpHeaders.acceptHeader, 'application/vnd.github+json');
    req.headers.set(HttpHeaders.userAgentHeader, 'fairyzero-xem');
    final res = await req.close().timeout(const Duration(seconds: 30));
    final body = await res.transform(utf8.decoder).join();
    if (res.statusCode == 403 || res.statusCode == 429) {
      throw HttpException('GitHub tạm chặn vì hỏi quá nhiều (60 lần / giờ); thử lại sau ít phút');
    }
    if (res.statusCode != 200) throw HttpException('GitHub trả mã ${res.statusCode}');
    return jsonDecode(body);
  }

  /// Tải `gen<N>.pt` rồi đổi thành thư mục mạng; xong thì xoá `.pt`. Huỷ bằng cách huỷ đăng ký luồng.
  Stream<TaiTienDo> download(MangTrenRelease r) {
    late StreamController<TaiTienDo> ctl;
    HttpClient? c;
    var cancelled = false;
    final pt = File('$root/gen${r.gen}.pt.tai');

    Future<void> run() async {
      try {
        c = HttpClient()..connectionTimeout = const Duration(seconds: 20);
        final req = await c!.getUrl(Uri.parse(r.url)); // GitHub chuyển hướng sang máy chứa tệp: HttpClient tự theo
        req.headers.set(HttpHeaders.userAgentHeader, 'fairyzero-xem');
        final res = await req.close();
        if (res.statusCode != 200) throw HttpException('tải trả mã ${res.statusCode}');
        final total = res.contentLength > 0 ? res.contentLength : r.bytes;
        final sink = pt.openWrite();
        var done = 0, last = 0;
        try {
          await for (final chunk in res) {
            if (cancelled) throw const _Huy();
            sink.add(chunk);
            done += chunk.length;
            if (done - last >= 1 << 18 || done == total) {
              last = done;
              ctl.add(TaiTienDo(done: done, total: total));
            }
          }
        } finally {
          await sink.close();
        }
        if (done != r.bytes) throw HttpException('tải được $done byte, Release ghi ${r.bytes} byte');
        ctl.add(TaiTienDo(done: done, total: total, converting: true));
        final khung = (await rootBundle.load('assets/mang/$kTenKhung')).buffer.asUint8List();
        final bang = await rootBundle.loadString('assets/mang/bang_ghep.json');
        final src = pt.path, dst = '$root/gen${r.gen}';
        await doiPtNen(ptPath: src, dich: dst, khung: khung, bangGhepJson: bang);
        ctl.add(const TaiTienDo(finished: true));
      } on _Huy {
        // người dùng huỷ
      } catch (e) {
        if (!cancelled) ctl.add(TaiTienDo(error: '$e'));
      } finally {
        c?.close(force: true);
        try {
          if (pt.existsSync()) pt.deleteSync();
        } on FileSystemException {
          // open() dọn lần sau
        }
        await ctl.close();
      }
    }

    ctl = StreamController<TaiTienDo>(
      onListen: run,
      onCancel: () {
        cancelled = true;
        c?.close(force: true);
      },
    );
    return ctl.stream;
  }
}

/// [doiPt] trong một isolate riêng (đọc 20 MB và chép byte không làm khựng giao diện). Hàm đứng riêng để bao đóng gửi
/// sang isolate chỉ mang các tham số: một bao đóng viết bên trong [KhoMang.download] mang theo cả ngữ cảnh của hàm đó
/// (StreamController, HttpClient), là những thứ không gửi sang isolate được.
Future<void> doiPtNen({required String ptPath, required String dich, required Uint8List khung, required String bangGhepJson}) =>
    Isolate.run(() => doiPt(ptPath: ptPath, dich: dich, khung: khung, bangGhepJson: bangGhepJson));

class _Huy implements Exception {
  const _Huy();
}

/// "20,3 MB"
String coTep(int bytes) {
  if (bytes >= 1 << 30) return '${(bytes / (1 << 30)).toStringAsFixed(2).replaceAll('.', ',')} GB';
  return '${(bytes / (1 << 20)).toStringAsFixed(1).replaceAll('.', ',')} MB';
}
