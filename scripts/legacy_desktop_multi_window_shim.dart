// Legacy (Android 4.4 / Flutter 3.19) shim for the vendored
// desktop_multi_window package.
//
// The real vendored package targets Flutter 3.44's same-engine windowing API
// (package:flutter/src/widgets/_window.dart etc.), which does not exist in
// Flutter 3.19. Android builds never enable multi-window (isSupported is
// false there), so this shim reproduces the public API surface with
// plain runApp semantics to keep the legacy tree compiling.
// ignore_for_file: unused_element

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'dart:ui' show FlutterView;

import 'package:flutter/widgets.dart';

typedef DesktopWindowBuilder = Widget Function(
    BuildContext context, WindowController controller);

enum DesktopTransientWindowPlacement { above, below, right, pointer }

void runDesktopMultiWindowApp(Widget app) {
  runApp(app);
}

class DesktopMultiWindowHost extends StatelessWidget {
  const DesktopMultiWindowHost({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) => child;
}

class DesktopMultiWindow {
  static bool get isSupported {
    if (kIsWeb) return false;
    return defaultTargetPlatform == TargetPlatform.macOS ||
        defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.linux;
  }

  static bool get supportsInteractivePopupWindows => false;
  static bool get supportsTooltipWindows => false;

  static Future<WindowController> createWindow({
    String? title,
    Size? size,
    Size? minSize,
    Size? maxSize,
    bool frameless = false,
    bool center = false,
    double? aspectRatio,
    required DesktopWindowBuilder builder,
    VoidCallback? onClosed,
  }) async {
    throw UnsupportedError(
        'desktop_multi_window is not supported on this build');
  }

  static WindowController? maybeControllerOf(BuildContext context) => null;

  static WindowController controllerOf(BuildContext context) {
    throw UnsupportedError('no window controller in legacy shim');
  }

  static bool isSecondaryWindow(BuildContext context) => false;

  static WindowController? fromWindowId(int windowId) => null;

  static List<int> getAllSubWindowIds() => const [];

  static void attachTransientView(Object owner, Widget view) {}
  static void detachTransientView(Object owner) {}
  static Widget inheritTransientViewContext(
      BuildContext context, Widget child) {
    return child;
  }

  static DesktopPopupWindowController? createPopupWindow({
    BuildContext? context,
    Rect? anchorRect,
    Widget? view,
    Offset? anchor,
    Size? size,
    DesktopTransientWindowPlacement? placement,
    double? gap,
    VoidCallback? onClosed,
  }) =>
      null;

  static DesktopTooltipWindowController? createTooltipWindow({
    BuildContext? context,
    Rect? anchorRect,
    Widget? view,
    Offset? anchor,
    Size? size,
    DesktopTransientWindowPlacement? placement,
    double? gap,
    VoidCallback? onClosed,
  }) =>
      null;
}

class DesktopPopupWindowController extends ChangeNotifier {
  DesktopPopupWindowController._();
  bool get isClosed => true;
  FlutterView get flutterView => throw UnsupportedError('legacy shim');
  Future<void> get ready async {}
  Future<void> close() async {}
  Future<void> updatePosition({Rect? anchorRect, DesktopTransientWindowPlacement? placement, double? gap, Offset? position}) async {}
  Future<void> startDragging() async {}
  Future<void> updateDragging(Offset p) async {}
  Future<void> endDragging() async {}
}

class DesktopTooltipWindowController extends ChangeNotifier {
  DesktopTooltipWindowController._();
  bool get isClosed => true;
  FlutterView get flutterView => throw UnsupportedError('legacy shim');
  Future<void> get ready async {}
  Future<void> close() async {}
  Future<void> updatePosition({Rect? anchorRect, DesktopTransientWindowPlacement? placement, double? gap, Offset? position}) async {}
}

/// Stub window controller for the legacy shim. Callers only use it as an
/// opaque handle (close()/windowId may be referenced on desktop paths that
/// never execute on Android).
class WindowController extends ChangeNotifier {
  WindowController._();

  int get windowId => -1;
  bool get isClosed => true;
  bool get isFullscreen => false;
  bool get isAlwaysOnTop => false;
  String get title => '';
  Future<void> get ready async {}
  FlutterView? get flutterView => null;
  Future<void> close() async {}
  Future<void> show() async {}
  Future<void> hide() async {}
  Future<void> focus() async {}
  Future<void> setTitle(String t) async {}
  Future<void> setSize(Size s) async {}
  Future<void> setMinimumSize(Size? s) async {}
  Future<void> setFullscreen(bool v) async {}
  Future<void> setAlwaysOnTop(bool v) async {}
  Future<void> toggleAlwaysOnTop() async {}
  Future<void> setAspectRatio(double? r) async {}
  Future<void> setPictureInPictureMode({bool enabled = false, double? aspectRatio, String? placement}) async {}
  Future<void> startDragging() async {}
  Future<void> updateDragging([Offset? position]) async {}
  Future<void> endDragging() async {}
}

/// Widget that renders inside a native tooltip window (legacy shim: unused on
/// Android; kept so desktop-only call sites compile).
class DesktopTooltipWindow extends StatelessWidget {
  const DesktopTooltipWindow({
    super.key,
    required this.controller,
    required this.child,
  });

  final DesktopTooltipWindowController controller;
  final Widget child;

  @override
  Widget build(BuildContext context) => child;
}

class DesktopPopupWindow extends StatelessWidget {
  const DesktopPopupWindow({
    super.key,
    required this.controller,
    required this.child,
  });

  final DesktopPopupWindowController controller;
  final Widget child;

  @override
  Widget build(BuildContext context) => child;
}
