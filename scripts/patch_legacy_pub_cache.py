#!/usr/bin/env python3
"""CI 阶段：修补 pub 缓存中与 legacy（Flutter 3.19 / Android 4.4）不兼容的包。

必须在 `flutter pub get` 之后运行（缓存目录由此时才存在）。

当前修补项
----------
screen_brightness_android 2.1.3
    源码 `import androidx.core.net.toUri` 并使用 `.toUri()`，但它的
    `android/build.gradle` 没有声明 `androidx.core:core-ktx` 依赖，
    因此在 Flutter 插件的独立编译单元里 Kotlin 报：

        Unresolved reference 'toUri'

    2.1.4/2.1.5 同样如此；2.1.6 起改用 Kotlin DSL 且需要 KGP 2.0，
    legacy 的 Kotlin 1.9.24 无法解析，所以这里给 2.1.3 补上依赖，
    而不是继续降版本（2.1.2 的 compileSdk 31 在 AGP 8.9 下风险更高）。
    androidx.core 1.10.1 与 app 主线使用的版本一致，minSdk 19 兼容。
"""

import glob
import os
import re
import sys


def pub_cache_dir():
    env = os.environ.get("PUB_CACHE")
    if env:
        return env
    return os.path.join(os.path.expanduser("~"), ".pub-cache")


def _insert_first_module_dependency(src, line, kts):
    """把依赖插到**模块级** dependencies 块的首行。

    build.gradle 里通常先出现 buildscript { ... dependencies { ... } }，
    那是构建脚本类路径，不能往里插 implementation。模块级（最后一个）
    dependencies 块才是声明运行时依赖的地方。
    """
    pattern = re.compile(r"^dependencies\s*\{", re.M)
    matches = list(pattern.finditer(src))
    if not matches:
        return None
    m = matches[-1]
    insert_at = m.end()
    return src[:insert_at] + "\n    " + line + src[insert_at:]


def patch_screen_brightness_android(cache):
    """给 screen_brightness_android 补 androidx.core:core-ktx 依赖。"""
    patched = []
    for pkg in sorted(glob.glob(os.path.join(cache, "hosted", "pub.dev",
                                             "screen_brightness_android-*"))):
        for name, kts in (("build.gradle", False), ("build.gradle.kts", True)):
            path = os.path.join(pkg, "android", name)
            if not os.path.exists(path):
                continue
            src = open(path, encoding="utf-8").read()
            if "androidx.core:core-ktx" in src:
                continue
            line = ('implementation("androidx.core:core-ktx:1.10.1")' if kts
                    else 'implementation "androidx.core:core-ktx:1.10.1"')
            new = _insert_first_module_dependency(src, line, kts)
            if new is None:
                continue
            open(path, "w", encoding="utf-8").write(new)
            patched.append(path)
            break
    return patched


def patch_min_sdk(cache):
    """把 pub 缓存里所有插件的 minSdk 降到 19。

    Flutter 的 Gradle 插件会校验每个 Android 插件声明的 minSdk：一旦某个插件
    大于 app 的 minSdk，构建立刻失败，例如：

        The plugin universal_gamepad requires a higher Android SDK version.

    而 API 19 目标本身就要求全部插件降到 19（4.4 是"尽力而为"支持，插件是否
    真的能在 19 上跑属于运行时问题，但不降就出不了 APK）。
    """
    patched = []
    pattern = re.compile(r"(?m)^([ \t]*minSdk(?:Version)?[ \t]*(?:=[ \t]*|[ \t]+))(\d+)([ \t]*)$")
    for pattern_path in ("*/android/build.gradle", "*/android/build.gradle.kts"):
        for f in glob.glob(os.path.join(cache, "hosted", "pub.dev", pattern_path)):
            src = open(f, encoding="utf-8").read()

            def repl(m):
                try:
                    val = int(m.group(2))
                except ValueError:
                    return m.group(0)
                if val <= 19:
                    return m.group(0)
                return m.group(1) + "19" + m.group(3)

            new = pattern.sub(repl, src)
            if new != src:
                open(f, "w", encoding="utf-8").write(new)
                patched.append(f)
    return patched


def main():
    cache = pub_cache_dir()
    if not os.path.isdir(cache):
        print(f"pub cache 不存在，跳过: {cache}")
        return 0
    total = 0
    for fn in (patch_screen_brightness_android, patch_min_sdk):
        for p in fn(cache):
            print(f"patched: {p}")
            total += 1
    print(f"legacy pub-cache 修补完成（{total} 个文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
