import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../shared/widgets/theme_picker_sheet.dart';
import '../../../personalization/application/theme_provider.dart';
import '../../../../app/theme/chat_theme_tokens.dart';

/// Screen 67 (new in this revision) — full-screen Chat Theme & Wallpaper
/// Studio scoped to "all chats" by default (doc 2 §2.7.4).
class ChatThemeStudioScreen extends ConsumerWidget {
  const ChatThemeStudioScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final themeAsync = ref.watch(themeProvider(const ChatThemeScopeKey.global()));

    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Chat Theme & Wallpaper Studio'),
          bottom: TabBar(
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            labelColor: milan.marigold700,
            unselectedLabelColor: milan.ink400,
            tabs: const [
              Tab(text: 'Presets'),
              Tab(text: 'Solid & Gradient'),
              Tab(text: 'Photo'),
              Tab(text: 'Bubble Color'),
            ],
          ),
        ),
        body: Column(children: [
          SizedBox(height: Spacing.lg),
          Padding(
            padding: EdgeInsets.symmetric(horizontal: Spacing.xl),
            child: Row(
              children: [
                Icon(Icons.info_outline, size: 16, color: milan.ink400),
                SizedBox(width: Spacing.sm),
                Text('Applying to: all chats',
                    style: TextStyle(fontSize: 12, color: milan.ink600)),
                TextButton(onPressed: () {}, child: Text('Change scope')),
              ],
            ),
          ),
          Expanded(
            child: themeAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Something went wrong. Please try again.')),
              data: (state) => TabBarView(children: [
                ListView(
                  padding: EdgeInsets.all(Spacing.xl),
                  children: [
                    WallpaperLivePreview(theme: state.theme),
                    SizedBox(height: Spacing.xl),
                    Text('Presets ship in verified light and dark variants.',
                        style: TextStyle(color: milan.ink600)),
                  ],
                ),
                ListView(
                  padding: EdgeInsets.all(Spacing.xl),
                  children: [
                    WallpaperLivePreview(theme: state.theme),
                    Slider(value: .5, onChanged: (_) {},
                        label: 'Dark-mode brightness',
                        activeColor: milan.marigold500),
                    Text('Dark mode brightness', style: TextStyle(fontSize: 12, color: milan.ink600)),
                  ],
                ),
                ListView(
                  padding: EdgeInsets.all(Spacing.xl),
                  children: [
                    WallpaperLivePreview(theme: state.theme),
                    SizedBox(height: Spacing.xl),
                    OutlinedButton.icon(
                      icon: Icon(Icons.add_photo_alternate_outlined),
                      label: Text('Choose photo'),
                      onPressed: () {},
                    ),
                    SizedBox(height: Spacing.md),
                    Text('Uploads pass through compression and moderation before they can be applied.',
                        style: TextStyle(fontSize: 12, color: milan.ink600)),
                  ],
                ),
                ListView(
                  padding: EdgeInsets.all(Spacing.xl),
                  children: [
                    WallpaperLivePreview(theme: state.theme),
                    SizedBox(height: Spacing.xl),
                    Row(children: [
                      Text('Bubble shape'),
                      Spacer(),
                      SegmentedButton<BubbleShape>(
                        segments: [
                          ButtonSegment(value: BubbleShape.rounded, label: Text('Soft')),
                          ButtonSegment(value: BubbleShape.compact, label: Text('Compact')),
                        ],
                        selected: {state.theme.bubbleShape},
                        onSelectionChanged: (_) {},
                      ),
                    ]),
                    SizedBox(height: Spacing.lg),
                    Row(children: [
                      Text('Chat text size'),
                      Spacer(),
                      IconButton(onPressed: () {}, icon: Icon(Icons.remove_circle_outline)),
                      Text('100%'),
                      IconButton(onPressed: () {}, icon: Icon(Icons.add_circle_outline)),
                    ]),
                  ],
                ),
              ]),
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: EdgeInsets.all(Spacing.xl),
              child: Row(children: [
                TextButton.icon(
                  icon: Icon(Icons.restart_alt, color: milan.error500),
                  label: Text('Reset to default', style: TextStyle(color: milan.error500)),
                  onPressed: () async {
                    await ref.read(themeProvider(const ChatThemeScopeKey.global()).notifier).reset();
                  },
                ),
              ]),
            ),
          ),
        ]),
      ),
    );
  }
}
