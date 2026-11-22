import 'package:flutter/services.dart' show MethodChannel;

/// Những thứ chỉ Android biết (xem MainActivity.kt): thư mục riêng của app, thư mục Download và quyền "Truy cập mọi tệp".
class AndroidPaths {
  static const MethodChannel _ch = MethodChannel('fairyzero/paths');

  /// Thư mục external-files RIÊNG của app (`/storage/emulated/0/Android/data/<gói>/files`).
  static Future<String?> externalFilesDir() =>
      _ch.invokeMethod<String>('externalFilesDir');

  /// Thư mục Download chung (/storage/emulated/0/Download).
  static Future<String?> downloadDir() =>
      _ch.invokeMethod<String>('downloadDir');

  /// Đã được cấp quyền "Truy cập mọi tệp" (đọc được tệp của app khác trong bộ nhớ chung)?
  static Future<bool> hasAllFilesAccess() async =>
      (await _ch.invokeMethod<bool>('hasAllFilesAccess')) ?? false;

  /// Mở màn hình Cài đặt của quyền đó cho app này (người dùng gạt công tắc, rồi quay lại app).
  static Future<void> requestAllFilesAccess() =>
      _ch.invokeMethod<void>('requestAllFilesAccess');
}
