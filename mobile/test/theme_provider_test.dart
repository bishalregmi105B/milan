import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:milan/app/theme/chat_theme_presets.dart';
import 'package:milan/app/theme/chat_theme_tokens.dart';
import 'package:milan/core/network/api_client.dart';
import 'package:milan/core/storage/local_db.dart';
import 'package:milan/core/storage/secure_storage.dart';
import 'package:milan/features/personalization/application/theme_provider.dart';
import 'package:milan/features/saathi/application/saathi_session_provider.dart';

class FakeLocalDb extends LocalDb {
  FakeLocalDb({Map<String, Map<String, dynamic>>? initial}) : _store = initial ?? {};

  final Map<String, Map<String, dynamic>> _store;
  int saves = 0;

  @override
  Future<Map<String, dynamic>?> loadResolvedTheme(String scopeKey) async =>
      _store[scopeKey];

  @override
  Future<void> saveResolvedTheme(String scopeKey, Map<String, dynamic> json,
      {bool synced = false}) async {
    saves++;
    _store[scopeKey] = json;
  }

  @override
  Future<void> markThemesSynced() async {}
}

class FailingApiClient extends ApiClient {
  FailingApiClient() : super(storage: SecureStorage());

  Never _fail(String path) => throw AppException('network_error', statusCode: 503);

  @override
  Future<T> get<T>(String path, {Map<String, dynamic>? query}) async =>
      _fail(path);

  @override
  Future<T> post<T>(String path, {Object? body}) async => _fail(path);

  @override
  Future<T> put<T>(String path, {Object? body}) async => _fail(path);

  @override
  Future<T> delete<T>(String path) async => _fail(path);
}

void main() {
  group('themeProvider scope resolution (doc 3 §4)', () {
    test('falls back to factory default when no cache and backend unreachable',
        () async {
      final container = ProviderContainer(overrides: [
        localDbProvider.overrideWithValue(FakeLocalDb()),
        apiClientProvider.overrideWithValue(FailingApiClient()),
      ]);
      addTearDown(container.dispose);

      final state = await container.read(
        themeProvider(const ChatThemeScopeKey.global()).future,
      );
      expect(state.theme.wallpaperValue,
          ChatWallpaperTheme.factoryDefault.wallpaperValue);
      expect(state.theme.bubbleShape, BubbleShape.rounded);
    });

    test('uses locally-cached resolved value instantly (offline-first)',
        () async {
      const cached = ChatWallpaperTheme(
        wallpaperType: WallpaperType.gradient,
        wallpaperValue: '#7B1E3A|#591129',
        bubbleColorSent: Color(0xFFC97D0C),
        bubbleColorReceived: Color(0xFFF3DCE2),
      );
      final db = FakeLocalDb(initial: {
        'global': cached.toBackendJson(scope: 'global'),
      });
      final container = ProviderContainer(overrides: [
        localDbProvider.overrideWithValue(db),
        apiClientProvider.overrideWithValue(FailingApiClient()),
      ]);
      addTearDown(container.dispose);

      final state = await container.read(
        themeProvider(const ChatThemeScopeKey.global()).future,
      );
      expect(state.theme.bubbleColorSent, const Color(0xFFC97D0C));
    });

    test('scoped Saathi chat defaults to the character signature look',
        () async {
      final container = ProviderContainer(overrides: [
        localDbProvider.overrideWithValue(FakeLocalDb()),
        apiClientProvider.overrideWithValue(FailingApiClient()),
      ]);
      addTearDown(container.dispose);

      final asha = await container.read(
        themeProvider(const ChatThemeScopeKey.saathi('asha')).future,
      );
      expect(asha.theme.presetFallbackMatches('saathi_asha'), isTrue);

      // A match scope never inherits a Saathi signature default.
      final match = await container.read(
        themeProvider(const ChatThemeScopeKey.match('m1')).future,
      );
      expect(match.theme.wallpaperValue,
          ChatWallpaperTheme.factoryDefault.wallpaperValue);
    });

    test('optimistic update keeps local value when sync fails', () async {
      final db = FakeLocalDb();
      final container = ProviderContainer(overrides: [
        localDbProvider.overrideWithValue(db),
        apiClientProvider.overrideWithValue(FailingApiClient()),
      ]);
      addTearDown(container.dispose);

      await container.read(themeProvider(const ChatThemeScopeKey.global()).future);
      const next = ChatWallpaperTheme(
        wallpaperType: WallpaperType.solid,
        wallpaperValue: '#1F6F54',
        bubbleColorSent: Color(0xFF1F6F54),
        bubbleColorReceived: Color(0xFFDCEFE7),
      );
      await container
          .read(themeProvider(const ChatThemeScopeKey.global()).notifier)
          .apply(next);

      // Local store holds the new choice even though the backend was down…
      expect(db._store['global']?['wallpaper_value'], '#1F6F54');
      // …and in-memory state reflects it (never reverted mid-session).
      final state = container.read(themeProvider(const ChatThemeScopeKey.global())).valueOrNull;
      expect(state?.syncPending, isTrue);
      expect(state?.theme.wallpaperValue, '#1F6F54');
    });
  });

  group('SaathiSessionState daily cap (doc 5 §2.5 mirror)', () {
    test('cap reached at 1 proactive message per day', () {
      const fresh = SaathiSessionState(sessionId: 's');
      expect(fresh.dailyCapReached, isFalse);
      const capped = SaathiSessionState(sessionId: 's', proactiveMessagesToday: 1);
      expect(capped.dailyCapReached, isTrue);
    });
  });
}

extension on ChatWallpaperTheme {
  bool presetFallbackMatches(String presetId) {
    final preset = MilanChatPresets.byId(presetId);
    return preset != null &&
        bubbleColorSent == preset.theme.bubbleColorSent &&
        wallpaperValue == preset.theme.wallpaperValue;
  }
}
