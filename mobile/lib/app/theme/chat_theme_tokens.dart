import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Doc 2 §2.7 — Chat Theme & Wallpaper system.
///
/// Private per viewer; resolved per scope ('global' / 'match:<id>' /
/// 'saathi:<characterId>') with order scoped override → global default →
/// factory default. Fully separate from the app-wide light/dark ColorScheme.

enum WallpaperType { preset, solid, gradient, customUpload, aiGenerated, photoSet }

enum BubbleShape { rounded, compact }

enum ChatThemeScopeKind { global, match, saathi }

@immutable
class ChatThemeScopeKey {
  const ChatThemeScopeKey.global()
      : kind = ChatThemeScopeKind.global,
        id = null;

  const ChatThemeScopeKey.match(this.id)
      : kind = ChatThemeScopeKind.match,
        assert(id != null);

  const ChatThemeScopeKey.saathi(this.id)
      : kind = ChatThemeScopeKind.saathi,
        assert(id != null);

  final ChatThemeScopeKind kind;
  final String? id;

  String get storageKey {
    switch (kind) {
      case ChatThemeScopeKind.global:
        return 'global';
      case ChatThemeScopeKind.match:
        return 'match:$id';
      case ChatThemeScopeKind.saathi:
        return 'saathi:$id';
    }
  }

  @override
  bool operator ==(Object other) => other is ChatThemeScopeKey && other.storageKey == storageKey;

  @override
  int get hashCode => storageKey.hashCode;
}

@immutable
class ChatWallpaperTheme {
  const ChatWallpaperTheme({
    required this.wallpaperType,
    required this.wallpaperValue,
    this.bubbleColorSent,
    this.bubbleColorReceived,
    this.bubbleShape = BubbleShape.rounded,
    this.doodleOverlayId,
    this.textScale,
    this.darkModeBrightness,
    this.presetId,
    this.photoUrls = const [],
  });

  final WallpaperType wallpaperType;
  final String wallpaperValue;
  /// Multi-photo rotating wallpaper (premium). Empty for single-photo themes.
  final List<String> photoUrls;
  final Color? bubbleColorSent;
  final Color? bubbleColorReceived;
  final BubbleShape bubbleShape;
  final String? doodleOverlayId;
  final double? textScale;
  final double? darkModeBrightness;
  final String? presetId;

  static const factoryDefault = ChatWallpaperTheme(
    wallpaperType: WallpaperType.preset,
    wallpaperValue: 'brand_marigold_warm',
    bubbleColorSent: Color(0xFFF5A623),
    bubbleColorReceived: Color(0xFFF3DCE2),
    bubbleShape: BubbleShape.rounded,
  );

  ChatWallpaperTheme copyWith({
    WallpaperType? wallpaperType,
    String? wallpaperValue,
    List<String>? photoUrls,
    Color? bubbleColorSent,
    Color? bubbleColorReceived,
    BubbleShape? bubbleShape,
    String? doodleOverlayId,
    double? textScale,
    double? darkModeBrightness,
    String? presetId,
    bool clearDoodle = false,
    bool clearTextScale = false,
    bool clearBrightness = false,
  }) {
    return ChatWallpaperTheme(
      wallpaperType: wallpaperType ?? this.wallpaperType,
      wallpaperValue: wallpaperValue ?? this.wallpaperValue,
      photoUrls: photoUrls ?? this.photoUrls,
      bubbleColorSent: bubbleColorSent ?? this.bubbleColorSent,
      bubbleColorReceived: bubbleColorReceived ?? this.bubbleColorReceived,
      bubbleShape: bubbleShape ?? this.bubbleShape,
      doodleOverlayId: clearDoodle ? null : (doodleOverlayId ?? this.doodleOverlayId),
      textScale: clearTextScale ? null : (textScale ?? this.textScale),
      darkModeBrightness:
          clearBrightness ? null : (darkModeBrightness ?? this.darkModeBrightness),
      presetId: presetId ?? this.presetId,
    );
  }

  Map<String, dynamic> toBackendJson({required String scope, String? scopeId}) => {
        'scope': scope,
        if (scopeId != null) 'scope_id': scopeId,
        'wallpaper_type': wallpaperType.name,
        'wallpaper_value': wallpaperValue,
        'bubble_color_sent': _toHex(bubbleColorSent),
        'bubble_color_received': _toHex(bubbleColorReceived),
        'bubble_shape': bubbleShape.name,
        'doodle_overlay_id': doodleOverlayId,
        'text_scale': textScale,
        'dark_mode_brightness': darkModeBrightness,
      };

  static ChatWallpaperTheme fromBackendJson(Map<String, dynamic> json) {
    return ChatWallpaperTheme(
      wallpaperType: WallpaperType.values.firstWhere(
        (t) => t.name == json['wallpaper_type'],
        orElse: () => WallpaperType.preset,
      ),
      wallpaperValue: (json['wallpaper_value'] as String?) ?? 'brand_marigold_warm',
      bubbleColorSent: _fromHex(json['bubble_color_sent'] as String?),
      bubbleColorReceived: _fromHex(json['bubble_color_received'] as String?),
      bubbleShape: json['bubble_shape'] == 'compact'
          ? BubbleShape.compact
          : BubbleShape.rounded,
      doodleOverlayId: json['doodle_overlay_id'] as String?,
      textScale: (json['text_scale'] as num?)?.toDouble(),
      darkModeBrightness: (json['dark_mode_brightness'] as num?)?.toDouble(),
      presetId: null,
    );
  }
}

String? _toHex(Color? c) => c == null ? null : c.toARGB32().toRadixString(16).padLeft(8, '0');

Color? _fromHex(String? hex) {
  if (hex == null || hex.isEmpty) return null;
  var value = hex.replaceFirst('#', '');
  if (value.length == 3 || value.length == 6) value = 'FF$value';
  final parsed = int.tryParse(value, radix: 16);
  return parsed == null ? null : Color(parsed);
}

/// WCAG-AA-equivalent contrast check (doc 2 §2.7.3): reject combinations that
/// would render message text unreadable before "Apply" is enabled.
double contrastRatio(Color a, Color b) {
  final la = _relativeLuminance(a);
  final lb = _relativeLuminance(b);
  final lighter = la > lb ? la : lb;
  final darker = la > lb ? lb : la;
  return (lighter + 0.05) / (darker + 0.05);
}

double _relativeLuminance(Color color) {
  double channel(double v) =>
      v <= 0.03928 ? v / 12.92 : math.pow((v + 0.055) / 1.055, 2.4).toDouble();
  return 0.2126 * channel(color.r) +
      0.7152 * channel(color.g) +
      0.0722 * channel(color.b);
}

bool passesContrast(ChatWallpaperTheme theme) {
  final sent = theme.bubbleColorSent;
  if (sent == null) return true;
  // Bubbles render ink900 (dark) message text — require AA-equivalent
  // contrast between the chosen fill and that text color (doc 2 §2.7.3).
  return contrastRatio(sent, const Color(0xFF1F1B16)) >= 4.5 &&
      contrastRatio(theme.bubbleColorReceived ?? const Color(0xFFF3DCE2),
              const Color(0xFF1F1B16)) >=
          4.5;
}
