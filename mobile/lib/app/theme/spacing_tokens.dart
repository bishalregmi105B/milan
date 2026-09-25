import 'dart:ui';

import 'package:flutter/material.dart';

/// Doc 2 §2.3 spacing, radius and elevation scale.
abstract final class Spacing {
  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double xxl = 32;
  static const double xxxl = 48;
  static const double huge = 64;

  static const double radiusSm = 8;
  static const double radiusMd = 16;
  static const double radiusLg = 24;
  static const double pill = 999;

  // Sky-tinted ambient shadow (deep sky #075985 at ~8% alpha) — matches the
  // Milan Sky system; was a rose/maroon tint left over from the old palette.
  static const Color shadowTint = Color(0x14075985);

  static List<BoxShadow> get raised => [
        BoxShadow(color: shadowTint, blurRadius: 12),
      ];

  static List<BoxShadow> get floating => [
        BoxShadow(color: shadowTint, blurRadius: 24),
      ];
}
