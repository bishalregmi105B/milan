import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

/// Doc 2 §2.4 motion tokens. All durations respect reduced-motion at call sites.
abstract final class Motion {
  static const Duration swipeSpring = Duration(milliseconds: 420);
  static const Duration matchCelebration = Duration(milliseconds: 900);
  static const Duration saathiTypingPulse = Duration(milliseconds: 1200);
  static const Duration storyTransition = Duration(milliseconds: 220);
  static const Duration chatThemeCrossfade = Duration(milliseconds: 180);

  static const Curve springOut = Curves.elasticOut;
  static const Curve standard = Curves.easeOutCubic;

  /// Max card rotation at full drag (doc 2 §2.4).
  static const double maxSwipeRotationDeg = 12;

  static double dragToRotation(double dragExtent, double width) {
    final t = (dragExtent.abs() / width).clamp(0.0, 1.0);
    return dragExtent.sign * maxSwipeRotationDeg * t;
  }

  static bool prefersReducedMotion(BuildContext context) {
    // OS setting OR the in-app toggle (a11y settings drive the MediaQuery flag
    // at the app root, so this stays a single source of truth).
    return MediaQuery.disableAnimationsOf(context);
  }
}

/// Doc 5 §2.6 typing-indicator calibration, mirrored client-side.
Duration saathiTypingDelay(int responseCharCount) {
  final seconds = responseCharCount / 14.0;
  return Duration(milliseconds: ((seconds.clamp(0.8, 4.0)) * 1000).round());
}

enum DragDirection { none, left, right }

extension DragGestureX on DragUpdateDetails {
  DragDirection get horizontalDirection =>
      delta.dx > 0 ? DragDirection.right : DragDirection.left;
}
