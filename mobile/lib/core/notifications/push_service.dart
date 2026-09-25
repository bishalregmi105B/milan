import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:onesignal_flutter/onesignal_flutter.dart';

import '../network/api_client.dart';

/// OneSignal push (§push v2 — this REPLACES the FCM path).
///
/// Why notifications never arrived before: the app registered *FCM* tokens
/// while the backend delivers through OneSignal — two different id spaces, so
/// no device was ever addressable. Now: OneSignal initializes at boot, the
/// subscription id is registered to /notifications/devices after sign-in, and
/// the backend's OneSignal v5 REST push reaches the device.
///
/// Taps are routed, not swallowed. The click that COLD-STARTS the app fires
/// before any widget exists, so clicks are buffered in [_pendingClicks] and
/// replayed the moment [clickHandler] is installed by the app root — a
/// broadcast stream with no subscriber silently dropped them, which is why a
/// notification tap only ever opened the app on its last screen.
class PushService {
  PushService(this._ref);

  final Ref _ref;
  final Set<String> _mutedCategories = {};
  bool _deviceRegistered = false;

  void muteCategory(String category) => _mutedCategories.add(category);
  void unmuteCategory(String category) => _mutedCategories.remove(category);

  static const _appId = String.fromEnvironment(
    'ONESIGNAL_APP_ID',
    defaultValue: '821deff4-bbd5-43d3-8572-42d17364dea3',
  );
  bool get _configured => _appId.isNotEmpty;

  /// Set to true once `OneSignal.initialize` has run. Gates every SDK call:
  /// OneSignal throws when touched before init (widget tests, push-less dev
  /// runs) and a sign-in must never crash because of the push layer.
  static bool initialized = false;

  static final List<Map<String, dynamic>> _pendingClicks = [];
  static void Function(Map<String, dynamic> data)? _clickHandler;

  /// Installed by the app root; buffered cold-start taps replay immediately.
  static set clickHandler(void Function(Map<String, dynamic> data)? handler) {
    _clickHandler = handler;
    if (handler == null) return;
    final pending = List<Map<String, dynamic>>.from(_pendingClicks);
    _pendingClicks.clear();
    for (final data in pending) {
      handler(data);
    }
  }

  /// Foreground pushes (banner feed / notification centre).
  static final StreamController<Map<String, dynamic>> _foreground =
      StreamController<Map<String, dynamic>>.broadcast();
  static Stream<Map<String, dynamic>> get foregroundNotifications =>
      _foreground.stream;

  static void _dispatchClick(Map<String, dynamic> data) {
    final handler = _clickHandler;
    if (handler == null) {
      _pendingClicks.add(data);
      return;
    }
    handler(data);
  }

  /// Boot-time init (main.dart) — static because no ProviderContainer exists
  /// yet; taps route through [clickHandler].
  static void initOnce() {
    final appId = _appId;
    if (appId.isEmpty || Platform.isLinux || Platform.isMacOS) {
      debugPrint('PushService: ONESIGNAL_APP_ID not set — push disabled');
      return;
    }
    try {
      OneSignal.initialize(appId);
      initialized = true;
      OneSignal.Notifications.requestPermission(true);
      OneSignal.Notifications.addClickListener((event) {
        final data = event.notification.additionalData ?? const {};
        _dispatchClick({
          'title': event.notification.title,
          'body': event.notification.body,
          ...data,
        });
      });
      OneSignal.Notifications.addForegroundWillDisplayListener((event) {
        final data = event.notification.additionalData ?? const {};
        _foreground.add({
          'title': event.notification.title,
          'body': event.notification.body,
          ...data,
        });
      });
    } catch (e) {
      debugPrint('PushService init failed: $e');
    }
  }

  /// After sign-in / session restore: bind the device to this user.
  /// OneSignal external id makes the user addressable across devices.
  Future<void> onSignedIn(String userId) async {
    if (!_configured || !initialized) return;
    try {
      OneSignal.login(userId);
    } catch (_) {}
    if (_deviceRegistered) return;
    // The subscription id is not always ready the instant we sign in (the
    // device is still registering with OneSignal), so poll briefly and keep
    // the observer as the long-term fix. Without this the very first launch
    // after install registered nothing and that device got no pushes at all.
    for (var attempt = 0; attempt < 10 && !_deviceRegistered; attempt++) {
      final id = OneSignal.User.pushSubscription.id;
      if (id != null && id.isNotEmpty) {
        await _registerDevice(id);
        break;
      }
      await Future<void>.delayed(const Duration(seconds: 2));
    }
    OneSignal.User.pushSubscription.addObserver((change) {
      final newId = change.current.id;
      if (newId != null && newId.isNotEmpty) _registerDevice(newId);
    });
  }

  Future<void> _registerDevice(String subscriptionId) async {
    try {
      await _ref.read(apiClientProvider).post('/notifications/devices', body: {
        'token': subscriptionId,
        'platform': Platform.isIOS ? 'ios' : 'android',
      });
      _deviceRegistered = true;
    } on AppException {
      // retried by the subscription observer / next sign-in
    }
  }
}

final pushServiceProvider = Provider<PushService>((ref) => PushService(ref));
