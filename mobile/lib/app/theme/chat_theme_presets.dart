import 'package:flutter/material.dart';

import 'chat_theme_tokens.dart';

/// Doc 2 §2.7.2 — Milan-native preset packs (no third-party wallpaper library).
/// Vector-friendly definitions; raster assets live under assets/theme_presets/.
@immutable
class ChatThemePreset {
  const ChatThemePreset({
    required this.id,
    required this.pack,
    required this.name,
    required this.theme,
  });

  final String id;
  final String pack;
  final String name;
  final ChatWallpaperTheme theme;
}

abstract final class MilanChatPresets {
  static const brand = <ChatThemePreset>[
    ChatThemePreset(
      id: 'brand_marigold_warm',
      pack: 'brand',
      name: 'Marigold Warm',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.preset,
        wallpaperValue: 'brand_marigold_warm',
        bubbleColorSent: Color(0xFFF5A623),
        bubbleColorReceived: Color(0xFFF3DCE2),
      ),
    ),
    ChatThemePreset(
      id: 'brand_dhaka_dusk',
      pack: 'brand',
      name: 'Dhaka Dusk',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.gradient,
        wallpaperValue: '#7B1E3A|#591129',
        bubbleColorSent: Color(0xFFC97D0C),
        bubbleColorReceived: Color(0xFFF3DCE2),
      ),
    ),
    ChatThemePreset(
      id: 'brand_pine_calm',
      pack: 'brand',
      name: 'Pine Calm',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.solid,
        wallpaperValue: '#1F6F54',
        bubbleColorSent: Color(0xFF1F6F54),
        bubbleColorReceived: Color(0xFFDCEFE7),
      ),
    ),
  ];

  static const festival = <ChatThemePreset>[
    ChatThemePreset(
      id: 'festival_dashain',
      pack: 'festival',
      name: 'Dashain Tika',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.preset,
        wallpaperValue: 'festival_dashain',
        bubbleColorSent: Color(0xFFB8791A),
        bubbleColorReceived: Color(0xFFFDE9C8),
        doodleOverlayId: 'marigold_petals',
      ),
    ),
    ChatThemePreset(
      id: 'festival_tihar',
      pack: 'festival',
      name: 'Tihar Diyo',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.preset,
        wallpaperValue: 'festival_tihar',
        bubbleColorSent: Color(0xFFC97D0C),
        bubbleColorReceived: Color(0xFFFFF3DC),
        doodleOverlayId: 'paisley',
      ),
    ),
    ChatThemePreset(
      id: 'festival_holi',
      pack: 'festival',
      name: 'Holi Rang',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.gradient,
        wallpaperValue: '#E85D9E|#F5A623',
        bubbleColorSent: Color(0xFF7B1E3A),
        bubbleColorReceived: Color(0xFFFFFBF5),
      ),
    ),
    ChatThemePreset(
      id: 'festival_teej',
      pack: 'festival',
      name: 'Teej Hariyali',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.gradient,
        wallpaperValue: '#1F6F54|#59A96A',
        bubbleColorSent: Color(0xFF591129),
        bubbleColorReceived: Color(0xFFDCEFE7),
      ),
    ),
  ];

  static const nature = <ChatThemePreset>[
    ChatThemePreset(
      id: 'nature_himalaya',
      pack: 'nature',
      name: 'Himalaya Skyline',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.preset,
        wallpaperValue: 'nature_himalaya',
        bubbleColorSent: Color(0xFF2B5F8A),
        bubbleColorReceived: Color(0xFFEAF2F8),
        doodleOverlayId: 'mountain_ridge',
      ),
    ),
    ChatThemePreset(
      id: 'nature_terrace_hills',
      pack: 'nature',
      name: 'Terraced Hills',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.gradient,
        wallpaperValue: '#4C7A3F|#A8C686',
        bubbleColorSent: Color(0xFF2E5229),
        bubbleColorReceived: Color(0xFFF2F7EC),
      ),
    ),
    ChatThemePreset(
      id: 'nature_rhododendron',
      pack: 'nature',
      name: 'Rhododendron Line-Art',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.preset,
        wallpaperValue: 'nature_rhododendron',
        bubbleColorSent: Color(0xFFB33A4B),
        bubbleColorReceived: Color(0xFFFBEDEF),
        doodleOverlayId: 'mithila_lines',
      ),
    ),
    ChatThemePreset(
      id: 'nature_monsoon_cloud',
      pack: 'nature',
      name: 'Monsoon Cloud',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.gradient,
        wallpaperValue: '#43535C|#93A8B4',
        bubbleColorSent: Color(0xFF34424A),
        bubbleColorReceived: Color(0xFFEDF1F4),
      ),
    ),
  ];

  static const minimal = <ChatThemePreset>[
    ChatThemePreset(
      id: 'minimal_paper',
      pack: 'minimal',
      name: 'Paper Tone',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.solid,
        wallpaperValue: '#FFFBF5',
        bubbleColorSent: Color(0xFFF5A623),
        bubbleColorReceived: Color(0xFFF5F0E6),
      ),
    ),
    ChatThemePreset(
      id: 'minimal_soft_slate',
      pack: 'minimal',
      name: 'Soft Slate',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.gradient,
        wallpaperValue: '#F5F0E6|#E8E1D3',
        bubbleColorSent: Color(0xFF4A443C),
        bubbleColorReceived: Color(0xFFFFFFFF),
      ),
    ),
  ];

  /// Doc 2 §2.7.2 — one signature look per curated Saathi character (doc 5 §2.2),
  /// dhaka-forward, visually distinct from any match chat.
  static const saathi = <ChatThemePreset>[
    ChatThemePreset(
      id: 'saathi_asha',
      pack: 'saathi',
      name: 'Saathi — Asha',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.preset,
        wallpaperValue: 'saathi_asha',
        bubbleColorSent: Color(0xFF7B1E3A),
        bubbleColorReceived: Color(0xFFF3DCE2),
      ),
    ),
    ChatThemePreset(
      id: 'saathi_bibek',
      pack: 'saathi',
      name: 'Saathi — Bibek',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.preset,
        wallpaperValue: 'saathi_bibek',
        bubbleColorSent: Color(0xFF591129),
        bubbleColorReceived: Color(0xFFEFD9DF),
      ),
    ),
    ChatThemePreset(
      id: 'saathi_priya',
      pack: 'saathi',
      name: 'Saathi — Priya',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.preset,
        wallpaperValue: 'saathi_priya',
        bubbleColorSent: Color(0xFF8A4A63),
        bubbleColorReceived: Color(0xFFF7EBEF),
      ),
    ),
    ChatThemePreset(
      id: 'saathi_sagar',
      pack: 'saathi',
      name: 'Saathi — Sagar',
      theme: ChatWallpaperTheme(
        wallpaperType: WallpaperType.preset,
        wallpaperValue: 'saathi_sagar',
        bubbleColorSent: Color(0xFF6E1B34),
        bubbleColorReceived: Color(0xFFEADCE1),
      ),
    ),
  ];

  static const all = <ChatThemePreset>[
    ...brand,
    ...festival,
    ...nature,
    ...minimal,
    ...saathi,
  ];

  static ChatThemePreset? byId(String? id) {
    if (id == null) return null;
    for (final preset in all) {
      if (preset.id == id) return preset;
    }
    return null;
  }

  /// Doc 5 §2.2 — each character's signature default applied on first chat open.
  static ChatWallpaperTheme defaultForSaathiCharacter(String characterKey) {
    return byId('saathi_$characterKey')?.theme ?? ChatWallpaperTheme.factoryDefault;
  }
}

/// Doc 2 §2.7.2 doodle overlays — Milan-drawn line-art pattern set, low opacity.
@immutable
class DoodleOverlayDef {
  const DoodleOverlayDef(this.id, this.label, this.opacity);
  final String id;
  final String label;
  final double opacity;
}

const kDoodleOverlays = <DoodleOverlayDef>[
  DoodleOverlayDef('paisley', 'Paisley', 0.08),
  DoodleOverlayDef('marigold_petals', 'Marigold Petals', 0.08),
  DoodleOverlayDef('mountain_ridge', 'Mountain Ridge', 0.07),
  DoodleOverlayDef('mithila_lines', 'Mithila Lines', 0.06),
];

/// Rotating photo-set wallpaper (premium): picks a photo by UTC-day so the
/// chat's background changes daily, like Messenger's rotating chat themes.
String? photoSetWallpaperFor(ChatWallpaperTheme theme) {
  if (theme.wallpaperType != WallpaperType.photoSet) return null;
  final urls = theme.photoUrls;
  if (urls.isEmpty) return null;
  final dayIndex = DateTime.now().toUtc().difference(
          DateTime.utc(2026, 1, 1)).inDays;
  return urls[dayIndex % urls.length];
}

/// Resolves a [ChatWallpaperTheme]'s background paint for the current mode.
Decoration resolveWallpaperDecoration(ChatWallpaperTheme theme, Brightness brightness) {
  final dark = brightness == Brightness.dark;

  // Photo set (premium multi-photo rotating theme) — daily rotation.
  final photoSetUrl = photoSetWallpaperFor(theme);
  if (photoSetUrl != null) {
    return BoxDecoration(
      color: dark ? const Color(0xFF221C15) : const Color(0xFFF5F0E6),
      image: DecorationImage(
        image: NetworkImage(photoSetUrl),
        fit: BoxFit.cover,
        opacity: dark ? 0.30 : 0.55,
        colorFilter: ColorFilter.mode(
          dark ? const Color(0xAA14100C) : const Color(0x33FFFFFF),
          BlendMode.overlay,
        ),
      ),
    );
  }

  // Single custom photo wallpaper.
  if (theme.wallpaperType == WallpaperType.customUpload &&
      theme.wallpaperValue.startsWith('http')) {
    return BoxDecoration(
      color: dark ? const Color(0xFF221C15) : const Color(0xFFF5F0E6),
      image: DecorationImage(
        image: NetworkImage(theme.wallpaperValue),
        fit: BoxFit.cover,
        opacity: dark ? 0.30 : 0.55,
      ),
    );
  }
  if (theme.wallpaperType == WallpaperType.gradient &&
      theme.wallpaperValue.contains('|')) {
    final parts = theme.wallpaperValue.split('|');
    var begin = _tryHex(parts[0]) ?? const Color(0xFFF5A623);
    var end = _tryHex(parts[1]) ?? const Color(0xFFF3DCE2);
    if (dark) {
      begin = dim(begin, theme.darkModeBrightness ?? 0.25);
      end = dim(end, theme.darkModeBrightness ?? 0.25);
    }
    return BoxDecoration(
      gradient: LinearGradient(colors: [begin, end], begin: Alignment.topLeft, end: Alignment.bottomRight),
    );
  }
  var color = _tryHex(theme.wallpaperValue);
  if (color == null && theme.wallpaperType == WallpaperType.preset) {
    final preset = MilanChatPresets.byId(theme.wallpaperValue);
    color = switch (preset?.id) {
      'brand_marigold_warm' => const Color(0xFFFFF3DD),
      'festival_dashain' => const Color(0xFFFFE9C4),
      'festival_tihar' => const Color(0xFF31221B),
      'nature_himalaya' => const Color(0xFFDDEAF4),
      'nature_rhododendron' => const Color(0xFFFBEDEF),
      'saathi_asha' || 'saathi_bibek' || 'saathi_priya' || 'saathi_sagar' =>
        const Color(0xFFF6E7EC),
      _ => const Color(0xFFF5F0E6),
    };
  }
  if (color == null) {
    // custom_upload / ai_generated values are media URLs; placeholder tone while loading.
    color = const Color(0xFFF5F0E6);
  }
  if (dark) {
    color = dim(color, theme.darkModeBrightness ?? 0.35);
  }
  return BoxDecoration(color: color);
}

Color dim(Color c, double keepRatio) {
  final keep = keepRatio.clamp(0.0, 1.0);
  final factor = 0.15 + 0.85 * keep;
  return Color.fromARGB(
    (c.a * 255).round(),
    (c.r * 255 * factor).round(),
    (c.g * 255 * factor).round(),
    (c.b * 255 * factor).round(),
  );
}

Color? _tryHex(String value) {
  var hex = value.replaceFirst('#', '');
  if (hex.length == 6) hex = 'FF$hex';
  final parsed = int.tryParse(hex, radix: 16);
  return parsed == null ? null : Color(parsed);
}
