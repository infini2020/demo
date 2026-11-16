#!/usr/bin/env bash
# Legacy (Android 4.4 / Flutter 3.19 / Dart 3.3) 依赖准备脚本。
#
# 在 CI 的 `flutter pub get` 之前调用。完成三件事：
#   1. 放宽 pubspec 与本地 path 包的 Dart/Flutter SDK 下限。
#   2. 降级若干 pub 依赖到 Dart 3.3 兼容版本。
#   3. 准备 vendored patched 副本（frb / erika / universal_gamepad），
#      并用 3.19 兼容 shim 替换 desktop_multi_window。
#   4. 调用 migrate_legacy_api19.py 批量迁移 Dart 代码 API。
#
# 已验证：经此脚本后 `flutter pub get` + `flutter analyze` 在 Flutter 3.19.6
# (Dart 3.3.4) 下对 lib/ 和 packages/*/lib 零编译错误。
# 注意：packages/fluent_ui-4.15.1、cargokit、media_kit web 路径的 analyze
#       错误不影响 Android APK 构建（不参与编译）。
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"

echo "=== [1/4] 放宽 SDK 约束 ==="
# 主 pubspec：Dart ^3.5.3 -> >=3.3.0；移除 tvos/ohos 专属依赖块
sed -i 's/^  sdk: \^3\.5\.3$/  sdk: ">=3.3.0 <4.0.0"/' pubspec.yaml
python3 - <<'PY'
import re
src = open('pubspec.yaml').read()
# 移除 tvos/ohos 专属依赖（git fork 与 ohos path 包）
for name in ['shared_preferences_tvos','path_provider_tvos','package_info_plus_tvos',
             'wakelock_plus_tvos','sqflite_tvos','video_player_tvos',
             'permission_handler_ohos','wakelock_plus_ohos']:
    src = re.sub(r'^  %s:\n(?:    .*\n|      .*\n)*' % name, '', src, flags=re.M)
open('pubspec.yaml','w').write(src)
PY

# 本地 path 包：放宽 sdk/flutter 下限。
#
# 约束写法并不统一：^3.5.3、^3.10.7、">=3.44.0"、">=3.47.0-0.3.pre" 都有。
# 早期版本用 sed 匹配 "^3.x" caret 形式，漏掉了 ">=x" 形式，导致
# desktop_multi_window 的 flutter: ">=3.44.0" 未被放宽，pub 解析直接失败：
#   Because nipaplay depends on desktop_multi_window from path which requires
#   Flutter SDK version >=3.44.0, version solving failed.
# 因此改为按 environment 块逐行归一化，覆盖任意约束写法。
relax_local_pubspecs() {
  python3 - "$@" <<'PY'
import re, sys

SDK = '">=3.3.0 <4.0.0"'
FLUTTER = '">=3.19.0"'

def relax(path):
    try:
        lines = open(path, encoding='utf-8').read().splitlines(keepends=True)
    except OSError:
        return
    out, in_env = [], False
    for line in lines:
        # 进入 environment: 块（该键必须顶格）
        if re.match(r'^environment:\s*(#.*)?$', line):
            in_env = True
            out.append(line)
            continue
        if in_env:
            # 遇到下一个顶格键即离开 environment 块
            if line.strip() and not line.startswith((' ', '\t')):
                in_env = False
            elif re.match(r'^  sdk:', line):
                out.append('  sdk: %s\n' % SDK)
                continue
            elif re.match(r'^  flutter:', line):
                out.append('  flutter: %s\n' % FLUTTER)
                continue
        out.append(line)
    open(path, 'w', encoding='utf-8').write(''.join(out))

for p in sys.argv[1:]:
    relax(p)
PY
}

relax_local_pubspecs packages/*/pubspec.yaml

echo "=== [2/4] 降级 pub 依赖 ==="
# 已验证的 Dart 3.3 兼容版本组合
sed -i 's/^  path: \^1\.9\.1$/  path: ^1.9.0/' pubspec.yaml
sed -i 's/^  intl: \^0\.20\.2$/  intl: ^0.18.1/' pubspec.yaml
sed -i 's/^  http: \^1\.3\.0$/  http: 1.2.2/' pubspec.yaml
sed -i 's/^  yaml: \^3\.1\.3$/  yaml: 3.1.2/' pubspec.yaml
sed -i 's/^  video_player: 2\.9\.5$/  video_player: 2.9.2/' pubspec.yaml
sed -i 's/^  webview_flutter: \^4\.13\.1$/  webview_flutter: 4.8.0/' pubspec.yaml
sed -i 's/^  battery_plus: \^7\.0\.0$/  battery_plus: 6.0.2/' pubspec.yaml
sed -i 's/^  wakelock_plus: \^1\.7\.0$/  wakelock_plus: 1.2.8/' pubspec.yaml
sed -i 's/^  package_info_plus: \^10\.2\.1$/  package_info_plus: 8.0.2/' pubspec.yaml
sed -i 's/^  permission_handler: \^12\.0\.0+1$/  permission_handler: 11.3.1/' pubspec.yaml
sed -i 's/^  mobile_scanner: \^7\.2\.0$/  mobile_scanner: 5.1.1/' pubspec.yaml
sed -i 's/^  fluent_ui: \^4\.13\.0$/  fluent_ui: 4.7.7/' pubspec.yaml
# fluent_ui 4.8+ 开始用 Flutter 3.22 的 WidgetState*；4.7.x 用自己的 ButtonState，
# 独立于框架 MaterialState/WidgetState，3.19 可编译。
# 注意：app 代码若调用了 4.8+ 新增 API，migrate 脚本不会修——需按 CI 日志手动改。
sed -i 's/^  desktop_drop: \^0\.6\.1$/  desktop_drop: 0.4.4/' pubspec.yaml
# flutter_svg 2.0.11+ 要求 Dart >=3.4.0。该行行尾带注释（"# 用于显示SVG图标"），
# 用 "^...$" 锚定的 sed 匹配不上，必须保留注释整体重写。
python3 - <<'PY'
import re
src = open('pubspec.yaml').read()
src = re.sub(r'^  flutter_svg: \^2\.0\.14(.*)$',
             lambda m: '  flutter_svg: 2.0.10+1' + m.group(1),
             src, count=1, flags=re.M)
open('pubspec.yaml', 'w').write(src)
PY
sed -i 's/^  flutter_rust_bridge: 2\.12\.0$/  flutter_rust_bridge: 2.7.0/' pubspec.yaml

# dependency_overrides：pin web/intl/lifecycle + vendored patched 副本
python3 - <<'PY'
src = open('pubspec.yaml').read()
if '  web: 0.5.1' not in src.split('dependency_overrides:',1)[-1].split('\n',1)[0] if 'dependency_overrides:' in src else True:
    pass
# 简单追加 overrides（若已存在则跳过）
ovr = src[src.find('dependency_overrides:'):] if 'dependency_overrides:' in src else ''
add = '''  # Legacy (Android 4.4/Dart 3.3): pin web to 0.5.x (package:web >=1.0 needs Dart 3.4).
  web: 0.5.1
  intl: 0.18.1
  flutter_plugin_android_lifecycle: 2.0.17
  # flutter_svg 2.0.11+ 要求 Dart >=3.4.0，强制回退（直接依赖与传递依赖一并覆盖）。
  flutter_svg: 2.0.10+1
  # 这两个包的新版本把 android/build.gradle 换成了 Kotlin DSL 并使用 Kotlin Gradle
  # Plugin 2.0 的 compilerOptions DSL，legacy 的 Kotlin 1.9.24 无法解析：
  #   e: .../dynamic_color-1.9.0/android/build.gradle.kts:29 Unresolved reference: compilerOptions
  # 回退到仍是 Groovy build.gradle 的版本（dynamic_color 1.8.1 / sba 2.1.3）。
  dynamic_color: 1.7.0
  screen_brightness_android: 2.1.3
  # Legacy: vendored frb 2.7.0 / erika 0.3.5 / universal_gamepad with relaxed SDK bounds.
  flutter_rust_bridge:
    path: .legacy-patches/flutter_rust_bridge
  erika_flutter:
    path: .legacy-patches/erika_flutter
  universal_gamepad:
    path: .legacy-patches/universal_gamepad
'''
if 'web: 0.5.1' not in ovr:
    src = src.replace('dependency_overrides:', 'dependency_overrides:\n' + add)
    open('pubspec.yaml','w').write(src)
PY

echo "=== [3/4] 准备 vendored patched 副本 ==="
mkdir -p .legacy-patches

# frb 2.7.0：放宽 SDK 约束
if [ ! -d .legacy-patches/flutter_rust_bridge ]; then
  dart pub cache add flutter_rust_bridge --version 2.7.0 >/dev/null 2>&1 || true
  cp -r "${HOME:-~}/.pub-cache/hosted/pub.dev/flutter_rust_bridge-2.7.0" \
        .legacy-patches/flutter_rust_bridge
  sed -i 's/sdk: ">=3\.4\.0 <4\.0\.0"/sdk: ">=3.3.0 <4.0.0"/' \
        .legacy-patches/flutter_rust_bridge/pubspec.yaml
fi

# erika_flutter 0.3.5：放宽 SDK/Flutter/ffi 约束
if [ ! -d .legacy-patches/erika_flutter ]; then
  dart pub cache add erika_flutter --version 0.3.5 >/dev/null 2>&1 || true
  cp -r "${HOME:-~}/.pub-cache/hosted/pub.dev/erika_flutter-0.3.5" \
        .legacy-patches/erika_flutter
  sed -i 's/sdk: ">=3\.5\.0 <4\.0\.0"/sdk: ">=3.3.0 <4.0.0"/; s/flutter: ">=3\.24\.0"/flutter: ">=3.19.0"/; s/ffi: \^2\.1\.4/ffi: ^2.1.0/' \
        .legacy-patches/erika_flutter/pubspec.yaml
fi

# erika_flutter 的 ErikaMediaSession 整体建立在 API 21+/26+（MediaSession、
# NotificationChannel、MediaStyle…）之上，而插件在 onAttachedToEngine 里无条件构造它。
# API 19 上这会让插件注册抛 NoClassDefFoundError，GeneratedPluginRegistrant 中断，
# erika 之后的所有插件都注册不上，Dart 端卡在首帧之前 —— 表现为启动后永久黑屏。
# 这里替换为同 API 的空实现（仅 legacy），媒体通知/锁屏控制不可用，其余功能不受影响。
cp scripts/legacy_erika_media_session_stub.kt \
   .legacy-patches/erika_flutter/android/src/main/kotlin/dev/aimesoft/erika_flutter/ErikaMediaSession.kt

# universal_gamepad：git clone + 放宽 SDK
if [ ! -d .legacy-patches/universal_gamepad ]; then
  git clone --depth 1 https://github.com/makabaka11/universal_gamepad.git \
            .legacy-patches/universal_gamepad
  sed -i 's/sdk: \^3\.10\.7/sdk: ">=3.3.0 <4.0.0"/; s/web: \^1\.1\.0/web: ">=0.5.0 <2.0.0"/' \
        .legacy-patches/universal_gamepad/pubspec.yaml
fi

# vendored 副本：同样按 environment 块归一化（各包约束写法不同，含 ">=x" 形式）。
# 上面逐个包做的 sed 只覆盖特定写法，这里兜底。
relax_local_pubspecs .legacy-patches/*/pubspec.yaml

# vendored 副本的 Android minSdk 一并降到 19。
# Flutter 的 Gradle 插件会校验每个 Android 插件声明的 minSdk，只要有一个大于
# app 的 minSdk 就整体失败（CI 曾报 "The plugin universal_gamepad requires a
# higher Android SDK version"）。erika_flutter 默认 26、universal_gamepad 默认 21。
for g in .legacy-patches/*/android/build.gradle; do
  [ -f "$g" ] || continue
  sed -i -E 's/(minSdk(Version)?[[:space:]]*=[[:space:]]*)2[0-9]([[:space:]]*)$/\1 19/' "$g"
  sed -i -E 's/(minSdkVersion[[:space:]]+)2[0-9]([[:space:]]*)$/\1 19/' "$g"
done

# 仓库内的 path 插件（packages/*、third_party/*）同理：只要声明了高于 19 的
# minSdk，Flutter 工具就会拒绝构建（CI 曾报 "The plugin volume_controller
# requires a higher Android SDK version"）。legacy 构建统一降到 19——
# adaptive_platform_ui / nipaplay_smb2 / fvp 已有 legacy 分支，这里只是兜底。
for g in packages/*/android/build.gradle third_party/*/android/build.gradle; do
  [ -f "$g" ] || continue
  sed -i -E 's/^([[:space:]]*minSdk(Version)?[[:space:]]*=[[:space:]]*)2[0-9]([[:space:]]*)$/\1 19/' "$g"
  sed -i -E 's/^([[:space:]]*minSdkVersion[[:space:]]+)2[0-9]([[:space:]]*)$/\1 19/' "$g"
done

# desktop_multi_window：用 3.19 shim 替换（fork 依赖 Flutter 3.44 私有窗口 API）
cp scripts/legacy_desktop_multi_window_shim.dart \
   packages/desktop_multi_window/lib/desktop_multi_window.dart

# frb_generated.dart：移除 3.19 不存在的命名参数
python3 - <<'PY'
f='lib/src/rust/frb_generated.dart'
import os
if os.path.exists(f):
    src=open(f).read()
    src=src.replace("    bool forceSameCodegenVersion = true,\n","")
    src=src.replace("      forceSameCodegenVersion: forceSameCodegenVersion,\n","")
    src=src.replace("    wasmBindgenName: 'wasm_bindgen',\n","")
    open(f,'w').write(src)
PY

echo "=== [4/4] 迁移 Dart 代码 API ==="
python3 scripts/migrate_legacy_api19.py lib packages/*/lib \
       third_party/fvp/lib third_party/volume_controller/lib \
       third_party/smb_connect/lib \
       third_party/media-kit-upstream/libs \
       third_party/media-kit-upstream/media_kit/lib \
       third_party/media-kit-upstream/media_kit_video/lib \
       packages/media_kit/lib packages/media_kit_video/lib

# media_kit_video onPopInvokedWithResult
find packages/media_kit_video third_party/media-kit-upstream/media_kit_video \
     -name fullscreen_inherited_widget.dart \
     -exec sed -i 's/onPopInvokedWithResult: (_, __)/onPopInvoked: (_)/g' {} +

# liquid_glass_widgets 的 meta/logging 约束
sed -i 's/^  meta: ">=1\.16\.0 <2\.0\.0"$/  meta: ">=1.11.0 <2.0.0"/' \
    packages/liquid_glass_widgets/pubspec.yaml 2>/dev/null || true
sed -i 's/^  logging: >=1\.3\.0$/  logging: ">=1.1.0 <3.0.0"/' \
    packages/liquid_glass_widgets/pubspec.yaml 2>/dev/null || true
sed -i 's/^  logging: \^1\.3\.0$/  logging: ">=1.1.0 <3.0.0"/' \
    packages/liquid_glass_widgets/pubspec.yaml 2>/dev/null || true

# ColorScheme 补 background/onBackground（app_theme.dart）
python3 - <<'PY'
import re
f='lib/utils/app_theme.dart'
src=open(f).read()
src=src.replace('''          surface: Colors.white, // 表面颜色
          onSurface: Colors.black87, // 在表面颜色上的文本和图标颜色''',
'''          surface: Colors.white, // 表面颜色
          background: Colors.white,
          onSurface: Colors.black87, // 在表面颜色上的文本和图标颜色
          onBackground: Colors.black87,''')
src=src.replace('''          surface: Colors.black, // 表面颜色，深色模式下使用黑色。
          onSurface: Colors.white, // 在表面颜色上的文本和图标颜色，确保对比度。''',
'''          surface: Colors.black, // 表面颜色，深色模式下使用黑色。
          background: Colors.black,
          onSurface: Colors.white, // 在表面颜色上的文本和图标颜色，确保对比度。
          onBackground: Colors.white,''')
open(f,'w').write(src)
PY

echo "=== legacy 依赖与代码迁移完成 ==="

# ── 迁移脚本覆盖不到的手动修复（CI 实测验证） ──
# 已用 Flutter 3.19.6 验证：经此脚本后 lib/ 和 packages/*/lib 零编译错误。
echo "=== [5/5] 手动修复剩余编译错误 ==="
python3 scripts/fix_legacy_manual.py
