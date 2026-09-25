import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'dart:async';

import '../core/network/websocket_client.dart';
import '../core/notifications/push_service.dart';
import '../core/realtime/realtime_bridge.dart';
import 'settings/a11y_settings.dart';
import 'settings/theme_mode_settings.dart';
import 'theme/color_tokens.dart';
import 'theme/accent_theme.dart';
import '../core/localization/app_localizations.dart';
import '../features/auth/application/auth_provider.dart';
import '../features/chat/application/chat_providers.dart';
import 'router.dart';

class MilanApp extends ConsumerStatefulWidget {
  const MilanApp({super.key});

  @override
  ConsumerState<MilanApp> createState() => _MilanAppState();
}

class _MilanAppState extends ConsumerState<MilanApp> {
  Timer? _presenceTimer;

  // P0-2: bring the realtime layer back after the app is resumed if it was
  // dropped while backgrounded (no-op when signed out or already online).
  late final AppLifecycleListener _lifecycle = AppLifecycleListener(
    onResume: () {
      ref.read(websocketClientProvider).ensureConnected();
      _startPresenceHeartbeat();
    },
    onPause: () => _presenceTimer?.cancel(),
    onDetach: () => _presenceTimer?.cancel(),
  );

  @override
  void initState() {
    super.initState();
    // The one socket subscriber for chat traffic, alive for the whole session.
    ref.read(realtimeBridgeProvider).start();
    // Notification taps → the screen the notification is about. This used to be
    // an empty listener, so every tap just reopened whatever screen was last on
    // top. Buffered cold-start taps replay as soon as the handler is installed.
    PushService.clickHandler = _handleNotificationTap;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _startPresenceHeartbeat();
    });
  }

  /// Routes a push payload to its screen. The backend sends
  /// `{"type": ..., "match_id": ...}` in `data` (chat/companion/match/expiry).
  ///
  /// A tap that cold-starts the app lands here while the splash screen is still
  /// restoring the session, and splash's own `context.go` would immediately
  /// throw the deep link away. So during boot the destination is parked in
  /// [pendingDeepLinkProvider] and splash navigates there once it knows the
  /// user is signed in.
  void _handleNotificationTap(Map<String, dynamic> data) {
    final location = _locationFor(data);
    if (location == null) return;
    final router = ref.read(routerProvider);
    final booting = ref.read(authProvider).isLoading ||
        router.state.matchedLocation == '/splash';
    if (booting) {
      ref.read(pendingDeepLinkProvider.notifier).state = location;
      return;
    }
    WidgetsBinding.instance.addPostFrameCallback((_) => router.go(location));
  }

  String? _locationFor(Map<String, dynamic> data) {
    final type = '${data['type'] ?? ''}';
    final matchId = data['match_id']?.toString();
    final hasMatch = matchId != null && matchId.isNotEmpty;
    switch (type) {
      case 'message':
      case 'companion_message':
      case 'companion_deferred':
      case 'match_expiry_warning':
      case 'match_expired':
        return hasMatch ? '/chat/$matchId' : '/chat';
      case 'match':
        return hasMatch
            ? '/discover/match/$matchId?celebration=true'
            : '/discover';
      case 'like_received':
      case 'superlike':
        return '/discover/who-liked-you';
      case 'snap_screenshot':
        return '/jhalak';
      case 'payment_approved':
      case 'payment_rejected':
        return '/settings/subscription';
      default:
        // Unknown category: the notification centre lists everything.
        return '/notifications';
    }
  }

  /// §presence: beat every 60s while the app is visible — socket for speed,
  /// REST as the fallback that works even while the socket reconnects. The
  /// server stamps last_active_at, which is what "Active now" reads.
  void _startPresenceHeartbeat() {
    _presenceTimer?.cancel();
    void beat() {
      final myId = ref.read(currentUserIdProvider);
      if (myId == null) return;
      ref.read(presenceProvider.notifier).heartbeat(myId);
    }

    beat();
    _presenceTimer = Timer.periodic(const Duration(seconds: 60), (_) => beat());
  }

  @override
  void dispose() {
    _presenceTimer?.cancel();
    PushService.clickHandler = null;
    _lifecycle.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final router = ref.watch(routerProvider);
    final a11y = ref.watch(a11yProvider);
    final themeMode = ref.watch(themeModeProvider);
    // the user's accent IS the app theme colour (Settings → Appearance) —
    // buttons, switches, chips and the nav bar all follow it
    final accent = ref.watch(accentThemeProvider).accent;
    return MaterialApp.router(
      title: 'Milan',
      debugShowCheckedModeBanner: false,
      theme: milanLightTheme(accent),
      darkTheme: milanDarkTheme(accent),
      // doc 8 §A3.2: real theme-mode control (system/light/dark), persisted.
      themeMode: themeMode.mode,
      locale: a11y.locale,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      builder: (context, child) => MediaQuery(
        data: MediaQuery.of(context).copyWith(
          textScaler: TextScaler.linear(a11y.textScale),
          disableAnimations: a11y.reduceMotion,
        ),
        child: child ?? const SizedBox.shrink(),
      ),
      routerConfig: router,
    );
  }
}

extension GoRouterX on BuildContext {
  void pushNamed(String location) => go(location);
}

/// A notification tap that arrived while the app was still booting. Splash
/// consumes it after session restore, so tapping a message notification on a
/// cold start lands in that chat instead of on the discovery deck.
final pendingDeepLinkProvider = StateProvider<String?>((ref) => null);
