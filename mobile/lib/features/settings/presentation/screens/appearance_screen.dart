import 'package:flutter/material.dart';
import 'package:flutter_colorpicker/flutter_colorpicker.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/settings/theme_mode_settings.dart';
import '../../../../app/theme/accent_theme.dart';
import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../shared/widgets/chat_bubble.dart';

/// Settings → Appearance (doc 8 §B): theme mode (system/light/dark) + accent
/// picker — five curated choices plus any custom colour, contrast-gated so a
/// light accent flips sent text to ink instead of becoming unreadable.
class AppearanceScreen extends ConsumerWidget {
  const AppearanceScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = context.milan;
    final accent = ref.watch(accentThemeProvider).accent;
    final themeMode = ref.watch(themeModeProvider).mode;

    return Scaffold(
      appBar: AppBar(title: const Text('Appearance')),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        Text('Theme', style: context.h4),
        SizedBox(height: Spacing.sm),
        SegmentedButton<ThemeMode>(
          segments: const [
            ButtonSegment(value: ThemeMode.system, label: Text('System'), icon: Icon(Icons.settings_suggest_outlined)),
            ButtonSegment(value: ThemeMode.light, label: Text('Light'), icon: Icon(Icons.light_mode_outlined)),
            ButtonSegment(value: ThemeMode.dark, label: Text('Dark'), icon: Icon(Icons.dark_mode_outlined)),
          ],
          selected: {themeMode},
          onSelectionChanged: (selection) => ref
              .read(themeModeProvider.notifier)
              .setMode(selection.first),
        ),
        SizedBox(height: Spacing.xl),
        Text('Chat accent', style: context.h4),
        SizedBox(height: Spacing.sm),
        Text('Used for your sent bubbles, the send button and highlights across chats.',
            style: TextStyle(fontSize: 13, color: milan.ink600)),
        SizedBox(height: Spacing.lg),
        // live preview
        Container(
          padding: EdgeInsets.all(Spacing.lg),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(Spacing.radiusLg),
              border: Border.all(color: milan.line200)),
          child: Column(children: [
            Align(
              alignment: Alignment.centerRight,
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 13),
                decoration: BoxDecoration(
                    color: accent,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(Spacing.radiusLg),
                      topRight: Radius.circular(Spacing.radiusLg),
                      bottomLeft: Radius.circular(Spacing.radiusLg),
                      bottomRight: Radius.circular(4),
                    )),
                child: Text('this is how your messages look',
                    style: TextStyle(
                        color: AccentThemeState.readableOn(accent), fontSize: 13)),
              ),
            ),
            const SizedBox(height: 6),
            Align(
              alignment: Alignment.centerLeft,
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 13),
                decoration: BoxDecoration(
                    color: ChatBubble.receivedFill,
                    borderRadius: const BorderRadius.only(
                      topLeft: Radius.circular(Spacing.radiusLg),
                      topRight: Radius.circular(Spacing.radiusLg),
                      bottomLeft: Radius.circular(4),
                      bottomRight: Radius.circular(Spacing.radiusLg),
                    )),
                child: Text('and how replies look',
                    style: TextStyle(color: milan.ink900, fontSize: 13)),
              ),
            ),
          ]),
        ),
        SizedBox(height: Spacing.lg),
        for (final entry in kAccentChoices.entries)
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: CircleAvatar(backgroundColor: entry.value, radius: 14),
            title: Text(entry.key),
            trailing: accent == entry.value
                ? Icon(Icons.check_circle, color: entry.value)
                : null,
            onTap: () =>
                ref.read(accentThemeProvider.notifier).setAccent(entry.value),
          ),
        // Custom colour — any colour at all (doc 8 §B), gated by the same
        // contrast rule the bubbles apply.
        ListTile(
          contentPadding: EdgeInsets.zero,
          leading: CircleAvatar(
            radius: 14,
            backgroundColor: accent,
            child: Icon(Icons.colorize, size: 15, color: AccentThemeState.readableOn(accent)),
          ),
          title: const Text('Custom colour'),
          subtitle: Text(
              AccentThemeState.readableOn(accent) == Colors.white
                  ? 'Good contrast with white text'
                  : 'Text on this colour switches to ink',
              style: const TextStyle(fontSize: 12)),
          trailing: const Icon(Icons.chevron_right),
          onTap: () => _pickCustomColor(context, ref, accent),
        ),
        SizedBox(height: Spacing.xl),
        Text('Chat background stays clean white — wallpapers and photo sets are per-chat from the chat’s own theme menu.',
            style: TextStyle(fontSize: 12, color: milan.ink400)),
      ]),
    );
  }

  Future<void> _pickCustomColor(BuildContext context, WidgetRef ref, Color current) async {
    Color picked = current;
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Pick an accent'),
        content: SingleChildScrollView(
          child: ColorPicker(
            pickerColor: current,
            onColorChanged: (color) => picked = color,
            enableAlpha: false,
            displayThumbColor: true,
            pickerAreaHeightPercent: 0.8,
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () {
                ref.read(accentThemeProvider.notifier).setAccent(picked);
                Navigator.of(dialogContext).pop();
              },
              child: const Text('Apply')),
        ],
      ),
    );
  }
}
