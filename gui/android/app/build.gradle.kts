plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "vn.fairyzero.xem"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // Xem ván của dữ liệu huấn luyện FairyZero trên Android.
        applicationId = "vn.fairyzero.xem"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        // minSdk 24: engine .so cross-compile voi aarch64-linux-android24-clang;
        // libonnxruntime.so toi thieu API21 -> 24 la an toan.
        minSdk = maxOf(24, flutter.minSdkVersion)
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        // Chi co .so arm64-v8a (jniLibs); gioi han ABI cho khop & APK gon.
        ndk {
            abiFilters += "arm64-v8a"
        }
    }

    // Chỉ arm64 (ndk.abiFilters không lọc .so của các gói Maven như LiteRT): bỏ bản armeabi-v7a / x86 / x86_64 của chúng.
    packaging {
        jniLibs {
            excludes += listOf("lib/armeabi-v7a/**", "lib/x86/**", "lib/x86_64/**")
        }
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}

dependencies {
    // Mạng chạy trên GPU (engine dlopen libtensorflowlite_jni.so + libtensorflowlite_gpu_jni.so, provider "gpu"): LiteRT 1.x
    // = TensorFlow Lite đổi tên, còn C API và GPU delegate cổ điển (LiteRT 2.x đổi sang API khác).
    implementation("com.google.ai.edge.litert:litert:1.4.2")
    implementation("com.google.ai.edge.litert:litert-gpu:1.4.2")
}
