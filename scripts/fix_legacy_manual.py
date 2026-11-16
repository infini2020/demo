#!/usr/bin/env python3
"""Legacy (Android 4.4 / Flutter 3.19) 手动修复脚本。

处理 migrate_legacy_api19.py 覆盖不到的编译错误。
已用 Flutter 3.19.6 验证：经此脚本后 lib/ 和 packages/*/lib 零编译错误。
"""
import re, os, glob, sys

def fix_cupertino_media_query():
    """CupertinoMediaQuery (3.27+) -> MediaQuery."""
    for f in glob.glob('lib/**/*.dart', recursive=True):
        src = open(f).read()
        if 'CupertinoMediaQuery' not in src: continue
        src = src.replace('CupertinoMediaQuery.platformBrightnessOf', 'MediaQuery.platformBrightnessOf')
        src = src.replace('CupertinoMediaQuery(', 'MediaQuery(')
        open(f,'w').write(src)

def fix_cupertino_button_params():
    """删除 3.19 CupertinoButton 不存在的参数。"""
    for f in glob.glob('lib/themes/cupertino/**/*.dart', recursive=True):
        src = open(f).read(); orig = src
        src = re.sub(r'\n\s*focusColor: [^\n]+,\n', '\n', src)
        src = re.sub(r'\n\s*onFocusChange: \([^\n]+,\n', '\n', src)
        if src != orig: open(f,'w').write(src)

def fix_focus_scope():
    """descendantsAreFocusable (3.27+) -> 删除。"""
    for f in glob.glob('lib/**/*.dart', recursive=True):
        src = open(f).read()
        if 'descendantsAreFocusable' not in src: continue
        src = re.sub(r'\n\s*descendantsAreFocusable: [^\n]+,', '', src)
        open(f,'w').write(src)

def fix_fluent_slider_params():
    """thumbBallInnerFactor (fluent_ui 4.9+) -> 删除。"""
    for f in glob.glob('lib/**/*.dart', recursive=True):
        src = open(f).read()
        if 'thumbBallInnerFactor' not in src: continue
        src = re.sub(r'\n\s*thumbBallInnerFactor: [^\n]+,', '', src)
        open(f,'w').write(src)

def fix_in_view_dialog():
    """requestFocus -> 删除。"""
    f = 'lib/widgets/in_view_dialog.dart'
    if os.path.exists(f):
        src = open(f).read()
        src = re.sub(r'\n\s*requestFocus: [^,\n]+,', '', src)
        open(f,'w').write(src)

def fix_glass_media_query():
    """GlassMediaQuery (liquid_glass 3.27+) -> MediaQuery。"""
    for f in glob.glob('packages/liquid_glass_widgets/lib/**/*.dart', recursive=True):
        src = open(f).read()
        if 'GlassMediaQuery' not in src: continue
        src = src.replace('GlassMediaQuery.platformBrightnessOf', 'MediaQuery.platformBrightnessOf')
        src = src.replace('GlassMediaQuery.of(', 'MediaQuery.of(')
        open(f,'w').write(src)

EXCLUDE_RGB = ['pixel', 'seg', 'nextSeg', 'startSeg', '_pointKey']

def _color_ctx(m):
    var = m.group(1)
    for ex in EXCLUDE_RGB:
        if var.endswith(ex) or var == ex: return m.group(0)
    ch = m.group(2)
    if ch == 'a': return f'{var}.opacity'
    name = {'r':'red','g':'green','b':'blue'}[ch]
    return f'({var}.{name} / 255.0)'

def fix_color_rgba():
    """Color.r/g/b/a (3.27+) -> red/green/blue/opacity。宽泛模式+排除非 Color。"""
    # liquid_glass: 宽泛模式（排除 Pixel/seg 等）
    for f in glob.glob('packages/liquid_glass_widgets/lib/**/*.dart', recursive=True):
        src = open(f).read(); orig = src
        src = re.sub(r'(\b\w+(?:\.\w+)*)\.([rgba])\b(?!\w)', _color_ctx, src)
        if src != orig: open(f,'w').write(src)
    # lib/: 精确模式（\w*[Cc]olor）
    for f in glob.glob('lib/**/*.dart', recursive=True):
        src = open(f).read(); orig = src
        src = re.sub(r'(\b\w*[Cc]olor[s]?)\.r\b(?!\w)', r'(\1.red / 255.0)', src)
        src = re.sub(r'(\b\w*[Cc]olor[s]?)\.g\b(?!\w)', r'(\1.green / 255.0)', src)
        src = re.sub(r'(\b\w*[Cc]olor[s]?)\.b\b(?!\w)', r'(\1.blue / 255.0)', src)
        src = re.sub(r'(\b\w*[Cc]olor[s]?)\.a\b(?!\w)', r'\1.opacity', src)
        if src != orig: open(f,'w').write(src)

def fix_ui_false():
    """ui.(false) 残留 -> (false)。"""
    for f in glob.glob('packages/liquid_glass_widgets/lib/**/*.dart', recursive=True):
        src = open(f).read()
        if 'ui.(false)' not in src: continue
        src = src.replace('ui.(false)', '(false)')
        open(f,'w').write(src)

def fix_image_filter_shader():
    """ImageFilter.shader -> blur; 分号修复。"""
    for f in glob.glob('packages/liquid_glass_widgets/lib/**/*.dart', recursive=True):
        src = open(f).read(); orig = src
        src = src.replace('ui.ImageFilter.blur(sigmaX: 40, sigmaY: 40) // legacy',
                          'ui.ImageFilter.blur(sigmaX: 40, sigmaY: 40); // legacy')
        src = re.sub(r'ImageFilter\.shader\([^)]+\)', 'ui.ImageFilter.blur(sigmaX: 40, sigmaY: 40)', src)
        src = re.sub(r'\n\s*\.\.backdropKey\s*=\s*\n?\s*[^\n]+\n', '\n', src)
        if src != orig: open(f,'w').write(src)

def fix_backdrop_stub():
    """BackdropGroup/BackdropKey stub 注入。"""
    stub = '''

// Flutter 3.19 legacy stubs for 3.27 backdrop-group APIs
typedef BackdropKey = Object;

class BackdropGroup extends StatelessWidget {
  const BackdropGroup({super.key, required this.child});
  final Widget child;
  static _BackdropGroupScope? of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<_BackdropGroupScope>();
  @override
  Widget build(BuildContext context) =>
      _BackdropGroupScope(backdropKey: Object(), child: child);
}

class _BackdropGroupScope extends InheritedWidget {
  const _BackdropGroupScope({required this.backdropKey, required super.child});
  final BackdropKey backdropKey;
  @override
  bool updateShouldNotify(_BackdropGroupScope old) =>
      backdropKey != old.backdropKey;
}
'''
    for f in ['packages/liquid_glass_widgets/lib/src/renderer/rendering/liquid_glass_layer.dart',
              'packages/liquid_glass_widgets/lib/src/renderer/rendering/liquid_glass_render_object.dart']:
        if not os.path.exists(f): continue
        src = open(f).read()
        need = 'BackdropKey' in src and 'typedef BackdropKey' not in src
        if not need and 'class BackdropGroup' not in src and 'BackdropGroup' in src:
            need = True
        if not need: continue
        # 移除已有的 typedef（可能位置错误）
        src = re.sub(r'^// Flutter 3\.19 legacy.*\ntypedef BackdropKey = Object;\n', '', src, flags=re.M)
        src = re.sub(r'^typedef BackdropKey = Object;\n', '', src, flags=re.M)
        lines = src.split('\n')
        last_import = max((i for i,l in enumerate(lines) if l.startswith('import ')), default=-1)
        if last_import >= 0:
            lines.insert(last_import + 1, stub)
        open(f,'w').write('\n'.join(lines))

def fix_glass_spring():
    """legacySpring 函数定义 + dart:math import。"""
    f = 'packages/liquid_glass_widgets/lib/utils/glass_spring.dart'
    if not os.path.exists(f): return
    src = open(f).read()
    if 'legacySpring' not in src: return
    # 确保有 dart:math import
    if "import 'dart:math'" not in src:
        # 在第一个 import 前加
        src = re.sub(r"(import '[^']+';\n)", "import 'dart:math' as math;\n\\1", src, count=1)
    # 确保有 legacySpring 函数定义
    if 'SpringDescription legacySpring(' not in src:
        helper = '''

/// Flutter 3.19 fallback for SpringDescription.withDurationAndBounce (3.27+).
SpringDescription legacySpring({required Duration duration, required double bounce}) {
  final stiffness = 100.0 / (duration.inMilliseconds / 300.0);
  final damping = 2.0 * math.sqrt(stiffness) * (1.0 - bounce.clamp(0.0, 1.0));
  return SpringDescription(mass: 1, stiffness: stiffness, damping: damping);
}
'''
        # 在 abstract final class GlassSpring 前插入
        src = src.replace('abstract final class GlassSpring', helper + '\nabstract final class GlassSpring')
    open(f,'w').write(src)

def fix_animated_glass_indicator():
    """Color.from -> fromRGBO。"""
    f = 'packages/liquid_glass_widgets/lib/widgets/shared/animated_glass_indicator.dart'
    if not os.path.exists(f): return
    src = open(f).read()
    src = re.sub(r'Color\.from\(\s*alpha:\s*([\d.]+),\s*red:\s*([\d.]+),\s*green:\s*([\d.]+),\s*blue:\s*([\d.]+),?\s*\)',
                 lambda m: f'Color.fromRGBO({int(round(float(m.group(2))*255))}, {int(round(float(m.group(3))*255))}, {int(round(float(m.group(4))*255))}, {m.group(1)})',
                 src, flags=re.S)
    open(f,'w').write(src)

def fix_glass_spacing():
    """spacing 参数删除 (liquid_glass)。"""
    for f in ['packages/liquid_glass_widgets/lib/widgets/surfaces/glass_app_bar.dart',
              'packages/liquid_glass_widgets/lib/widgets/surfaces/shared/tab_bar_bottom_internal.dart']:
        if not os.path.exists(f): continue
        src = open(f).read()
        src = re.sub(r'\n\s*spacing:\s*[^,\n]+,', '', src)
        open(f,'w').write(src)

def fix_window_service_minimum_size():
    """DesktopMultiWindow.createWindow 的 minimumSize -> minSize（shim API）。

    不能无差别替换 `minimumSize:`：这些文件里还有本地辅助函数
    `calculateHalfWidthBounds(minimumSize: ...)`，一起改名会让调用点与
    形参声明不一致（CI 曾在 external_player_window_service.dart:60 报
    “No named parameter with the name 'minSize'”）。只改 shim 的具名参数。
    """
    for f in ['lib/services/desktop_player_window_service.dart',
              'lib/services/external_player_window_service.dart',
              'lib/services/external_player_console_window_service.dart']:
        if not os.path.exists(f): continue
        src = open(f).read()
        src = re.sub(r'\bminimumSize:\s*(?=minimumWindowSizeForAspect\(|_minimumSizeFor\()',
                     'minSize: ', src)
        open(f,'w').write(src)

def fix_bangumi_image():
    """bangumi_comments_widget: AssetImage/NetworkImage as String + as ImageProvider。"""
    f = 'lib/themes/nipaplay/widgets/bangumi_comments_widget.dart'
    if not os.path.exists(f): return
    src = open(f).read()
    # 统一格式
    src = re.sub(r'AssetImage\(my\.avatarUrl(?: as String)?\)(?: as ImageProvider)?',
                 'AssetImage(my.avatarUrl as String) as ImageProvider', src)
    src = re.sub(r'NetworkImage\(_proxiedImageUrl\(my\.avatarUrl(?: as String)?\)\)(?: as ImageProvider)?',
                 'NetworkImage(_proxiedImageUrl(my.avatarUrl as String)) as ImageProvider', src)
    src = re.sub(r'AssetImage\(comment\.avatarUrl(?: as String)?\)(?: as ImageProvider)?',
                 'AssetImage(comment.avatarUrl as String) as ImageProvider', src)
    src = re.sub(r'NetworkImage\(_proxiedImageUrl\(comment\.avatarUrl(?: as String)?\)\)(?: as ImageProvider)?',
                 'NetworkImage(_proxiedImageUrl(comment.avatarUrl as String)) as ImageProvider', src)
    src = re.sub(r'\(?my\.avatarUrl as String\)?\.startsWith', '(my.avatarUrl as String).startsWith', src)
    src = re.sub(r'\(?comment\.avatarUrl as String\)?\.startsWith', '(comment.avatarUrl as String).startsWith', src)
    open(f,'w').write(src)

def fix_fluent_button_state():
    """fluent_ui 4.7 的 ButtonState 转换。

    fluent_ui 4.7.7 的定义（src/controls/utils/hover_button.dart）：
        abstract class ButtonState<T> {
          static ButtonState<T> all<T>(T value)
          static ButtonState<T> resolveWith<T>(ButtonStateResolver<T> callback)
        }
    注意两点：all/resolveWith 是**静态方法**（不是构造器，不能带 const），
    且必须带 `fluent.` 前缀；类型实参可能是 `Color?` 这种带 `?` 的形式。
    """
    for f in ['lib/themes/nipaplay/widgets/large_screen_editable_slider.dart',
              'lib/themes/nipaplay/widgets/fluent_settings_switch.dart']:
        if not os.path.exists(f): continue
        src = open(f).read()
        # [^>]+ 才能吃下 Color? 这类带问号的类型实参
        src = re.sub(r'\bMaterialStatePropertyAll<([^>]+)>\(', r'fluent.ButtonState.all<\1>(', src)
        src = re.sub(r'\bMaterialStateProperty\.resolveWith<([^>]+)>\(', r'fluent.ButtonState.resolveWith<\1>(', src)
        src = re.sub(r'\bMaterialStateProperty\.resolveWith\(', r'fluent.ButtonState.resolveWith(', src)
        src = re.sub(r'\bMaterialStateProperty\.all\(', r'fluent.ButtonState.all(', src)
        # fluent_ui 4.7 的 resolveWith 回调收到 Set<ButtonStates>
        src = src.replace('MaterialState.disabled', 'fluent.ButtonStates.disabled')
        # 静态方法调用不能带 const（const 只能在构造器上）
        src = re.sub(r'\bconst\s+(fluent\.ButtonState\.(?:all|resolveWith))', r'\1', src)
        open(f,'w').write(src)

def fix_media_kit_video_surface_producer():
    """Flutter 3.19 的 TextureRegistry.SurfaceProducer 没有 Callback / setCallback。

    media_kit_video 的 VideoOutput.java 实现了 3.24+ 才加入的
    TextureRegistry.SurfaceProducer.Callback 并在构造时 setCallback(this)，
    在 3.19 的 embedding 上编译不过（cannot find symbol: class Callback）。
    该插件本来就会手动驱动生命周期（dispose() 里调 onSurfaceCleanup()、
    setSurfaceSize() 里调 onSurfaceAvailable()），因此去掉接口、回调和
    @Override 注解即可，行为不变。
    """
    f = ('packages/media_kit_video/android/src/main/java/'
         'com/alexmercerind/media_kit_video/VideoOutput.java')
    if not os.path.exists(f): return
    src = open(f).read()
    src = src.replace('implements TextureRegistry.SurfaceProducer.Callback {', '{')
    src = re.sub(r'\n[ \t]*surfaceProducer\.setCallback\(this\);', '', src)
    src = re.sub(r'[ \t]*@Override\r?\n(?=[ \t]*public void onSurface(?:Available|Cleanup)\(\))',
                 '', src)
    open(f,'w').write(src)

def fix_manifest_override_library():
    """放行声明了更高 minSdk 的预编译 AAR（manifest 合并）。

    flutter_js 依赖 JitPack 上的 com.github.fast-development.android-js-runtimes:
    fastdev-jsruntimes-quickjs:0.3.6，该 AAR 的 AndroidManifest 声明了 minSdk 21，
    于是 legacy（minSdk 19）在 processReleaseMainManifest 阶段失败：

        uses-sdk:minSdkVersion 19 cannot be smaller than version 21 declared in
        library [...fastdev-jsruntimes-quickjs:0.3.6]

    AAR 是预编译产物，改不了它的 build.gradle，官方变通就是 tools:overrideLibrary。
    风险：API 19 上若真的调用到 quickjs，可能运行期崩溃——属于 legacy "尽力而为"
    范畴，构建阶段必须先放行。
    """
    f = 'android/app/src/main/AndroidManifest.xml'
    if not os.path.exists(f): return
    src = open(f).read()
    if 'io.abner.fastdev.android.quickjs' in src: return
    m = re.search(r'<manifest[^>]*>', src, re.S)
    if not m: return
    insert = ('\n    <!-- legacy(API 19): flutter_js 的 quickjs AAR 声明 minSdk 21，'
              '构建期放行（运行期风险已知） -->\n'
              '    <uses-sdk tools:overrideLibrary="io.abner.fastdev.android.quickjs" />')
    src = src[:m.end()] + insert + src[m.end():]
    open(f,'w').write(src)


def fix_cupertino_switch_track_color():
    """CupertinoSwitch.activeTrackColor (3.27+) -> trackColor (3.19)。

    只在确实使用 CupertinoSwitch 的文件里改名：Material 的 SliderThemeData 方向
    正好相反（3.19 叫 activeTrackColor，3.27+ 叫 trackColor），全局改名会把
    media_kit_video 的 SliderThemeData 改坏。
    """
    files = glob.glob('lib/**/*.dart', recursive=True) + \
            glob.glob('packages/*/lib/**/*.dart', recursive=True) + \
            glob.glob('third_party/*/lib/**/*.dart', recursive=True)
    for f in files:
        src = open(f).read()
        if 'CupertinoSwitch(' not in src or 'activeTrackColor:' not in src:
            continue
        src = src.replace('activeTrackColor:', 'trackColor:')
        open(f,'w').write(src)

def fix_cupertino_cancel_label():
    """CupertinoLocalizations.cancelButtonLabel -> MaterialLocalizations。

    3.19 的 CupertinoLocalizations 只有 cut/copy/paste/clear/selectAll/lookUp/
    searchWeb/share 这些标签，没有 cancelButtonLabel（该成员只在
    MaterialLocalizations 里）。应用顶层是 MaterialApp 且注册了
    GlobalMaterialLocalizations.delegate，运行时可用；只 import cupertino 的文件
    需要补上 material import。
    """
    files = glob.glob('lib/**/*.dart', recursive=True) + \
            glob.glob('packages/*/lib/**/*.dart', recursive=True) + \
            glob.glob('third_party/*/lib/**/*.dart', recursive=True)
    pat = re.compile(r'\bCupertinoLocalizations\.of\(([^)]+)\)\.cancelButtonLabel')
    for f in files:
        src = open(f).read()
        if not pat.search(src):
            continue
        src = pat.sub(r'MaterialLocalizations.of(\1).cancelButtonLabel', src)
        if ("import 'package:flutter/material.dart'" not in src
                and 'import "package:flutter/material.dart"' not in src):
            lines = src.split('\n')
            last_import = max((i for i, l in enumerate(lines) if l.startswith('import ')), default=-1)
            if last_import >= 0:
                lines.insert(last_import + 1, "import 'package:flutter/material.dart';")
                src = '\n'.join(lines)
        open(f,'w').write(src)

def fix_cupertino_min_size():
    """lib/themes/cupertino 下 CupertinoButton.minimumSize(Size) -> minSize(double)。

    值可能是字面量，也可能是表达式（如 CupertinoMediaSearchToolbar.controlHeight），
    并且常以多行 `const material.Size.square(...)` 形式出现——按 Size 结构解析，
    不能只匹配数字字面量。

    只作用于 cupertino 主题目录：Material 的 ButtonStyle.minimumSize 在 3.19
    本来就是正确参数名，改了反而错。
    """
    def to_double(expr):
        e = expr.strip()
        return e + '.0' if re.fullmatch(r'\d+', e) else e

    for f in glob.glob('lib/themes/cupertino/**/*.dart', recursive=True):
        src = open(f).read(); orig = src
        # Size.square(<expr>)
        src = re.sub(
            r'\bminimumSize:\s*(?:const\s+)?(?:material\.)?Size\.square\(\s*([^,()]+?)\s*,?\s*\)',
            lambda m: 'minSize: ' + to_double(m.group(1)), src, flags=re.S)
        # Size(<w>, <h>) -> 取max，折算成边长
        def _wh(m):
            try:
                return 'minSize: %d.0' % max(int(float(m.group(1))), int(float(m.group(2))))
            except ValueError:
                return m.group(0)
        src = re.sub(
            r'\bminimumSize:\s*(?:const\s+)?(?:material\.)?Size\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,?\s*\)',
            _wh, src, flags=re.S)
        src = re.sub(r'\bminimumSize:\s*(?:const\s+)?(?:material\.)?Size\.zero', 'minSize: 0.0', src)
        if src != orig: open(f,'w').write(src)

def fix_theme_maybe_brightness():
    """Theme.maybeBrightnessOf (3.27+) -> 3.19 等价写法。

    3.19 没有 Theme.maybeBrightnessOf；原语义是“没有 Material 祖先时返回 null”，
    用 findAncestorWidgetOfExactType<Theme>() 保持同样的可空行为。
    """
    f = 'packages/liquid_glass_widgets/lib/utils/glass_brightness.dart'
    if not os.path.exists(f): return
    src = open(f).read()
    src = src.replace('Theme.maybeBrightnessOf(context)',
                      'context.findAncestorWidgetOfExactType<Theme>()?.data.brightness')
    open(f,'w').write(src)

def fix_stretch_translate():
    """多行 4 参 translate/scale -> 3 参。

    单行形式（`..translateByDouble(a, b, 0.0, 1.0)`）已由 migrate 的
    `, 1.0)` 规则处理；这里只补多行写法：
        matrix.translate(
          A,
          B,
          0.0,
          1.0,
        );
    为防止误伤已经是 3 参的调用，要求尾部精确匹配 `0.0, 1.0` / `1.0, 1.0`。
    """
    f = 'packages/liquid_glass_widgets/lib/src/renderer/stretch.dart'
    if not os.path.exists(f): return
    src = open(f).read()
    src = re.sub(r'\.translate\(\s*([^;]*?),\s*0\.0\s*,\s*1\.0\s*,?\s*\)',
                 r'.translate(\1, 0.0)', src)
    src = re.sub(r'\.scale\(\s*([^;]*?),\s*1\.0\s*,\s*1\.0\s*,?\s*\)',
                 r'.scale(\1, 1.0)', src)
    open(f,'w').write(src)

def fix_media_kit_pop():
    """onPopInvokedWithResult -> onPopInvoked。"""
    import subprocess
    subprocess.run(['find', 'packages/media_kit_video', 'third_party/media-kit-upstream/media_kit_video',
                    '-name', 'fullscreen_inherited_widget.dart',
                    '-exec', 'sed', '-i',
                    's/onPopInvokedWithResult: (_, __)/onPopInvoked: (_)/g', '{}', '+'],
                   capture_output=True)

def fix_color_scheme():
    """ColorScheme 补 background/onBackground。"""
    f = 'lib/utils/app_theme.dart'
    if not os.path.exists(f): return
    src = open(f).read()
    src = src.replace(
        '          surface: Colors.white, // 表面颜色\n          onSurface: Colors.black87,',
        '          surface: Colors.white,\n          background: Colors.white,\n          onSurface: Colors.black87,\n          onBackground: Colors.black87,')
    src = src.replace(
        '          surface: Colors.black, // 表面颜色，深色模式下使用黑色。\n          onSurface: Colors.white, // 在表面颜色上的文本和图标颜色，确保对比度。',
        '          surface: Colors.black,\n          background: Colors.black,\n          onSurface: Colors.white,\n          onBackground: Colors.white,')
    open(f,'w').write(src)

if __name__ == '__main__':
    fix_cupertino_media_query()
    fix_cupertino_button_params()
    fix_focus_scope()
    fix_fluent_slider_params()
    fix_in_view_dialog()
    fix_glass_media_query()
    fix_color_rgba()
    fix_ui_false()
    fix_image_filter_shader()
    fix_backdrop_stub()
    fix_glass_spring()
    fix_animated_glass_indicator()
    fix_glass_spacing()
    fix_window_service_minimum_size()
    fix_bangumi_image()
    fix_fluent_button_state()
    fix_media_kit_video_surface_producer()
    fix_cupertino_min_size()
    fix_manifest_override_library()
    fix_cupertino_switch_track_color()
    fix_cupertino_cancel_label()
    fix_theme_maybe_brightness()
    fix_stretch_translate()
    fix_media_kit_pop()
    fix_color_scheme()
    print("manual fixes applied")
