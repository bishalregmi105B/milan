import 'package:flutter/material.dart';

import 'color_tokens.dart';

/// Doc 2 §2.2 typography. Devanagari runs auto-swap to Noto Sans Devanagari
/// inside [AppText] — per-run, not per-screen, because Nepali/English
/// code-switching happens mid-sentence.
abstract final class MilanFonts {
  static const display = 'Sora';
  static const body = 'Manrope';
  static const devanagari = 'Noto Sans Devanagari';
}

bool containsDevanagari(String text) {
  for (final rune in text.runes) {
    if (rune >= 0x0900 && rune <= 0x097F) return true;
  }
  return false;
}

class AppText extends StatelessWidget {
  const AppText(
    this.data, {
    super.key,
    this.style,
    this.maxLines,
    this.overflow,
    this.textAlign,
  });

  final String data;
  final TextStyle? style;
  final int? maxLines;
  final TextOverflow? overflow;
  final TextAlign? textAlign;

  @override
  Widget build(BuildContext context) {
    final base = style ?? DefaultTextStyle.of(context).style;
    final spans = <InlineSpan>[];
    final buffer = StringBuffer();

    void flush() {
      if (buffer.isEmpty) return;
      final chunk = buffer.toString();
      buffer.clear();
      spans.add(TextSpan(
        text: chunk,
        style: containsDevanagari(chunk)
            ? base.copyWith(fontFamily: MilanFonts.devanagari)
            : base,
      ));
    }

    // Split on script boundaries so a single mixed line renders both scripts.
    var currentIsDeva = false;
    for (final rune in data.runes) {
      final isDeva = rune >= 0x0900 && rune <= 0x097F;
      if (isDeva != currentIsDeva && buffer.isNotEmpty) {
        flush();
      }
      currentIsDeva = isDeva;
      buffer.writeCharCode(rune);
    }
    flush();

    return RichText(
      maxLines: maxLines,
      overflow: overflow ?? TextOverflow.clip,
      textAlign: textAlign ?? TextAlign.start,
      text: TextSpan(children: spans, style: base),
    );
  }
}

/// Doc 2 §2.2 type scale helpers, tinted by the active [MilanColors].
extension MilanTypeScale on BuildContext {
  TextStyle get displayLarge => _t(MilanFonts.display, 32, 40, FontWeight.w700);
  TextStyle get h1 => _t(MilanFonts.display, 28, 36, FontWeight.w700);
  TextStyle get h2 => _t(MilanFonts.display, 24, 32, FontWeight.w600);
  TextStyle get h3 => _t(MilanFonts.display, 20, 28, FontWeight.w600);
  TextStyle get h4 => _t(MilanFonts.body, 18, 24, FontWeight.w600);
  TextStyle get bodyLarge => _t(MilanFonts.body, 16, 24, FontWeight.w400);
  TextStyle get bodyMedium => _t(MilanFonts.body, 14, 20, FontWeight.w400);
  TextStyle get caption => _t(MilanFonts.body, 12, 16, FontWeight.w500);
  TextStyle get overline =>
      _t(MilanFonts.body, 11, 16, FontWeight.w600, tracking: 0.04);

  TextStyle _t(String family, double size, double height, FontWeight weight,
      {double tracking = 0}) {
    // No textScalerOf pre-multiply here: app.dart installs the user's text
    // scale into MediaQuery, so pre-multiplying would scale twice (a 1.4
    // setting rendered at 1.96×). The scaler applies this once, globally.
    return TextStyle(
      fontFamily: family,
      fontSize: size,
      height: height / size,
      fontWeight: weight,
      letterSpacing: tracking,
      color: milan.ink900,
    );
  }
}
