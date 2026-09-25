import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Theme-mode control (doc 8 §A3.2): the app hardcoded `ThemeMode.system`
/// while the Settings comment promised a manual override that did not exist.
/// Persisted and applied at the app root like [A11yState].
class ThemeModeState {
  const ThemeModeState({this.mode = ThemeMode.system});
  final ThemeMode mode;
}

class ThemeModeController extends StateNotifier<ThemeModeState> {
  ThemeModeController() : super(const ThemeModeState()) {
    _restore();
  }

  static const _key = 'app.themeMode';

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    final stored = prefs.getString(_key);
    state = ThemeModeState(mode: _decode(stored));
  }

  Future<void> setMode(ThemeMode mode) async {
    state = ThemeModeState(mode: mode);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, _encode(mode));
  }

  static ThemeMode _decode(String? value) => switch (value) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => ThemeMode.system,
      };

  static String _encode(ThemeMode mode) => switch (mode) {
        ThemeMode.light => 'light',
        ThemeMode.dark => 'dark',
        _ => 'system',
      };
}

final themeModeProvider =
    StateNotifierProvider<ThemeModeController, ThemeModeState>(
        (ref) => ThemeModeController());
