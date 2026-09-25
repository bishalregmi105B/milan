import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:milan/app/theme/chat_theme_tokens.dart';
import 'package:milan/app/theme/color_tokens.dart';
import 'package:milan/shared/widgets/chat_bubble.dart';
import 'package:milan/shared/widgets/common.dart' show WallpaperPreviewCard;

void main() {
  group('ChatWallpaperTheme', () {
    test('factory default matches doc 2 §2.1 brand tokens', () {
      const theme = ChatWallpaperTheme.factoryDefault;
      expect(theme.bubbleColorSent, const Color(0xFFF5A623));
      expect(theme.bubbleColorReceived, const Color(0xFFF3DCE2));
      expect(theme.bubbleShape, BubbleShape.rounded);
    });

    test('scope keys never collide across kinds', () {
      expect(const ChatThemeScopeKey.global().storageKey, 'global');
      expect(const ChatThemeScopeKey.match('m1').storageKey, 'match:m1');
      expect(
        const ChatThemeScopeKey.saathi('asha').storageKey,
        'saathi:asha',
      );
    });

    test('contrast check rejects unreadable bubble/text pairs', () {
      const readable = ChatWallpaperTheme(
        wallpaperType: WallpaperType.solid,
        wallpaperValue: '#FFFBF5',
        bubbleColorSent: Color(0xFFF5A623),
        bubbleColorReceived: Color(0xFFF3DCE2),
      );
      // A dark bubble under ink900 message text fails the AA-equivalent check
      const unreadable = ChatWallpaperTheme(
        wallpaperType: WallpaperType.solid,
        wallpaperValue: '#FFFBF5',
        bubbleColorSent: Color(0xFF33291D),
        bubbleColorReceived: Color(0xFF33291D),
      );
      expect(passesContrast(readable), isTrue);
      expect(passesContrast(unreadable), isFalse);
    });

    test('backend JSON round-trip preserves every layer', () {
      const theme = ChatWallpaperTheme(
        wallpaperType: WallpaperType.gradient,
        wallpaperValue: '#F5A623|#7B1E3A',
        bubbleColorSent: Color(0xFF7B1E3A),
        bubbleColorReceived: Color(0xFFFDE9C8),
        bubbleShape: BubbleShape.compact,
        doodleOverlayId: 'paisley',
        textScale: 1.15,
        darkModeBrightness: 0.4,
      );
      final json = theme.toBackendJson(scope: 'match', scopeId: 'abc');
      final restored = ChatWallpaperTheme.fromBackendJson(json);
      expect(restored.wallpaperType, theme.wallpaperType);
      expect(restored.wallpaperValue, theme.wallpaperValue);
      expect(restored.bubbleColorSent, theme.bubbleColorSent);
      expect(restored.bubbleShape, BubbleShape.compact);
      expect(restored.doodleOverlayId, 'paisley');
      expect(restored.textScale, 1.15);
      expect(restored.darkModeBrightness, 0.4);
    });
  });

  group('ChatBubble widget', () {
    Future<void> pumpBubble(
      WidgetTester tester, {
      required bool isSent,
      bool isAi = false,
      Brightness brightness = Brightness.light,
      BubbleShape shape = BubbleShape.rounded,
    }) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            theme:
                brightness == Brightness.light ? milanLightTheme() : milanDarkTheme(),
            home: Scaffold(
              body: Center(
                child: ChatBubble(
                  text: 'नमस्ते! How are you?',
                  isSent: isSent,
                  isAi: isAi,
                  bubbleShape: shape,
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('renders sent bubble without AI tag', (tester) async {
      await pumpBubble(tester, isSent: true);
      expect(find.text('नमस्ते! How are you?'), findsOneWidget);
      expect(find.text('SUGGESTED'), findsNothing);
    });

    testWidgets('AI variant drops per-message tag — disclosure lives in the header (§2)', (tester) async {
      await pumpBubble(tester, isSent: false, isAi: true);
      expect(find.text('SUGGESTED'), findsNothing);
      expect(find.text('AI'), findsNothing); // header badge only, never per bubble
    });

    testWidgets('renders in dark theme without exception', (tester) async {
      await pumpBubble(tester, isSent: true, brightness: Brightness.dark);
      expect(find.byType(ChatBubble), findsOneWidget);
    });
  });

  group('WallpaperPreviewCard', () {
    testWidgets('shows sample bubble pair over candidate wallpaper', (tester) async {
      const theme = ChatWallpaperTheme.factoryDefault;
      await tester.pumpWidget(
        MaterialApp(
          theme: milanLightTheme(),
          home: Scaffold(
            body: Center(child: WallpaperPreviewCard(theme: theme, selected: true)),
          ),
        ),
      );
      expect(find.byType(WallpaperPreviewCard), findsOneWidget);
    });
  });
}
