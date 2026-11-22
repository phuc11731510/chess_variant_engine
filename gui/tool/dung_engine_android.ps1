# Dựng lại libfairyzero.so (engine HIỆN TẠI, arm64) bằng Android NDK và chép vào gui/android/app/src/main/jniLibs/arm64-v8a.
# Chạy MỖI KHI đổi luật / bộ quân / mã engine (app Android dùng engine trong tiến trình để kiểm nước đi và dựng FEN,
# nên bản cũ = luật cũ). Các tệp .so không nằm trong git (*.so bị bỏ qua) nên tệp này là cách dựng lại chúng.
#
#   powershell -ExecutionPolicy Bypass -File gui\tool\dung_engine_android.ps1
#   flutter build apk --release --target-platform android-arm64     (trong thư mục gui)
#
# Cần: Android NDK 28.2.13676358 (đường dẫn trong custom_engine/cross/aarch64-linux-android.txt), meson + ninja
# (C:\msys64\ucrt64\bin), custom_engine/third_party/onnxruntime-android-1.18.0 (libonnxruntime.so + include).
$ErrorActionPreference = 'Stop'
$env:Path = 'C:\msys64\ucrt64\bin;' + $env:Path
$gui = Resolve-Path (Join-Path $PSScriptRoot '..')
$ce = Resolve-Path (Join-Path $gui '..\custom_engine')
$jni = Join-Path $gui 'android\app\src\main\jniLibs\arm64-v8a'
New-Item -ItemType Directory -Force $jni | Out-Null
Push-Location $ce
try {
    if (-not (Test-Path 'build-android\build.ninja')) {
        meson setup build-android --cross-file cross/aarch64-linux-android.txt --buildtype=release `
            -Donnxruntime_dir=third_party/onnxruntime-android-1.18.0
        if ($LASTEXITCODE -ne 0) { throw 'meson setup lỗi' }
    }
    ninja -C build-android libfairyzero.so
    if ($LASTEXITCODE -ne 0) { throw 'ninja lỗi' }
} finally {
    Pop-Location
}
Copy-Item (Join-Path $ce 'build-android\libfairyzero.so') (Join-Path $jni 'libfairyzero.so') -Force
$ort = Join-Path $ce 'third_party\onnxruntime-android-1.18.0\lib\libonnxruntime.so'
if (-not (Test-Path (Join-Path $jni 'libonnxruntime.so'))) { Copy-Item $ort $jni }
$ndk = 'C:\Users\7\AppData\Local\Android\Sdk\ndk\28.2.13676358\toolchains\llvm\prebuilt\windows-x86_64\sysroot\usr\lib\aarch64-linux-android\libc++_shared.so'
if (-not (Test-Path (Join-Path $jni 'libc++_shared.so'))) { Copy-Item $ndk $jni }
Get-ChildItem $jni | Format-Table Name, Length, LastWriteTime
