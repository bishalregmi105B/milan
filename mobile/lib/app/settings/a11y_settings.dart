import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Language & accessibility settings — REAL, persisted, and applied at the
/// app root (MaterialApp locale + textScaler). 'system' follows the OS.
class A11yState {
  const A11yState({
    this.languageCode = 'system',
    this.textScale = 1.0,
    this.reduceMotion = false,
  });
  final String languageCode; // system | en | ne
  final double textScale;
  final bool reduceMotion;

  Locale? get locale =>
      languageCode == 'system' ? null : Locale(languageCode);
}

class A11yController extends StateNotifier<A11yState> {
  A11yController() : super(const A11yState()) {
    _restore();
  }

  static const _langKey = 'app.language';
  static const _scaleKey = 'app.textScale';
  static const _motionKey = 'app.reduceMotion';

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    state = A11yState(
      languageCode: prefs.getString(_langKey) ?? 'system',
      textScale: prefs.getDouble(_scaleKey) ?? 1.0,
      reduceMotion: prefs.getBool(_motionKey) ?? false,
    );
  }

  Future<void> setLanguage(String code) async {
    state = A11yState(
        languageCode: code,
        textScale: state.textScale,
        reduceMotion: state.reduceMotion);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_langKey, code);
  }

  Future<void> setTextScale(double scale) async {
    state = A11yState(
        languageCode: state.languageCode,
        textScale: scale,
        reduceMotion: state.reduceMotion);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_scaleKey, scale);
  }

  Future<void> setReduceMotion(bool on) async {
    state = A11yState(
        languageCode: state.languageCode,
        textScale: state.textScale,
        reduceMotion: on);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_motionKey, on);
  }
}

final a11yProvider =
    StateNotifierProvider<A11yController, A11yState>((ref) => A11yController());
