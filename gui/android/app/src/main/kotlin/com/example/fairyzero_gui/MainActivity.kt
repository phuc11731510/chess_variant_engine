package com.example.fairyzero_gui

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/// MethodChannel nhỏ để Dart hỏi đường dẫn hệ thống mà chỉ Android biết.
/// `externalFilesDir` = thư mục external-files RIÊNG của app
/// (/storage/emulated/0/Android/data/<pkg>/files): app luôn đọc/ghi được, và
/// `adb push` được vào đây mà không cần root — nơi đặt model.onnx (M4).
/// Tự viết tại đây (không phải pub plugin) nên build Android trên Windows host
/// không kích hoạt yêu cầu symlink/Developer Mode của Flutter.
class MainActivity : FlutterActivity() {
    private val channelName = "fairyzero/paths"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "externalFilesDir" -> result.success(getExternalFilesDir(null)?.absolutePath)
                    else -> result.notImplemented()
                }
            }
    }
}
