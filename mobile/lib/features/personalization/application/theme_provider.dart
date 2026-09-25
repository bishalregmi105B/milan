import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/theme/chat_theme_presets.dart';
import '../../../app/theme/chat_theme_tokens.dart';
import '../../../core/network/api_client.dart';
import '../../../core/storage/local_db.dart';
import '../../saathi/application/saathi_session_provider.dart';

/// Doc 3 §4 — resolved [ChatWallpaperTheme] per scope
/// ('global' / 'match:<matchId>' / 'saathi:<characterId>').
///
/// Resolution order: scoped override → global default → Milan factory default.
/// Writes go optimistic-local-first (instant, offline-capable) then sync to
/// `/api/v1/personalization/theme*`; on sync failure we KEEP the local value
/// and retry silently — never reverting the user's choice mid-session.

class ChatThemeState {
  const ChatThemeState({required this.theme, this.syncPending = false});
  final ChatWallpaperTheme theme;
  final bool syncPending;
}

class ThemeScopeNotifier extends FamilyAsyncNotifier<ChatThemeState, ChatThemeScopeKey> {
  LocalDb get _db => ref.read(localDbProvider);
  ApiClient get _api => ref.read(apiClientProvider);

  @override
  Future<ChatThemeState> build(ChatThemeScopeKey arg) async {
    // 1) instant offline path: last locally-resolved value
    final cached = await _db.loadResolvedTheme(arg.storageKey);
    if (cached != null) {
      unawaitedSync();
      return ChatThemeState(
        theme: _mergeWithDefaults(ChatWallpaperTheme.fromBackendJson(cached)),
      );
    }
    // 2) server truth
    try {
      final json = await _fetchResolvedFromBackend(arg);
      if (json != null) {
        await _db.saveResolvedTheme(arg.storageKey, json, synced: true);
        return ChatThemeState(theme: _mergeWithDefaults(ChatWallpaperTheme.fromBackendJson(json)));
      }
    } on AppException {
      // fall through to defaults; retried on next watch/mutation
    }
    return ChatThemeState(theme: _defaultForScope(arg));
  }

  ChatWallpaperTheme _mergeWithDefaults(ChatWallpaperTheme resolved) {
    var merged = resolved;
    if (merged.bubbleColorSent == null || merged.bubbleColorReceived == null) {
      final preset = MilanChatPresets.byId(merged.wallpaperValue);
      merged = merged.copyWith(
        bubbleColorSent: merged.bubbleColorSent ?? preset?.theme.bubbleColorSent,
        bubbleColorReceived:
            merged.bubbleColorReceived ?? preset?.theme.bubbleColorReceived,
      );
    }
    return merged;
  }

  ChatWallpaperTheme _defaultForScope(ChatThemeScopeKey scope) {
    if (scope.kind == ChatThemeScopeKind.saathi && scope.id != null) {
      // Signature character look applied on first open (doc 3 §6).
      return MilanChatPresets.defaultForSaathiCharacter(scope.id!);
    }
    return ChatWallpaperTheme.factoryDefault;
  }

  /// P0-4: the backend's /personalization/theme/saathi_session/:scope_id
  /// parses scope_id as a UUID of the user's SaathiSession — a character key
  /// like 'asha' makes uuid.UUID raise → 500. Saathi scopes stay keyed by
  /// character locally (storageKey) but resolve to the ACTIVE session UUID
  /// for every backend call. No session yet → null → themes stay local-only.
  Future<String?> _saathiSessionId(String characterKey) async {
    try {
      final session = await ref.read(saathiSessionProvider(characterKey).future);
      return session.sessionId;
    } on AppException {
      return null;
    }
  }

  Future<Map<String, dynamic>?> _fetchResolvedFromBackend(
      ChatThemeScopeKey scope) async {
    switch (scope.kind) {
      case ChatThemeScopeKind.global:
        return _api.get<Map<String, dynamic>>('/personalization/theme');
      case ChatThemeScopeKind.match:
        return _api.get<Map<String, dynamic>>(
            '/personalization/theme/match/${scope.id}');
      case ChatThemeScopeKind.saathi:
        final sessionId = await _saathiSessionId(scope.id!);
        if (sessionId == null) return null; // local-only until a session exists
        return _api.get<Map<String, dynamic>>(
            '/personalization/theme/saathi_session/$sessionId');
      }
  }

  /// Optimistic update: persist locally first, then best-effort backend sync.
  /// Named `apply` to avoid clashing with AsyncNotifier.update (Riverpod 2.x).
  Future<void> apply(ChatWallpaperTheme next) async {
    final scope = arg;
    state = AsyncData(ChatThemeState(theme: next, syncPending: true));
    final json = next.toBackendJson(scope: _scopeName(scope), scopeId: scope.id);
    await _db.saveResolvedTheme(scope.storageKey, json, synced: false);
    try {
      await _pushToBackend(scope, json);
      await _db.saveResolvedTheme(scope.storageKey, json, synced: true);
      state = AsyncData(ChatThemeState(theme: next));
    } on AppException {
      // Keep local value; silent retry later (doc 3 §4).
      ref.keepAlive();
    }
  }

  /// One-tap reset at any level (doc 2 §2.7.1).
  Future<void> reset() async {
    final scope = arg;
    try {
      switch (scope.kind) {
        case ChatThemeScopeKind.global:
          await _api.delete('/personalization/theme');
        case ChatThemeScopeKind.match:
          await _api.delete('/personalization/theme/match/${scope.id}');
        case ChatThemeScopeKind.saathi:
          final sessionId = await _saathiSessionId(scope.id!);
          if (sessionId != null) {
            await _api.delete('/personalization/theme/saathi_session/$sessionId');
          }
      }
    } on AppException {
      // backend unreachable — still revert locally so UX matches intent
    }
    await _db.saveResolvedTheme(
      scope.storageKey,
      _defaultForScope(scope)
          .toBackendJson(scope: _scopeName(scope), scopeId: scope.id),
      synced: true,
    );
    state = AsyncData(ChatThemeState(theme: _defaultForScope(scope)));
  }

  void unawaitedSync() {
    Future.microtask(() async {
      final cached = await _db.loadResolvedTheme(arg.storageKey);
      if (cached != null) {
        try {
          await _pushToBackend(arg, cached);
          await _db.markThemesSynced();
        } on AppException {
          // stay quiet; retried on next change
        }
      }
    });
  }

  String _scopeName(ChatThemeScopeKey scope) {
    switch (scope.kind) {
      case ChatThemeScopeKind.global:
        return 'global';
      case ChatThemeScopeKind.match:
        return 'match';
      case ChatThemeScopeKind.saathi:
        return 'saathi_session';
    }
  }

  Future<void> _pushToBackend(
      ChatThemeScopeKey scope, Map<String, dynamic> json) async {
    switch (scope.kind) {
      case ChatThemeScopeKind.global:
        await _api.put('/personalization/theme', body: json);
      case ChatThemeScopeKind.match:
        await _api.put('/personalization/theme/match/${scope.id}', body: json);
      case ChatThemeScopeKind.saathi:
        final sessionId = await _saathiSessionId(scope.id!);
        if (sessionId == null) return; // local-only until a session exists
        await _api.put('/personalization/theme/saathi_session/$sessionId',
            body: {...json, 'scope_id': sessionId});
    }
  }
}

final themeProvider = AsyncNotifierProvider.family<ThemeScopeNotifier,
    ChatThemeState, ChatThemeScopeKey>(ThemeScopeNotifier.new);
