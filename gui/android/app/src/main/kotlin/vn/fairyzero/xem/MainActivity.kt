package vn.fairyzero.xem

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/// MethodChannel nhỏ để Dart hỏi / xin những thứ chỉ Android biết:
///  - `externalFilesDir`: thư mục external-files RIÊNG của app (/storage/emulated/0/Android/data/<pkg>/files): app luôn
///    đọc / ghi được, `adb push` vào đây được; nơi lưu đệm chỉ mục dữ liệu (và model.onnx khi chơi với máy).
///  - `downloadDir`: thư mục Download chung (dữ liệu huấn luyện của vòng lặp Termux nằm ở Download/FairyZero).
///  - `hasAllFilesAccess` / `requestAllFilesAccess`: quyền "Truy cập mọi tệp" (MANAGE_EXTERNAL_STORAGE). Từ Android 11,
///    app không đọc được tệp .xz do Termux ghi trong Download nếu thiếu quyền này; người dùng bật MỘT LẦN trong Cài đặt.
/// Tự viết tại đây (không phải pub plugin) nên build Android trên Windows không đòi symlink / Developer Mode.
class MainActivity : FlutterActivity() {
    private val channelName = "fairyzero/paths"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "externalFilesDir" -> result.success(getExternalFilesDir(null)?.absolutePath)
                    "downloadDir" -> result.success(
                        Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).absolutePath
                    )
                    "hasAllFilesAccess" -> result.success(
                        Build.VERSION.SDK_INT < Build.VERSION_CODES.R || Environment.isExternalStorageManager()
                    )
                    "requestAllFilesAccess" -> {
                        openAllFilesSettings()
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun openAllFilesSettings() {
        try {
            startActivity(
                Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION, Uri.parse("package:$packageName"))
            )
        } catch (e: Exception) {
            startActivity(Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION))
        }
    }
}
