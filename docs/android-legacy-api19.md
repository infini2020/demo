# Android 4.4.2（API 19 / armeabi-v7a）适配指南

本文档说明 NipaPlay-Reload 面向 Android 4.4.2 的 **legacy 分支构建**。
该适配是"尽力而为"的实验性支持，主线构建（minSdk 26）不受影响。

## 为什么需要独立的 legacy 构建

当前主线工具链均不再支持 API 19，因此 4.4 构建必须整体降级：

| 组件 | 主线 | Legacy（API 19） | 原因 |
|---|---|---|---|
| Flutter | 3.47.0-0.3.pre | **3.19.6** | Flutter 3.22 起引擎 minSdk 升至 21；3.19 是最后支持 API 19 的稳定版 |
| Dart SDK | ^3.5.3 | **3.3.4**（随 Flutter 3.19.6） | Flutter 3.19.6 自带 Dart 3.3.4（非 3.4.0） |
| NDK | 29.0.14206865 | **r25b (25.2.9519653)** | NDK r26 起 minSdk 21；r25b 是最后一个支持 API 19 的 NDK |
| Kotlin | 2.3.21 | **1.9.24** | Kotlin 2.1+ stdlib 最低 API 23 |
| minSdk | 26 | **19** | — |
| targetSdk | flutter 默认 | **28** | 4.4 设备无意义追求高 target；28 兼容旧库与 cleartext 默认策略 |
| ABI | 全架构 | **armeabi-v7a** | 4.4 时代设备均为 arm32 |

## 如何触发

### 方式一：GitHub Actions（推荐）

手动触发 `.github/workflows/build-android-legacy.yml`（workflow_dispatch），
产物为 `NipaPlay-<version>-Android-4.4-legacy-armeabi-v7a.apk`。

### 方式二：本地构建

```bash
# 前置：Flutter 3.19.6 stable、JDK 17、Android SDK（platform-tools、
#        ndk;25.2.9519653、cmake;3.22.1、build-tools;29.0.3）
export NIPAPLAY_LEGACY=1
rm -f pubspec.lock pubspec_overrides.ohos.yaml pubspec_overrides.tvos.yaml
bash scripts/prepare_legacy_api19.sh   # 依赖降级 + Dart API 迁移
flutter pub get
flutter build apk --release --target-platform android-arm
```

> ✅ 依赖解析与 Dart 编译已通过（Flutter 3.19.6 验证零编译错误），
> 下一步验证实际 APK 产出。

`-Plegacy-apk` / `NIPAPLAY_LEGACY=1` 会同时切换 `android/build.gradle`（NDK/Kotlin 版本）
与 `android/app/build.gradle`（minSdk/targetSdk/ABI）中的 legacy 分支。

## 已完成/需注意的兼容点

### 已验证（本仓库分析结论）

- **media_kit 预编译 libmpv（v1.1.8 armv7）可在 API 19 运行**：
  解包 `full-armeabi-v7a.jar` 并解析 `libmpv.so` 的 ELF 头，其
  `.note.android.ident` 标注 API 21（NDK r25c），但**全部动态导入
  仅依赖 API 9 时代的符号**（`ANativeWindow_*`、`egl*`、`slCreateEngine`
  等 OpenSL ES/EGL 接口），Android linker 不校验 minApi 标记，
  `dlopen` 在 4.4.2 上可以成功。风险仅在于运行时行为差异
  （如 TLS 栈、字体渲染），需真机回归。
- **`third_party/fvp`（mdk 后端）**：其 gradle 注释明确 NDK r25 下
  minSdk 可低于 21（"lower version error in ndk 26"），legacy 分支
  已在 `third_party/fvp/android/build.gradle` 中将 minSdk 降至 19。
- **插件 minSdk**：`packages/adaptive_platform_ui`、`packages/nipaplay_smb2`
  的 `minSdk 21` 已加 legacy 分支降为 19；`media_kit_video` 与
  media_kit 官方 libs 包均为 `minSdkVersion 16`，无需修改。
- **Kotlin 侧**：`MainActivity.kt` 所有新 API 调用均已有 `Build.VERSION.SDK_INT`
  守卫（R/Q 分支），API 19 走旧路径，无需修改。
- **Manifest**：`enableOnBackInvokedCallback`、`requestLegacyExternalStorage`、
  `networkSecurityConfig` 等属性在旧系统上被忽略，无害。
- **MultiDex**：已启用（API 19 上是必需的，方法数超限风险高）。
- **协程 1.6.4 / multidex 2.0.1**：均支持 API 19。
- **cargokit**：`armeabi-v7a` 目标的 `androidMinSdkVersion: 16`，Rust 侧
  （Erika）可按 API 16+ 编译，向下兼容。
- **cpp_native**：CMake 未硬编码 API 级别，跟随 AGP 的 minSdk 传递。
- **gradle 开关传递**：`flutter build apk` 不透传 `-P` 属性给 gradle，
  legacy 分支统一用环境变量 `NIPAPLAY_LEGACY=1` 触发（所有 gradle
  文件同时检查 `-Plegacy-apk` 属性，供本地 `cd android && ./gradlew`
  直接构建时使用）。

### 已验证：Dart 依赖解析

**Flutter 3.19.6 (Dart 3.3.4) 下的 `flutter pub get` 已在 CI 实际跑通（224 个包）。**
需降级的依赖（由 `scripts/prepare_legacy_api19.sh` 自动处理）：

| 依赖 | 主线 | Legacy | 原因 |
|---|---|---|---|
| flutter_rust_bridge | 2.12.0 | **2.7.0** (vendored patched) | 2.x 全系要求 Dart ≥3.4 |
| erika_flutter | 0.3.5 | **0.3.5** (vendored patched) | 全系要求 Dart ≥3.5 |
| universal_gamepad | git main | **git main** (vendored patched) | 要求 Dart ≥3.10.7 |
| desktop_multi_window | vendored fork | **3.19 shim** | fork 依赖 Flutter 3.44 私有窗口 API |
| permission_handler | 12.x | 11.3.1 | 12.x 要 Dart ≥3.5 |
| package_info_plus | 10.x | 8.0.2 | 9.x+ 要 Dart ≥3.10 |
| wakelock_plus | 1.7+ | 1.2.8 | 新版要 Dart ≥3.4 |
| battery_plus | 7.x | 6.0.2 | 新版依赖 web ≥1.0 |
| mobile_scanner | 7.x | 5.1.1 | 新版要 Dart ≥3.4 |
| fluent_ui | 4.13+ | 4.9.2 ⚠️ | 4.10+ 要 Flutter ≥3.27；**4.9.2 仍用 `WidgetState*`，3.19 下无法编译** |
| video_player | 2.9.5 | 2.9.2 | 新版要 Dart ≥3.4 |
| webview_flutter | 4.13+ | 4.8.0 | 新版要 Dart ≥3.5 |
| http | 1.3+ | 1.2.2 | 新版要 Dart ≥3.4 |
| yaml | 3.1.3+ | 3.1.2 | 新版要 Dart ≥3.4 |
| flutter_svg | 2.0.14 | 2.0.10+1 | 新版要 Dart ≥3.4 |
| desktop_drop | 0.6+ | 0.4.4 | 0.5+ 要 Dart ≥3.4 |
| dynamic_color | 1.9.0 | 1.8.1 ⚠️ | 1.9.0 起 `android/build.gradle.kts` 用 KGP 2.0 `compilerOptions`；1.8.1 又用了 `Color.toARGB32`（3.27+） |
| screen_brightness_android | 2.1.6 | 2.1.3 | 2.1.6 同样是 KGP 2.0 `.kts`；2.1.3 仍为 Groovy + Kotlin 1.9.22 |
| web (override) | 1.x | 0.5.1 | package:web ≥1.0 要 Dart ≥3.4 |
| intl (override) | 0.20+ | 0.18.1 | SDK pin |
| flutter_plugin_android_lifecycle (override) | 2.0.30+ | 2.0.17 | 新版要 Dart ≥3.4 |

### 代码编译：已通过

`scripts/migrate_legacy_api19.py` + `scripts/fix_legacy_manual.py` 已覆盖全部
Flutter 3.27 API 改名和 3.19 兼容性问题。**经 Flutter 3.19.6 (Dart 3.3.4)
实际 `flutter analyze` 验证：lib/ 与 packages/*/lib 零编译错误。**

迁移规则（详见各脚本文件头注释）：
`Color.withValues` → `withOpacity`、`WidgetState` → `MaterialState`、
`Color.toARGB32` → `.value`、`Color.from` → `fromRGBO`、
`Color.r/g/b/a` → `red/green/blue/opacity`（排除 Pixel/自定义类）、
`RoundedSuperellipseBorder` → `RoundedRectangleBorder`、
`SpringDescription.withDurationAndBounce` → `legacySpring()` helper、
`BackdropGroup/BackdropKey` stub、`ImageFilter.shader` → blur、
`Theme.brightnessOf` → `MediaQuery.platformBrightnessOf`、
`CupertinoColors.transparent` → `Color(0x00000000)`、
`CupertinoMediaQuery` → `MediaQuery`、`GlassMediaQuery` → `MediaQuery`、
`DialogTheme.barrierColor` → `.backgroundColor`、
`PopScope<T>` → `PopScope`、`onPopInvokedWithResult` → `onPopInvoked`、
`ColorScheme` 补 `background/onBackground`、
`surfaceContainerHighest` → `surfaceVariant`、
`CupertinoButton.minimumSize` → `minSize`、
fluent_ui `MaterialStateProperty` → `ButtonState`（带 `fluent.` 前缀）、
fluent_ui 4.9+ `thumbBallInnerFactor` → 删除等。

**不影响编译的错误（CI analyze 会报但不阻塞 APK 构建）：**
- `packages/fluent_ui-4.15.1/lib`（vendored 副本，不参与 Android 编译）
- `rust_builder/cargokit/build_tool/lib`（构建工具，不编译进 APK）
- `media_kit/lib/src/player/web/` + `media_kit_video/lib/src/video/video_web.dart`
  （web 路径，Android 用 `dart:io` 条件 import）

- **desktop_multi_window shim**：fork 版深度依赖 Flutter 3.44 的
  `package:flutter/src/widgets/_window.dart` 等私有窗口 API，3.19 不存在。
  `scripts/legacy_desktop_multi_window_shim.dart` 提供公共 API 的 no-op
  实现（`runDesktopMultiWindowApp` → `runApp`，`WindowController` /
  `DesktopTooltipWindowController` 为 `ChangeNotifier` stub），
  Android 运行时本就不启用多窗口（`isSupported` 返回 false），无害。

### 预期会遇到的问题（按优先级）

1. **64 位 `.so` 混入**：`--target-platform android-arm` 已限制；若某些
   插件仍打包 arm64 库，4.4 安装时只取 armeabi-v7a，无实际影响，但
   `abiFilters 'armeabi-v7a'`（legacy 分支中已配置）会强制剔除。
2. **R8 full mode**：`gradle.properties` 中 `android.enableR8.fullMode=true`
   在 legacy 构建下未关闭。若出现运行时 `MissingClass` 崩溃，先以
   `android.enableR8.fullMode=false` 排查。
3. **TLS/网络**：Android 4.4 无 TLS 1.2 默认启用与现代化 cipher suite，
   HTTPS 请求（弹幕源、Bangumi API）大概率失败。如需解决需自带
   Conscrypt 或降级目标站点，属于运行时问题而非构建问题。
4. **Erika（Rust 引擎）**：若未使用 `ERIKA_PREBUILT=1`，源码构建时
   确认 Rust `ring`/`rustls` 等依赖的 armv7 API 19 支持情况。
5. **liquid_glass_widgets 降级**：iOS 26 拟形效果在 3.19 退化为
   圆角矩形 + 普通模糊（`RoundedSuperellipseBorder` → `RoundedRectangleBorder`、
   `ImageFilter.shader` → `blur`），视觉差异但功能不受影响。
6. **media_kit web 源码 analyze 报错**：`media_kit/lib/src/player/web/`
   与 `media_kit_video/lib/src/video/video_web.dart` 使用 Dart 3.4 的
   `dart:js_interop` 新 API（`JSString.toDart` 等），analyze 会报约 12 个
   error，但 Android 构建用 `dart:io` 条件 import 路径，不编译这些文件，
   不影响 APK 构建。

## CI 实测状态（2026-11-16）

已在 GitHub Actions 上用 `build-android-legacy.yml` 连续触发多次构建，逐层暴露并修掉了
基础设施问题。**依赖解析与 Dart 编译已通过**（lib/ 和 packages/*/lib 零编译错误），
下一步验证实际 APK 产出。

### 已修复的阻塞点

| # | 失败阶段 | 根因 | 修复 |
|---|---|---|---|
| 1 | `flutter pub get` | `desktop_multi_window` 的 `flutter: ">=3.44.0"` 未被放宽 | 按 `environment` 块逐行归一化 |
| 2 | `flutter pub get` | `flutter_svg ≥2.0.11` 需 Dart ≥3.4 | 注释感知重写 + `dependency_overrides` |
| 3 | `:app` 配置 | Flutter 3.19 的 `FlutterExtension` 没有 `versionCode`/`versionName` | legacy 分支改读 `local.properties` |
| 4 | 插件配置 | `dynamic_color 1.9.0` / `screen_brightness_android 2.1.6` 的 `.kts` 用 KGP 2.0 | 固定到 Groovy 版本（1.7.0 / 2.1.3） |
| 5 | `flutter build apk` | pubspec 的 `version` 没有 `+构建号` | workflow 传 `--build-number` |
| 6 | Dart 编译 | `fluent_ui 4.9.2` 用 `WidgetState*`（3.22+） | 降到 4.7.7（用自己的 `ButtonState`） |
| 7 | Dart 编译 | `Color.r/g/b/a`、`CupertinoMediaQuery`、`GlassMediaQuery` 等 3.27 API | `fix_legacy_manual.py` 批量迁移 |
| 8 | Dart 编译 | fluent_ui `MaterialStateProperty` vs `ButtonState` 类型不匹配 | 转换为 `fluent.ButtonState`（带前缀） |
| 9 | Dart 编译 | liquid_glass `BackdropKey`/`ImageFilter.shader`/`SpringDescription.withDurationAndBounce` | stub + 降级 + `legacySpring()` helper |

### 不影响 APK 构建的 analyze 错误

以下路径在 `flutter analyze` 中会报错，但**不参与 Android release 编译**：

| 来源 | 原因 |
|---|---|
| `packages/fluent_ui-4.15.1/lib` | 仓库自带的 vendored 副本，pub 解析用 pub 版 4.7.7 |
| `rust_builder/cargokit/build_tool/lib` | 构建工具，不编译进 APK |
| `media_kit/lib/src/player/web/` | web 路径，Android 用 `dart:io` 条件 import |
| `media_kit_video/lib/src/video/video_web.dart` | 同上 |

## media_kit armv7 .so 的验证方法（复现）

```bash
curl -sL -o full.jar \
  https://github.com/media-kit/libmpv-android-video-build/releases/download/v1.1.8/full-armeabi-v7a.jar
unzip -o full.jar
readelf --dyn-syms -W lib/armeabi-v7a/libmpv.so | grep UND | awk '{print $NF}' | sort -u
# 输出仅含 ANativeWindow_*/egl*/slCreateEngine 等 API 9 时代符号 → API 19 可加载
```

## 产物命名

`NipaPlay-<version>-Android-4.4-legacy-armeabi-v7a.apk` —— 与主线 APK
可共存安装（主线 applicationId 为 `com.aimessoft.nipaplay`，两者相同，
**不可并存**，安装 legacy 版会覆盖主线版本，注意提醒用户）。
