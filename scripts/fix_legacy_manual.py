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
    """minimumSize -> minSize (shim API)。"""
    for f in ['lib/services/desktop_player_window_service.dart',
              'lib/services/external_player_window_service.dart',
              'lib/services/external_player_console_window_service.dart']:
        if not os.path.exists(f): continue
        src = open(f).read()
        src = re.sub(r'\bminimumSize:', 'minSize:', src)
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
    """fluent_ui ButtonState 转换（import as fluent 前缀）。"""
    for f in ['lib/themes/nipaplay/widgets/large_screen_editable_slider.dart',
              'lib/themes/nipaplay/widgets/fluent_settings_switch.dart']:
        if not os.path.exists(f): continue
        src = open(f).read()
        # MaterialStateProperty -> fluent.ButtonState
        src = re.sub(r'\bMaterialStatePropertyAll<(\w+)>\(([^)]+)\)', r'fluent.ButtonState.all<\1>(\2)', src)
        src = re.sub(r'\bMaterialStateProperty\.resolveWith<(\w+)>\(', r'fluent.ButtonState.resolveWith<\1>(', src)
        src = re.sub(r'\bMaterialStateProperty\.resolveWith\(', r'fluent.ButtonState.resolveWith(', src)
        src = src.replace('MaterialState.disabled', 'fluent.ButtonStates.disabled')
        # const ButtonState.all -> ButtonState.all (非 const)
        src = src.replace('const fluent.ButtonState.all', 'fluent.ButtonState.all')
        # resolveWith with disabled states -> 简化为 all（避免 Set 类型不匹配）
        src = re.sub(
            r'fluent\.ButtonState\.resolveWith<Color\?>\(\(states\) \{\s*return states\.contains\(fluent\.ButtonStates\.disabled\)\s*\?\s*[^;]+;\s*\}\)',
            'fluent.ButtonState.all<Color?>(accent)', src)
        open(f,'w').write(src)

def fix_cupertino_search_toolbar():
    """multiline Size.square -> double。"""
    f = 'lib/themes/cupertino/widgets/cupertino_media_search_toolbar.dart'
    if not os.path.exists(f): return
    src = open(f).read()
    src = re.sub(r'minSize:\s*const material\.Size\.square\(\s*\n?\s*(\w+)\s*\n?\s*\)', r'minSize: \1', src)
    open(f,'w').write(src)

def fix_stretch_translate():
    """4-arg translate -> 3-arg。"""
    f = 'packages/liquid_glass_widgets/lib/src/renderer/stretch.dart'
    if not os.path.exists(f): return
    src = open(f).read()
    src = re.sub(r'\.translate\(([^;]+?), 1\.0\)', r'.translate(\1)', src)
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
    fix_cupertino_search_toolbar()
    fix_stretch_translate()
    fix_media_kit_pop()
    fix_color_scheme()
    print("manual fixes applied")
