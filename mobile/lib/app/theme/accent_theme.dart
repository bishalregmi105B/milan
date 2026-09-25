import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../shared/widgets/chat_bubble.dart';

/// User-selectable app accent (Messenger-style personalization): the accent
/// drives sent-bubble color, send button and key highlights across the app.
/// Default is Messenger blue over a white surface; the user can change it
/// anytime from Settings → Appearance. Persisted locally.
class AccentThemeState {
  const AccentThemeState({this.accent = ChatBubble.defaultAccent});
  final Color accent;

  AccentThemeState copyWith(Color color) => AccentThemeState(accent: color);

  /// doc 8 §B: the accent drives *action* colour. Sent-bubble text switches
  /// to ink when a light custom accent would make white unreadable.
  static Color readableOn(Color background) {
    final luminance = background.computeLuminance();
    return luminance > 0.55 ? const Color(0xFF1F1B16) : Colors.white;
  }
}

class AccentThemeController extends StateNotifier<AccentThemeState> {
  AccentThemeController() : super(const AccentThemeState()) {
    _restore();
  }

  static const _key = 'app.accent.color';

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    final value = prefs.getInt(_key);
    if (value != null) {
      state = AccentThemeState(accent: Color(value));
    }
  }

  Future<void> setAccent(Color color) async {
    state = state.copyWith(color);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_key, color.toARGB32());
  }
}

final accentThemeProvider =
    StateNotifierProvider<AccentThemeController, AccentThemeState>(
        (ref) => AccentThemeController());

/// The palette offered in Settings → Appearance.
const kAccentChoices = <String, Color>{
  'Milan Sky': Color(0xFF38BDF8),
  'Deep Sky': Color(0xFF0369A1),
  'Milan Marigold': Color(0xFFF5A623),
  'Dhaka Rose': Color(0xFFC2426E),
  'Pine Green': Color(0xFF1F8F62),
  'Royal Violet': Color(0xFF6B4EE6),
};
