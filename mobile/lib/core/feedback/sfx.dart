import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// App-wide sound + haptic language (Messenger-parity feedback): system
/// sounds (zero licensed assets) + HapticFeedback patterns, user-toggleable.
enum Sfx {
  swipeLight, // pass
  swipeLike, // like commit
  superlike, // diamond
  match, // mutual match celebration
  messageSent,
  messageReceived,
  keyboardish, // generic tap
}

class SfxState {
  const SfxState({this.soundOn = true, this.hapticsOn = true});
  final bool soundOn;
  final bool hapticsOn;
}

class SfxController extends StateNotifier<SfxState> {
  SfxController() : super(const SfxState()) {
    _restore();
  }

  static const _soundKey = 'app.sound.enabled';
  static const _hapticsKey = 'app.haptics.enabled';

  Future<void> _restore() async {
    final prefs = await SharedPreferences.getInstance();
    state = SfxState(
      soundOn: prefs.getBool(_soundKey) ?? true,
      hapticsOn: prefs.getBool(_hapticsKey) ?? true,
    );
  }

  Future<void> setSound(bool on) async {
    state = SfxState(soundOn: on, hapticsOn: state.hapticsOn);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_soundKey, on);
  }

  Future<void> setHaptics(bool on) async {
    state = SfxState(soundOn: state.soundOn, hapticsOn: on);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_hapticsKey, on);
  }

  void play(Sfx sfx) {
    if (!state.soundOn && !state.hapticsOn) return;
    switch (sfx) {
      case Sfx.swipeLight:
        if (state.hapticsOn) HapticFeedback.lightImpact();
        if (state.soundOn) SystemSound.play(SystemSoundType.click);
      case Sfx.swipeLike:
        if (state.hapticsOn) HapticFeedback.mediumImpact();
        if (state.soundOn) SystemSound.play(SystemSoundType.alert);
      case Sfx.superlike:
        if (state.hapticsOn) HapticFeedback.heavyImpact();
        if (state.soundOn) SystemSound.play(SystemSoundType.alert);
      case Sfx.match:
        if (state.hapticsOn) HapticFeedback.heavyImpact();
        if (state.soundOn) SystemSound.play(SystemSoundType.alert);
      case Sfx.messageSent:
        if (state.hapticsOn) HapticFeedback.lightImpact();
        if (state.soundOn) SystemSound.play(SystemSoundType.click);
      case Sfx.messageReceived:
        if (state.hapticsOn) HapticFeedback.lightImpact();
        // Messenger-parity incoming pop — user-toggleable via Settings.
        if (state.soundOn) SystemSound.play(SystemSoundType.alert);
      case Sfx.keyboardish:
        if (state.hapticsOn) HapticFeedback.selectionClick();
    }
  }
}

final sfxProvider = StateNotifierProvider<SfxController, SfxState>(
    (ref) => SfxController());
