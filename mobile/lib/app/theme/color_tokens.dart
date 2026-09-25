import 'package:flutter/material.dart';

import 'accent_theme.dart';
import 'spacing_tokens.dart';

/// Doc 2 §2.1 color tokens.
class MilanColors extends ThemeExtension<MilanColors> {
  const MilanColors({
    required this.marigold500,
    required this.marigold700,
    required this.marigold100,
    required this.dhaka500,
    required this.dhaka700,
    required this.dhaka100,
    required this.pine500,
    required this.pine100,
    required this.ink900,
    required this.ink600,
    required this.ink400,
    required this.paper0,
    required this.paper100,
    required this.line200,
    required this.error500,
    required this.warning500,
  });

  final Color marigold500;
  final Color marigold700;
  final Color marigold100;
  final Color dhaka500;
  final Color dhaka700;
  final Color dhaka100;
  final Color pine500;
  final Color pine100;
  final Color ink900;
  final Color ink600;
  final Color ink400;
  final Color paper0;
  final Color paper100;
  final Color line200;
  final Color error500;
  final Color warning500;

  /// Default look (Milan Sky): pure-white surfaces, sky-blue action, and a
  /// deep-sky CTA color. Bright sky is for focus/selection; deep sky carries
  /// text-bearing buttons and links for AA contrast.
  static const light = MilanColors(
    marigold500: Color(0xFFF5A623),
    marigold700: Color(0xFFC97D0C),
    marigold100: Color(0xFFE0F2FE),
    dhaka500: Color(0xFF0369A1),
    dhaka700: Color(0xFF075985),
    dhaka100: Color(0xFFBAE6FD),
    pine500: Color(0xFF1F6F54),
    pine100: Color(0xFFDCEFE7),
    ink900: Color(0xFF0B1520),
    ink600: Color(0xFF38546B),
    ink400: Color(0xFF7C8794),
    paper0: Color(0xFFFFFFFF),
    paper100: Color(0xFFFFFFFF),
    line200: Color(0xFFDBEAFE),
    error500: Color(0xFFE0384C),
    warning500: Color(0xFFB8791A),
  );

    static const dark = MilanColors(
    marigold500: Color(0xFFF5A623),
    marigold700: Color(0xFFDD9520),
    marigold100: Color(0xFF3A2E17),
    dhaka500: Color(0xFF6E1B34),
    dhaka700: Color(0xFF4F0F26),
    dhaka100: Color(0xFF3A1A24),
    pine500: Color(0xFF1C644C),
    pine100: Color(0xFF17352C),
    ink900: Color(0xFFF2F5F9),
    ink600: Color(0xFFB9C2CE),
    ink400: Color(0xFF7C8794),
    paper0: Color(0xFF0E1116),
    paper100: Color(0xFF1A1F27),
    line200: Color(0xFF2A313C),
    error500: Color(0xFFE0384C),
    warning500: Color(0xFFA66D17),
  );

  @override
  MilanColors copyWith({
    Color? marigold500, Color? marigold700, Color? marigold100,
    Color? dhaka500, Color? dhaka700, Color? dhaka100,
    Color? pine500, Color? pine100,
    Color? ink900, Color? ink600, Color? ink400,
    Color? paper0, Color? paper100, Color? line200,
    Color? error500, Color? warning500,
  }) {
    return MilanColors(
      marigold500: marigold500 ?? this.marigold500,
      marigold700: marigold700 ?? this.marigold700,
      marigold100: marigold100 ?? this.marigold100,
      dhaka500: dhaka500 ?? this.dhaka500,
      dhaka700: dhaka700 ?? this.dhaka700,
      dhaka100: dhaka100 ?? this.dhaka100,
      pine500: pine500 ?? this.pine500,
      pine100: pine100 ?? this.pine100,
      ink900: ink900 ?? this.ink900,
      ink600: ink600 ?? this.ink600,
      ink400: ink400 ?? this.ink400,
      paper0: paper0 ?? this.paper0,
      paper100: paper100 ?? this.paper100,
      line200: line200 ?? this.line200,
      error500: error500 ?? this.error500,
      warning500: warning500 ?? this.warning500,
    );
  }

  @override
  MilanColors lerp(MilanColors? other, double t) {
    if (other == null) return this;
    return MilanColors(
      marigold500: Color.lerp(marigold500, other.marigold500, t)!,
      marigold700: Color.lerp(marigold700, other.marigold700, t)!,
      marigold100: Color.lerp(marigold100, other.marigold100, t)!,
      dhaka500: Color.lerp(dhaka500, other.dhaka500, t)!,
      dhaka700: Color.lerp(dhaka700, other.dhaka700, t)!,
      dhaka100: Color.lerp(dhaka100, other.dhaka100, t)!,
      pine500: Color.lerp(pine500, other.pine500, t)!,
      pine100: Color.lerp(pine100, other.pine100, t)!,
      ink900: Color.lerp(ink900, other.ink900, t)!,
      ink600: Color.lerp(ink600, other.ink600, t)!,
      ink400: Color.lerp(ink400, other.ink400, t)!,
      paper0: Color.lerp(paper0, other.paper0, t)!,
      paper100: Color.lerp(paper100, other.paper100, t)!,
      line200: Color.lerp(line200, other.line200, t)!,
      error500: Color.lerp(error500, other.error500, t)!,
      warning500: Color.lerp(warning500, other.warning500, t)!,
    );
  }
}

ColorScheme _schemeFrom(MilanColors c, Brightness brightness, Color? accent) {
  final action = accent ?? const Color(0xFF0369A1);
  final onAction = AccentThemeState.readableOn(action);
  return ColorScheme(
    brightness: brightness,
    primary: action,
    onPrimary: onAction,
    secondary: c.dhaka500,
    onSecondary: AccentThemeState.readableOn(c.dhaka500),
    error: c.error500,
    onError: Colors.white,
    surface: c.paper0,
    onSurface: c.ink900,
    surfaceContainerHighest: c.paper100,
    outlineVariant: c.line200,
  );
}

/// The user's accent (Settings → Appearance) recolors the WHOLE app —
/// buttons, switches, chips, the nav bar — not just chat bubbles.
ThemeData milanLightTheme([Color? accent]) =>
    _baseTheme(MilanColors.light, Brightness.light, accent);

ThemeData milanDarkTheme([Color? accent]) =>
    _baseTheme(MilanColors.dark, Brightness.dark, accent);

ThemeData _baseTheme(MilanColors colors, Brightness brightness,
    [Color? accent]) {
  final action = accent ?? const Color(0xFF0369A1);
  final onAction = AccentThemeState.readableOn(action);
  // doc 8 §A3.5: a real textTheme so any bare Text/TextStyle falls back to
  // Manrope (Sora for display roles) — not the platform default font.
  final textTheme = TextTheme(
    displayLarge: TextStyle(fontFamily: 'Sora', fontSize: 32, height: 40 / 32, fontWeight: FontWeight.w700),
    displayMedium: TextStyle(fontFamily: 'Sora', fontSize: 28, height: 36 / 28, fontWeight: FontWeight.w700),
    displaySmall: TextStyle(fontFamily: 'Sora', fontSize: 24, height: 32 / 24, fontWeight: FontWeight.w600),
    headlineLarge: TextStyle(fontFamily: 'Sora', fontSize: 24, height: 32 / 24, fontWeight: FontWeight.w600),
    headlineMedium: TextStyle(fontFamily: 'Sora', fontSize: 20, height: 28 / 20, fontWeight: FontWeight.w600),
    headlineSmall: TextStyle(fontFamily: 'Manrope', fontSize: 18, height: 24 / 18, fontWeight: FontWeight.w600),
    titleLarge: TextStyle(fontFamily: 'Manrope', fontSize: 16, height: 24 / 16, fontWeight: FontWeight.w600),
    titleMedium: TextStyle(fontFamily: 'Manrope', fontSize: 14, height: 20 / 14, fontWeight: FontWeight.w600),
    titleSmall: TextStyle(fontFamily: 'Manrope', fontSize: 12, height: 16 / 12, fontWeight: FontWeight.w600),
    bodyLarge: TextStyle(fontFamily: 'Manrope', fontSize: 16, height: 24 / 16, fontWeight: FontWeight.w400),
    bodyMedium: TextStyle(fontFamily: 'Manrope', fontSize: 14, height: 20 / 14, fontWeight: FontWeight.w400),
    bodySmall: TextStyle(fontFamily: 'Manrope', fontSize: 12, height: 16 / 12, fontWeight: FontWeight.w400),
    labelLarge: TextStyle(fontFamily: 'Manrope', fontSize: 14, height: 20 / 14, fontWeight: FontWeight.w600),
    labelMedium: TextStyle(fontFamily: 'Manrope', fontSize: 12, height: 16 / 12, fontWeight: FontWeight.w500),
    labelSmall: TextStyle(fontFamily: 'Manrope', fontSize: 11, height: 16 / 11, fontWeight: FontWeight.w600, letterSpacing: 0.04),
  );
  return ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: _schemeFrom(colors, brightness, accent),
    textTheme: textTheme,
    scaffoldBackgroundColor: colors.paper0,
    extensions: [colors],
    appBarTheme: AppBarTheme(
      backgroundColor: colors.paper0,
      foregroundColor: colors.ink900,
      elevation: 0,
      centerTitle: false,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: action,
        foregroundColor: onAction,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Spacing.radiusMd)),
        // Height-only touch target. Size.fromHeight() sets minimum WIDTH to
        // infinity, which starves sibling text in Rows/ListTiles down to one
        // character per line — full-width comes from stretch parents instead.
        minimumSize: const Size(0, 48),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: action,
        side: BorderSide(color: action),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Spacing.radiusMd)),
        minimumSize: const Size(0, 48),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: colors.paper100,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Spacing.radiusMd),
        borderSide: BorderSide(color: colors.line200),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(Spacing.radiusMd),
        borderSide: BorderSide(color: colors.line200),
      ),
    ),
    chipTheme: ChipThemeData(
      shape: StadiumBorder(side: BorderSide(color: colors.line200)),
      selectedColor: action.withValues(alpha: 0.14),
      secondarySelectedColor: action.withValues(alpha: 0.14),
      labelStyle: TextStyle(color: colors.ink900),
      secondaryLabelStyle: TextStyle(color: action),
    ),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith(
          (states) => states.contains(WidgetState.selected) ? Colors.white : colors.ink400),
      trackColor: WidgetStateProperty.resolveWith((states) =>
          states.contains(WidgetState.selected) ? action : colors.line200),
    ),
    progressIndicatorTheme: ProgressIndicatorThemeData(color: action),
  );
}

extension MilanColorsContext on BuildContext {
  MilanColors get milan => Theme.of(this).extension<MilanColors>()!;
}
