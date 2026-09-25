import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../app/theme/chat_theme_presets.dart';
import '../../app/theme/chat_theme_tokens.dart';
import '../../app/theme/color_tokens.dart';
import '../../app/theme/motion_tokens.dart';
import 'common.dart' show WallpaperPreviewCard;
import '../../app/theme/spacing_tokens.dart';
import '../../core/media/compression_service.dart';
import '../../features/profile/application/tier_provider.dart';
import '../../core/network/api_client.dart';
import '../../features/personalization/application/theme_provider.dart';

/// Doc 2 §2.6 (new) — tabbed bottom sheet (Presets / Solid & Gradient / Photo /
/// Bubble Color) with a live preview pane. Opens scoped per entry point.
class ThemePickerSheet extends ConsumerStatefulWidget {
  const ThemePickerSheet({super.key, required this.scope, this.showScopeToggle = false, this.embedded = false});

  final ChatThemeScopeKey scope;
  final bool showScopeToggle;
  final bool embedded;

  @override
  ConsumerState<ThemePickerSheet> createState() => _ThemePickerSheetState();
}

class _ThemePickerSheetState extends ConsumerState<ThemePickerSheet> {
  late ChatWallpaperTheme _candidate;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final current = ref.read(themeProvider(widget.scope)).valueOrNull?.theme
        ?? ChatWallpaperTheme.factoryDefault;
    _candidate = current;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.embedded) {
      return _body(context);
    }
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.78,
        child: _body(context),
      ),
    );
  }

  Widget _body(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final contrastOk = passesContrast(_candidate);
    return Column(
          children: [
            if (!widget.embedded)
              Container(
              width: 44,
              height: 4,
              margin: EdgeInsets.symmetric(vertical: Spacing.md),
              decoration: BoxDecoration(
                color: milan.line200,
                borderRadius: BorderRadius.circular(Spacing.pill),
              ),
            ),
            Padding(
              padding: EdgeInsets.symmetric(horizontal: Spacing.xl),
              child: Row(children: [
                Icon(widget.scope.kind == ChatThemeScopeKind.saathi
                    ? Icons.auto_awesome : Icons.chat_bubble_outline,
                    size: 18, color: milan.dhaka500),
                SizedBox(width: Spacing.sm),
                Text(
                  widget.scope.kind == ChatThemeScopeKind.global
                      ? 'Applying to: all chats'
                      : 'Applying to: ${widget.scope.kind == ChatThemeScopeKind.match ? 'this chat' : 'this Saathi character'}',
                  style: TextStyle(fontWeight: FontWeight.w600, color: milan.ink600),
                ),
              ]),
            ),
            SizedBox(height: Spacing.lg),
            WallpaperLivePreview(theme: _candidate),
            Expanded(
              child: DefaultTabController(
                length: 5,
                child: Column(children: [
                  TabBar(
                    isScrollable: true,
                    tabAlignment: TabAlignment.start,
                    labelColor: milan.marigold700,
                    unselectedLabelColor: milan.ink400,
                    tabs: const [
                      Tab(text: 'Presets'),
                      Tab(text: 'Solid & Gradient'),
                      Tab(text: 'Photo'),
                      Tab(text: 'Photo Set'),
                      Tab(text: 'Bubble Color'),
                    ],
                  ),
                  Expanded(
                    child: TabBarView(children: [
                      _presetsTab(context),
                      _solidGradientTab(context, milan),
                      _photoTab(context, milan),
                      _photoSetTab(context, milan),
                      _bubbleColorTab(context, milan),
                    ]),
                  ),
                ]),
              ),
            ),
            SafeArea(
              top: false,
              child: Padding(
                padding: EdgeInsets.fromLTRB(Spacing.xl, Spacing.sm, Spacing.xl, Spacing.lg),
                child: Row(children: [
                  TextButton(
                    onPressed: () async {
                      await ref.read(themeProvider(widget.scope).notifier).reset();
                      if (context.mounted) Navigator.of(context).pop();
                    },
                    child: Text('Reset to default',
                        style: TextStyle(color: milan.error500)),
                  ),
                  const Spacer(),
                  FilledButton.icon(
                    style: FilledButton.styleFrom(
                        minimumSize: Size(140, 44), backgroundColor: contrastOk
                            ? milan.marigold500
                            : milan.ink400),
                    icon: const Icon(Icons.check),
                    label: const Text('Apply'),
                    onPressed: contrastOk ? () async {
                      await ref.read(themeProvider(widget.scope).notifier).apply(_candidate);
                      if (context.mounted) Navigator.of(context).pop();
                    } : null,
                  ),
                 ]),
               ),
             ),
           ],
         );
   }

  Widget _presetsTab(BuildContext context) {
    final packs = <String, List<ChatThemePreset>>{
      'Brand': MilanChatPresets.brand,
      'Festival': MilanChatPresets.festival,
      'Nature': MilanChatPresets.nature,
      'Minimal': MilanChatPresets.minimal,
      'Saathi': MilanChatPresets.saathi,
    };
    return ListView(padding: EdgeInsets.all(Spacing.xl), children: [
      for (final entry in packs.entries) ...[
        Padding(
          padding: EdgeInsets.only(bottom: Spacing.md),
          child: Text(entry.key.toUpperCase(),
              style: TextStyle(fontSize: 11, letterSpacing: .04, fontWeight: FontWeight.w600)),
        ),
        SizedBox(
          height: 150,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: entry.value.length,
            separatorBuilder: (_, __) => SizedBox(width: Spacing.md),
            itemBuilder: (context, i) {
              final preset = entry.value[i];
              final theme = preset.theme;
              return WallpaperPreviewCard(
                theme: theme,
                selected: _candidate.presetId == preset.id ||
                    (_candidate.wallpaperValue == theme.wallpaperValue &&
                        _candidate.bubbleColorSent == theme.bubbleColorSent),
                onTap: () => setState(() => _candidate = theme.copyWith(presetId: preset.id)),
              );
            },
          ),
        ),
        SizedBox(height: Spacing.xl),
      ],
    ]);
  }

  Widget _solidGradientTab(BuildContext context, MilanColors milan) {
    final solids = ['#FFFBF5', '#F5F0E6', '#1F6F54', '#7B1E3A', '#161310', '#43535C'];
    final gradients = ['#F5A623|#C97D0C', '#7B1E3A|#591129', '#4C7A3F|#A8C686', '#43535C|#93A8B4'];
    return ListView(padding: EdgeInsets.all(Spacing.xl), children: [
      Text('SOLID', style: TextStyle(fontSize: 11, letterSpacing: .04, color: milan.ink400)),
      Wrap(
        spacing: Spacing.md,
        runSpacing: Spacing.md,
        children: [
          for (final hex in solids)
            GestureDetector(
              onTap: () => setState(() => _candidate = _candidate.copyWith(
                  wallpaperType: WallpaperType.solid, wallpaperValue: hex)),
              child: CircleAvatar(radius: 24, backgroundColor: _colorOf(hex)),
            ),
        ],
      ),
      SizedBox(height: Spacing.xl),
      Text('GRADIENT', style: TextStyle(fontSize: 11, letterSpacing: .04, color: milan.ink400)),
      Wrap(
        spacing: Spacing.md,
        runSpacing: Spacing.md,
        children: [
          for (final pair in gradients)
            GestureDetector(
              onTap: () => setState(() => _candidate = _candidate.copyWith(
                  wallpaperType: WallpaperType.gradient, wallpaperValue: pair)),
              child: Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(Spacing.radiusMd),
                  gradient: LinearGradient(colors: [
                    _colorOf(pair.split('|')[0]),
                    _colorOf(pair.split('|')[1]),
                  ]),
                ),
              ),
            ),
        ],
      ),
    ]);
  }

  Widget _photoTab(BuildContext context, MilanColors milan) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.photo_outlined, size: 44, color: milan.ink400),
          SizedBox(height: Spacing.lg),
          Text('Use a photo from your gallery or camera.',
              textAlign: TextAlign.center,
              style: TextStyle(color: milan.ink600)),
          SizedBox(height: Spacing.lg),
          OutlinedButton.icon(
            icon: const Icon(Icons.photo_library_outlined),
            label: const Text('Choose photo'),
            onPressed: () async {
              final picked =
                  await ImagePicker().pickImage(source: ImageSource.gallery);
              if (picked == null || !mounted) return;
              // Compression first (doc 2 §2.7.2), then the moderated upload
              // endpoint; only the returned CDN URL becomes the wallpaper value.
              final compressed = await ref
                  .read(compressionServiceProvider)
                  .compressImage(picked.path);
              try {
                final res = await ref.read(apiClientProvider).uploadMultipart(
                      '/personalization/theme/upload',
                      filePath: compressed.path,
                      field: 'image',
                    );
                if (!mounted) return;
                setState(() => _candidate = _candidate.copyWith(
                      wallpaperType: WallpaperType.customUpload,
                      wallpaperValue: (res['url'] as String?) ?? compressed.uri.toString(),
                    ));
              } on AppException {
                if (!mounted) return;
                // Offline: preview locally; upload retries on Apply.
                setState(() => _candidate = _candidate.copyWith(
                      wallpaperType: WallpaperType.customUpload,
                      wallpaperValue: compressed.uri.toString(),
                    ));
              }
            },
          ),
        ]),
      ),
    );
  }

  /// Premium multi-photo rotating wallpaper (§3.7): pick 2-6 photos; the chat
  /// background rotates daily. FREE users see the upsell, not a dead end.
  Widget _photoSetTab(BuildContext context, MilanColors milan) {
    final tier = ref.read(tierProvider);
    final photos = _candidate.photoUrls;
    return ListView(padding: EdgeInsets.all(Spacing.xl), children: [
      Row(children: [
        Icon(Icons.auto_awesome, size: 18, color: milan.dhaka500),
        SizedBox(width: Spacing.sm),
        Text('Photo Set — rotating wallpaper',
            style: const TextStyle(fontWeight: FontWeight.w700)),
        SizedBox(width: Spacing.sm),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: BoxDecoration(
              border: Border.all(color: milan.marigold500),
              borderRadius: BorderRadius.circular(Spacing.radiusSm)),
          child: Text('PREMIUM',
              style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  color: milan.marigold500)),
        ),
      ]),
      SizedBox(height: Spacing.sm),
      Text(
          'Pick 2-6 photos. Your chat background rotates through them — a new one every day, just like Messenger.',
          style: TextStyle(fontSize: 12.5, color: milan.ink600, height: 1.45)),
      SizedBox(height: Spacing.lg),
      if (!tier.isPlusOrHigher)
        Container(
          padding: EdgeInsets.all(Spacing.lg),
          decoration: BoxDecoration(
              color: milan.paper100,
              borderRadius: BorderRadius.circular(Spacing.radiusMd)),
          child: Column(children: [
            Icon(Icons.workspace_premium_outlined, size: 36, color: milan.marigold500),
            SizedBox(height: Spacing.md),
            const Text('Photo Sets are part of Plus & Premium',
                style: TextStyle(fontWeight: FontWeight.w700)),
            SizedBox(height: Spacing.sm),
            FilledButton(
                onPressed: () => context.push('/settings/subscription'),
                child: const Text('See passes')),
          ]),
        )
      else ...[
        Wrap(spacing: Spacing.md, runSpacing: Spacing.md, children: [
          for (var i = 0; i < photos.length; i++)
            Stack(children: [
              ClipRRect(
                  borderRadius: BorderRadius.circular(Spacing.radiusMd),
                  child: Image.network(photos[i],
                      width: 96, height: 96, fit: BoxFit.cover)),
              Positioned(
                top: 4,
                right: 4,
                child: GestureDetector(
                  onTap: () {
                    final next = [...photos]..removeAt(i);
                    setState(() => _candidate = _candidate.copyWith(
                        photoUrls: next,
                        wallpaperType: WallpaperType.photoSet));
                  },
                  child: Container(
                    decoration: const BoxDecoration(
                        color: Colors.black54, shape: BoxShape.circle),
                    child: const Icon(Icons.close, size: 16, color: Colors.white),
                  ),
                ),
              ),
            ]),
          if (photos.length < 6)
            GestureDetector(
              onTap: () async {
                final picked =
                    await ImagePicker().pickMultiImage(imageQuality: 85);
                if (picked.isEmpty || !mounted) return;
                setState(() => _busy = true);
                final urls = [...photos];
                for (final p in picked.take(6 - photos.length)) {
                  try {
                    final compressed = await ref
                        .read(compressionServiceProvider)
                        .compressImage(p.path);
                    final res = await ref.read(apiClientProvider).uploadMultipart(
                        '/personalization/theme/upload',
                        filePath: compressed.path,
                        field: 'image');
                    urls.add((res['url'] as String?) ?? '');
                  } on AppException {
                    // skip failed uploads; keep the rest
                  }
                }
                if (!mounted) return;
                setState(() {
                  _busy = false;
                  _candidate = _candidate.copyWith(
                      photoUrls: urls.where((u) => u.isNotEmpty).toList(),
                      wallpaperType: WallpaperType.photoSet);
                });
              },
              child: Container(
                width: 96,
                height: 96,
                decoration: BoxDecoration(
                    color: milan.paper100,
                    borderRadius: BorderRadius.circular(Spacing.radiusMd),
                    border: Border.all(color: milan.line200)),
                child: Icon(Icons.add_a_photo_outlined, color: milan.ink400),
              ),
            ),
        ]),
        SizedBox(height: Spacing.lg),
        if (_candidate.wallpaperType == WallpaperType.photoSet && photos.length >= 2)
          Text('Selected — tap Apply to set. Rotates daily.',
              style: TextStyle(fontSize: 12, color: milan.pine500)),
      ],
    ]);
  }

  Widget _bubbleColorTab(BuildContext context, MilanColors milan) {
    final swatches = [
      const Color(0xFFF5A623), const Color(0xFF7B1E3A), const Color(0xFF1F6F54),
      const Color(0xFF43535C), const Color(0xFFB33A4B), const Color(0xFF591129),
    ];
    final shapeOk = passesContrast(_candidate);
    return ListView(padding: EdgeInsets.all(Spacing.xl), children: [
      Text('SENT', style: TextStyle(fontSize: 11, letterSpacing: .04, color: milan.ink400)),
      Wrap(spacing: Spacing.md, children: [
        for (final c in swatches)
          GestureDetector(
            onTap: () => setState(() => _candidate =
                _candidate.copyWith(bubbleColorSent: c)),
            child: _swatch(c, _candidate.bubbleColorSent == c),
          ),
      ]),
      SizedBox(height: Spacing.xl),
      Text('RECEIVED', style: TextStyle(fontSize: 11, letterSpacing: .04, color: milan.ink400)),
      Wrap(spacing: Spacing.md, children: [
        for (final c in [const Color(0xFFF3DCE2), const Color(0xFFFDE9C8), const Color(0xFFDCEFE7)])
          GestureDetector(
            onTap: () => setState(() => _candidate =
                _candidate.copyWith(bubbleColorReceived: c)),
            child: _swatch(c, _candidate.bubbleColorReceived == c),
          ),
      ]),
      SizedBox(height: Spacing.xl),
      Row(children: [
        Text('Bubble shape', style: TextStyle(color: milan.ink600)),
        Spacer(),
        SegmentedButton<BubbleShape>(
          segments: const [
            ButtonSegment(value: BubbleShape.rounded, label: Text('Soft')),
            ButtonSegment(value: BubbleShape.compact, label: Text('Compact')),
          ],
          selected: {_candidate.bubbleShape},
          onSelectionChanged: (selection) =>
              setState(() => _candidate = _candidate.copyWith(bubbleShape: selection.first)),
        ),
      ]),
      if (!shapeOk) ...[
        SizedBox(height: Spacing.lg),
        Text('This color combination is hard to read.',
            style: TextStyle(color: milan.error500, fontSize: 12)),
      ],
    ]);
  }

  Widget _swatch(Color color, bool selected) {
    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(width: selected ? 3 : 1, color: selected ? Colors.black87 : Colors.black26),
      ),
    );
  }

  Color _colorOf(String hex) {
    var value = hex.replaceFirst('#', '');
    if (value.length == 6) value = 'FF$value';
    return Color(int.parse(value, radix: 16));
  }
}

/// Live preview pane shared by the sheet and the full-screen Studio (screen 67).
class WallpaperLivePreview extends StatelessWidget {
  const WallpaperLivePreview({super.key, required this.theme});
  final ChatWallpaperTheme theme;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final dark = Theme.of(context).brightness == Brightness.dark;
    return AnimatedContainer(
      duration: Motion.prefersReducedMotion(context)
          ? Duration.zero
          : Motion.chatThemeCrossfade,
      margin: EdgeInsets.symmetric(horizontal: Spacing.xl),
      height: 132,
      decoration:
          resolveWallpaperDecoration(theme, dark ? Brightness.dark : Brightness.light),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: _sampleBubble(
              fill: theme.bubbleColorReceived ?? milan.paper100,
              textColor: milan.ink900,
              alignRight: false,
            ),
          ),
          SizedBox(height: Spacing.md),
          Align(
            alignment: Alignment.centerRight,
            child: _sampleBubble(
              fill: theme.bubbleColorSent ?? milan.marigold500,
              textColor: milan.ink900,
              alignRight: true,
            ),
          ),
        ],
      ),
    );
  }

  Widget _sampleBubble(
      {required Color fill, required Color textColor, required bool alignRight}) {
    return Container(
      margin: EdgeInsets.symmetric(horizontal: Spacing.xl),
      padding: EdgeInsets.symmetric(vertical: Spacing.sm, horizontal: Spacing.lg),
      constraints: BoxConstraints(maxWidth: 220),
      decoration: BoxDecoration(
        color: fill,
        borderRadius: BorderRadius.circular(
          theme.bubbleShape == BubbleShape.compact ? Spacing.radiusMd : Spacing.radiusLg,
        ),
      ),
      child: Text(
        alignRight ? 'Haha that trek story!' : 'कस्तो रमाइलो! Tell me more?',
        style: TextStyle(color: textColor, fontSize: 13),
      ),
    );
  }
}


/// Full-page host for theme routes (/chat/:id/theme, /saathi/chat/:id/theme,
/// /settings/chat-theme). Wraps [ThemePickerSheet] content with a scope.
class ThemePickerHostPage extends StatelessWidget {
  const ThemePickerHostPage({super.key, required this.title, required this.scopeBuilder});
  final String title;
  final ChatThemeScopeKey Function() scopeBuilder;

  @override
  Widget build(BuildContext context) {
    late final scope = scopeBuilder();
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: ThemePickerSheet(scope: scope, embedded: true),
    );
  }
}
