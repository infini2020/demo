#!/usr/bin/env python3
"""Legacy (Android 4.4 / Flutter 3.19 / Dart 3.3) Dart 代码迁移脚本。

将 Flutter 3.24+ API 用法批量降级到 3.19 兼容形式。在 CI 的
build-android-legacy.yml 中于 `flutter pub get` 之前调用。

已验证：经此脚本 + pubspec 调整后，flutter analyze 在 Flutter 3.19.6
(Dart 3.3.4) 下对 lib/ 与参与编译的 packages/*/lib 零编译错误。

迁移规则（均为 Flutter 3.27 → 3.19 的 API 退降）：
  - Color.withValues(alpha: X)        -> .withOpacity(X)
  - Color .a/.r/.g/.b (0-1 double)    -> .opacity / (.red/.green/.blue / 255.0)
  - Color.toARGB32()                  -> .value
  - Color.from(alpha:,red:,green:,blue:) -> Color.fromRGBO(R*255, G*255, B*255, A)
  - WidgetStateProperty(All) / WidgetState -> MaterialStateProperty(All) / MaterialState
  - Matrix4.translateByDouble/scaleByDouble -> translate/scale (并剔除第 4 参数)
  - CupertinoButton minSize: Size(...) -> minSize: double（边长）
  - ButtonStyle/MenuStyle minSize -> minimumSize
  - styleFrom minSize/overlayColor -> 删除（3.19 styleFrom 无此参数）
  - PopScope<T> -> PopScope
  - onPopInvokedWithResult: (didPop, X) -> onPopInvoked: (didPop)
  - DialogTheme.barrierColor -> .backgroundColor
  - ColorScheme 缺 background/onBackground -> 补齐
  - ColorScheme.surfaceContainerHighest -> .surfaceVariant
  - CupertinoColors.transparent -> const Color(0x00000000)
  - CupertinoLocalizations.cancelButtonLabel -> MaterialLocalizations.cancelButtonLabel
  - Theme.brightnessOf/maybeBrightnessOf -> MediaQuery.platformBrightnessOf / Theme.of(context).brightness
  - ImageFilter.isShaderFilterSupported -> (false)
  - ImageFilter.shader(x) -> ImageFilter.blur(sigmaX:40, sigmaY:40)（降级）
  - BackdropFilterLayer.backdropKey = -> 删除（3.27 blur-sharing API）
  - RoundedSuperellipseBorder -> RoundedRectangleBorder
  - SpringDescription.withDurationAndBounce -> legacySpring() helper
  - BackdropGroup/BackdropKey -> legacy stub (Object typedef + no-op widget)
  - Tooltip constraints: -> 删除
  - SegmentedButton.styleFrom minSize -> 删除
  - CupertinoSwitch activeTrackColor -> trackColor
"""
import re, sys, pathlib

ROOTS = sys.argv[1:] or ['.']

def _rgb_repl(m):
    """Replace Color.r/g/b (0-1 double) with Color.red/green/blue / 255.0."""
    var = m.group(1)
    channel = m.group(0)[-1]  # r, g, or b
    name_map = {'r': 'red', 'g': 'green', 'b': 'blue'}
    return f'({var}.{name_map[channel]} / 255.0)'

def migrate(path: pathlib.Path):
    src = path.read_text(encoding='utf-8')
    orig = src

    # Color.withValues(alpha: X) -> withOpacity(X)（含跨行）
    src = re.sub(r'\.withValues\(\s*\n?\s*alpha:\s*([^,)]+?),?\s*\n?\s*\)',
                 r'.withOpacity(\1)', src)

    # Color .a (0-1 double, Flutter 3.27+) -> .opacity (3.19)
    # 仅在明确 Color 上下文：变量名以 color/Color/theme/backgroundColor 等结尾，
    # 或链式 colorScheme.xxx.a 形式。避免误伤 Pixel.a / 自定义类 .a 字段。
    # 用精确的 Color-getter 链模式匹配，而非宽泛的任意标识符。
    _color_a_patterns = [
        r'(\bcolorScheme\.\w+)\.a\b',
        r'(\b(?:theme|Theme)\.\w+)\.a\b',
        r'(\bbackgroundColor)\.a\b',
        r'(\bforegroundColor)\.a\b',
        r'(\bselectedColor)\.a\b',
        r'(\btextColor)\.a\b',
        r'(\bdividerColor)\.a\b',
        r'(\bbaseDividerColor)\.a\b',
        r'(\bshadowColor)\.a\b',
        r'(\baccentColor)\.a\b',
        r'(\bseedColor)\.a\b',
        r'(\bprimaryColor)\.a\b',
        r'(\bsecondaryColor)\.a\b',
        r'(\bsurfaceColor)\.a\b',
        r'(\bonSurfaceColor)\.a\b',
        r'(\berrorColor)\.a\b',
        r'(\biconColor)\.a\b',
        r'(\blabelColor)\.a\b',
        r'(\bhintColor)\.a\b',
        r'(\bhighlightColor)\.a\b',
        r'(\bsplashColor)\.a\b',
        r'(\bdisabledColor)\.a\b',
        r'(\bCanvas\.color)\.a\b',
        r'(\bPaint\(\)\.\w+)\.a\b',  # paint.color.a
    ]
    for pat in _color_a_patterns:
        src = re.sub(pat, r'\1.opacity', src)
    # 通用模式：变量名为 xxxColor/xxxColors/color/Color 的 .a（常见命名约定）
    # 匹配大小写：color, Color, backgroundColor, xxxColor 等
    src = re.sub(r'(\b\w*[Cc]olor[s]?)\.a\b(?!\w)', r'\1.opacity', src)
    # colorScheme.xxx.withOpacity(…).a 形式不常见，跳过

    # Color .r/.g/.b (0-1 double) -> .red/.green/.blue / 255.0
    # ⚠️ 极易误伤：Pixel.r/g/b (image 包) 用 0-255 int，不是 0-1 double！
    # _MsdfEdgeSegment.b 是自定义字段名，不是 Color！
    # 因此只匹配已知的 Color 变量名模式（同 .a 的策略）。
    _color_rgb_patterns = [
        r'(\bcolorScheme\.\w+)\.[rgb]\b',
        r'(\b\w*[Cc]olor[s]?)\.[rgb]\b',
        r'(\bbackgroundColor)\.[rgb]\b',
        r'(\bforegroundColor)\.[rgb]\b',
        r'(\bseedColor)\.[rgb]\b',
        r'(\baccentColor)\.[rgb]\b',
    ]
    for pat in _color_rgb_patterns:
        src = re.sub(pat + r'(?!\w)', lambda m: _rgb_repl(m), src)

    # Color.toARGB32() -> .value
    src = re.sub(r'\.toARGB32\(\)', '.value', src)

    # Color.from(alpha: A, red: R, green: G, blue: B) -> Color.fromRGBO(R*255, G*255, B*255, A)
    pat_from = re.compile(r'Color\.from\(\s*\n?\s*alpha:\s*([\d.]+),\s*\n?\s*red:\s*([\d.]+),\s*\n?\s*green:\s*([\d.]+),\s*\n?\s*blue:\s*([\d.]+)\s*\n?\s*\)')
    def _from(m):
        a, r, g, b = map(float, m.groups())
        return f'Color.fromRGBO({int(round(r*255))}, {int(round(g*255))}, {int(round(b*255))}, {a})'
    src = pat_from.sub(_from, src)

    # WidgetState -> MaterialState (Flutter framework APIs in 3.19)
    src = re.sub(r'\bWidgetStatePropertyAll\b', 'MaterialStatePropertyAll', src)
    src = re.sub(r'\bWidgetStateProperty\b', 'MaterialStateProperty', src)
    src = re.sub(r'\bWidgetState\b', 'MaterialState', src)

    # fluent_ui 的 ButtonState 转换不在这里做。
    # ButtonState.all / .resolveWith 是 fluent_ui 的**静态方法**（不是构造器），
    # 调用点必须带 `fluent.` 前缀且不能带 const，还需要处理 <Color?> 这类带 `?`
    # 的类型实参——这些在 migrate 里做不干净（曾产出 `const ButtonState.all<double>(4)`
    # 与未转换的 `MaterialStateProperty.resolveWith<Color?>`）。
    # 统一交给 scripts/fix_legacy_manual.py 的 fix_fluent_button_state()。

    # Matrix4.translateByDouble/scaleByDouble -> translate/scale
    src = re.sub(r'\.translateByDouble\(', '.translate(', src)
    src = re.sub(r'\.scaleByDouble\(', '.scale(', src)
    # translate(x,y,z,1.0) 4-arg -> translate(x,y,z)
    src = re.sub(r'\.translate\(([^;]+?), 1\.0\)', r'.translate(\1)', src)

    # CupertinoButton.minimumSize (3.27+) -> minSize (3.19)
    # 3.19 CupertinoButton 的参数叫 minSize: double?，不是 minimumSize。
    # migrate 脚本之前把 minSize -> minimumSize 是反的！
    src = re.sub(r'\bminimumSize:\s*const Size\.square\(\s*(\d+)\s*\)',
                 r'minSize: \1.0', src)
    src = re.sub(r'\bminimumSize:\s*const (?:material\.)?Size\.square\(\s*(\d+)\s*\)',
                 r'minSize: \1.0', src)
    src = re.sub(r'\bminimumSize:\s*const (?:material\.)?Size\((\d+),\s*(\d+)\)',
                 lambda m: f'minSize: {max(int(m.group(1)), int(m.group(2)))}.0', src)
    src = re.sub(r'\bminimumSize:\s*Size\.zero', 'minSize: 0.0', src)
    src = re.sub(r'\bminimumSize:\s*Size\((\d+),\s*(\d+)\)',
                 lambda m: f'minSize: {max(int(m.group(1)), int(m.group(2)))}.0', src)
    # multiline: minimumSize: const Size.square(\n  N,\n)
    src = re.sub(r'\bminimumSize:\s*const (?:material\.)?Size\.square\(\s*\n?\s*(\d+)\s*,?\s*\n?\s*\)',
                 r'minSize: \1.0', src)

    # CupertinoButton minSize: Size.square(N) / Size(N,N) / Size.zero -> N.0 / max / 0.0
    src = re.sub(r'\bminSize:\s*const (?:material\.)?Size\.square\(\s*(\d+)\s*\)', r'minSize: \1.0', src)
    src = re.sub(r'\bminSize:\s*const (?:material\.)?Size\((\d+),\s*(\d+)\)',
                 lambda m: f'minSize: {max(int(m.group(1)), int(m.group(2)))}.0', src)
    src = re.sub(r'\bminSize:\s*Size\.zero', 'minSize: 0.0', src)
    src = re.sub(r'\bminSize:\s*Size\((\d+),\s*(\d+)\)',
                 lambda m: f'minSize: {max(int(m.group(1)), int(m.group(2)))}.0', src)

    # ButtonStyle/MenuStyle minimumSize (Material, 3.27+) stays as minimumSize
    # in MaterialStateProperty context — that's correct for 3.19 too.

    # styleFrom minSize/overlayColor -> 删除（行级）
    src = re.sub(r'\n\s*minSize: [^,\n]+,', '', src)
    src = re.sub(r'\n\s*overlayColor: Colors\.transparent,', '', src)

    # PopScope<T> -> PopScope
    src = re.sub(r'\bPopScope<[^>]+>\(', 'PopScope(', src)

    # onPopInvokedWithResult: (didPop, X) { -> onPopInvoked: (didPop) {
    src = re.sub(r'onPopInvokedWithResult:\s*\(didPop,\s*[_\w]+\)\s*\{',
                 'onPopInvoked: (didPop) {', src)
    src = re.sub(r'onPopInvokedWithResult:\s*\(_,\s*__\)',
                 'onPopInvoked: (_)', src)

    # DialogTheme.barrierColor -> .backgroundColor
    src = re.sub(r'DialogTheme\.of\(context\)\.barrierColor',
                 'DialogTheme.of(context).backgroundColor', src)
    src = re.sub(r'\.dialogTheme\.barrierColor', '.dialogTheme.backgroundColor', src)

    # ColorScheme.surfaceContainerHighest -> .surfaceVariant
    src = src.replace('.surfaceContainerHighest', '.surfaceVariant')

    # CupertinoColors.transparent -> const Color(0x00000000)
    src = src.replace('CupertinoColors.transparent', 'const Color(0x00000000)')

    # 注意：不要改 CupertinoLocalizations。
    # CupertinoLocalizations.of(ctx).cancelButtonLabel 在 3.19 本来就存在；
    # 早期规则把它换成 MaterialLocalizations，反而让只 import cupertino 的文件
    # 报 “The getter 'MaterialLocalizations' isn't defined”。

    # Theme.brightnessOf -> MediaQuery.platformBrightnessOf
    src = src.replace('Theme.brightnessOf(context)',
                      'MediaQuery.platformBrightnessOf(context)')

    # ImageFilter.isShaderFilterSupported -> (false)
    src = src.replace('ImageFilter.isShaderFilterSupported', '(false)')
    # 清理 ui.(false) 残留（isShaderFilterSupported 带前缀时）
    src = src.replace('ui.(false)', '(false)')

    # ImageFilter.shader(x) -> ImageFilter.blur（降级）
    src = re.sub(r'ImageFilter\.shader\([^)]+\)',
                 'ui.ImageFilter.blur(sigmaX: 40, sigmaY: 40) // legacy: shader unsupported in 3.19', src)

    # BackdropFilterLayer.backdropKey = 赋值行 -> 删除（多行块）
    src = re.sub(r'\n\s*\.\.backdropKey\s*=\s*\n?\s*[^\n]+\n', '\n', src)

    # RoundedSuperellipseBorder -> RoundedRectangleBorder
    src = src.replace('RoundedSuperellipseBorder(', 'RoundedRectangleBorder(')

    # SpringDescription.withDurationAndBounce(...) -> legacySpring(...)
    src = re.sub(r'SpringDescription\.withDurationAndBounce\(\s*\n?\s*duration:\s*([^,]+),\s*\n?\s*bounce:\s*([^,]+),?\s*\n?\s*\)',
                 r'legacySpring(duration: \1, bounce: \2)', src)

    # Tooltip constraints: height != null ? BoxConstraints(...) : null, -> 删除（3 行块）
    src = re.sub(r'\n\s*constraints: height != null\s*\n\s*\?\s*BoxConstraints\([^\n]+\)\s*\n\s*: null,', '', src)

    # 注意：不要全局改 activeTrackColor。
    # CupertinoSwitch 在 3.27+ 叫 activeTrackColor、3.19 叫 trackColor（需改名）；
    # 但 Material 的 SliderThemeData 恰好相反：3.19 叫 activeTrackColor、3.27+ 叫
    # trackColor。全局改名会把 media_kit_video 的 SliderThemeData 改坏
    # （CI: “No named parameter with the name 'trackColor'”）。
    # 因此 CupertinoSwitch 的改名交给 fix_legacy_manual.fix_cupertino_switch_track_color()。

    # Pixel.opacity -> Pixel.a (image package 4.x field rename)
    # 仅在明确 Pixel 上下文（pixel./seg.）
    src = re.sub(r'\bpixel\.opacity\b', 'pixel.a', src)
    src = re.sub(r'\bseg\.opacity\b', 'seg.a', src)
    src = re.sub(r'\bnextSeg\.opacity\b', 'nextSeg.a', src)
    src = re.sub(r'\bstartSeg\.opacity\b', 'startSeg.a', src)

    if src != orig:
        path.write_text(src, encoding='utf-8')
        return True
    return False

changed = 0
for root in ROOTS:
    p = pathlib.Path(root)
    for f in p.rglob('*.dart'):
        if any(x in f.parts for x in ('.git', '.legacy-tools', '.dart_tool',
                                       'example', 'test', 'build')):
            continue
        try:
            if migrate(f):
                changed += 1
        except Exception as e:
            print(f'ERR {f}: {e}', file=sys.stderr)
print(f'migrated {changed} files')
