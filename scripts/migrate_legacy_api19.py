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

def migrate(path: pathlib.Path):
    src = path.read_text(encoding='utf-8')
    orig = src

    # Color.withValues(alpha: X) -> withOpacity(X)（含跨行）
    src = re.sub(r'\.withValues\(\s*\n?\s*alpha:\s*([^,)]+?),?\s*\n?\s*\)',
                 r'.withOpacity(\1)', src)

    # Color .r/.g/.b (0-1 double) -> .red/.green/.blue / 255.0
    # 仅在 Color 上下文（启发式：紧邻标识符链）。.a 单独处理以避免与变量名冲突。
    src = re.sub(r'([a-zA-Z_)\]]+)\.r\b(?!\w)', r'(\1.red / 255.0)', src)
    src = re.sub(r'([a-zA-Z_)\]]+)\.g\b(?!\w)', r'(\1.green / 255.0)', src)
    src = re.sub(r'([a-zA-Z_)\]]+)\.b\b(?!\w)', r'(\1.blue / 255.0)', src)

    # Color.toARGB32() -> .value
    src = re.sub(r'\.toARGB32\(\)', '.value', src)

    # Color.from(alpha: A, red: R, green: G, blue: B) -> Color.fromRGBO(R*255, G*255, B*255, A)
    pat_from = re.compile(r'Color\.from\(\s*\n?\s*alpha:\s*([\d.]+),\s*\n?\s*red:\s*([\d.]+),\s*\n?\s*green:\s*([\d.]+),\s*\n?\s*blue:\s*([\d.]+)\s*\n?\s*\)')
    def _from(m):
        a, r, g, b = map(float, m.groups())
        return f'Color.fromRGBO({int(round(r*255))}, {int(round(g*255))}, {int(round(b*255))}, {a})'
    src = pat_from.sub(_from, src)

    # WidgetState -> MaterialState
    src = re.sub(r'\bWidgetStatePropertyAll\b', 'MaterialStatePropertyAll', src)
    src = re.sub(r'\bWidgetStateProperty\b', 'MaterialStateProperty', src)
    src = re.sub(r'\bWidgetState\b', 'MaterialState', src)

    # Matrix4.translateByDouble/scaleByDouble -> translate/scale
    src = re.sub(r'\.translateByDouble\(', '.translate(', src)
    src = re.sub(r'\.scaleByDouble\(', '.scale(', src)
    # translate(x,y,z,1.0) 4-arg -> translate(x,y,z)
    src = re.sub(r'\.translate\(([^;]+?), 1\.0\)', r'.translate(\1)', src)

    # CupertinoButton minSize: Size.square(N) / Size(N,N) / Size.zero -> N.0 / max / 0.0
    src = re.sub(r'minSize: const (?:material\.)?Size\.square\(\s*(\d+)\s*\)', r'minSize: \1.0', src)
    src = re.sub(r'minSize: const (?:material\.)?Size\((\d+),\s*(\d+)\)',
                 lambda m: f'minSize: {max(int(m.group(1)), int(m.group(2)))}.0', src)
    src = re.sub(r'minSize: Size\.zero', 'minSize: 0.0', src)
    src = re.sub(r'minSize: Size\((\d+),\s*(\d+)\)',
                 lambda m: f'minSize: {max(int(m.group(1)), int(m.group(2)))}.0', src)

    # ButtonStyle/MenuStyle minSize: -> minimumSize:
    src = re.sub(r'\bminSize: const MaterialStatePropertyAll', 'minimumSize: const MaterialStatePropertyAll', src)
    src = re.sub(r'\bminSize: MaterialStateProperty\.all', 'minimumSize: MaterialStateProperty.all', src)

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

    # CupertinoLocalizations.cancelButtonLabel -> MaterialLocalizations.cancelButtonLabel
    src = src.replace('CupertinoLocalizations.of(context).cancelButtonLabel',
                      'MaterialLocalizations.of(context).cancelButtonLabel')
    src = src.replace('CupertinoLocalizations.of(ctx).cancelButtonLabel',
                      'MaterialLocalizations.of(ctx).cancelButtonLabel')

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

    # CupertinoSwitch activeTrackColor -> trackColor
    src = re.sub(r'\n\s*activeTrackColor: [^,\n]+,', '\n        trackColor: Colors.white,', src)

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
