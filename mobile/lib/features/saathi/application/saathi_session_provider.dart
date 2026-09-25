import 'dart:ui';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class SaathiCharacter {
  const SaathiCharacter({
    required this.id,
    required this.key,
    required this.name,
    required this.description,
  });
  final String id;
  final String key;
  final String name;
  final String description;

  factory SaathiCharacter.fromJson(Map<String, dynamic> json) => SaathiCharacter(
        id: json['id'] as String,
        key: json['key'] as String,
        name: json['name'] as String,
        description: json['persona_description'] as String? ?? '',
      );
}

class SaathiMessageItem {
  const SaathiMessageItem({required this.role, required this.content});
  final String role; // 'user' | 'saathi'
  final String content;

  bool get isAi => role == 'saathi';
}

class SaathiSessionState {
  const SaathiSessionState({
    required this.sessionId,
    this.messages = const [],
    this.lastProactiveMessageAt,
    this.proactiveMessagesToday = 0,
    this.isPaused = false,
    this.proactiveOptIn = false,
    this.showCrisisCard = false,
    this.degraded = false,
    this.bondStage,
    this.intimacyLevel = 0,
    this.intimacyCap = 25,
    this.streakDays = 0,
    this.characterMood,
    this.presenceActivity,
    this.presenceState,
    this.isAiCharacter = true,
    this.characterDisplayName = 'Saathi · AI',
  });

  final String sessionId;
  final List<SaathiMessageItem> messages;
  final DateTime? lastProactiveMessageAt;
  final int proactiveMessagesToday;
  final bool isPaused;
  final bool proactiveOptIn;
  final bool showCrisisCard;
  final bool degraded;
  // Bond HUD (master plan §4.6) — no numeric intimacy meter is shown to the
  // user (CA SB 243 / FTC 6(b) pattern); only the stage name + streak.
  final String? bondStage;
  final int intimacyLevel;
  final int intimacyCap;
  final int streakDays;
  final String? characterMood;
  final String? presenceActivity;
  final String? presenceState;
  final bool isAiCharacter;
  final String characterDisplayName;

  /// Client-side UX safeguard mirroring the server cap (doc 3 §4): the server
  /// enforces the real cap; this only gates UI affordances.
  bool get dailyCapReached => proactiveMessagesToday >= 1;

  /// Text of the latest user message — powers long-press-to-regenerate.
  String? get lastUserBody {
    for (final m in messages.reversed) {
      if (!m.isAi) return m.content;
    }
    return null;
  }

  SaathiSessionState copyWith({
    String? sessionId,
    List<SaathiMessageItem>? messages,
    int? proactiveMessagesToday,
    bool? isPaused,
    bool? proactiveOptIn,
    bool? showCrisisCard,
    bool? degraded,
    String? bondStage,
    int? intimacyLevel,
    int? intimacyCap,
    int? streakDays,
    String? characterMood,
    String? presenceActivity,
    String? presenceState,
    bool? isAiCharacter,
    String? characterDisplayName,
  }) {
    return SaathiSessionState(
      sessionId: sessionId ?? this.sessionId,
      messages: messages ?? this.messages,
      proactiveMessagesToday: proactiveMessagesToday ?? this.proactiveMessagesToday,
      isPaused: isPaused ?? this.isPaused,
      proactiveOptIn: proactiveOptIn ?? this.proactiveOptIn,
      showCrisisCard: showCrisisCard ?? this.showCrisisCard,
      degraded: degraded ?? this.degraded,
      bondStage: bondStage ?? this.bondStage,
      intimacyLevel: intimacyLevel ?? this.intimacyLevel,
      intimacyCap: intimacyCap ?? this.intimacyCap,
      streakDays: streakDays ?? this.streakDays,
      characterMood: characterMood ?? this.characterMood,
      presenceActivity: presenceActivity ?? this.presenceActivity,
      presenceState: presenceState ?? this.presenceState,
      isAiCharacter: isAiCharacter ?? this.isAiCharacter,
      characterDisplayName: characterDisplayName ?? this.characterDisplayName,
    );
  }

  static SaathiSessionState fromSessionDto(Map<String, dynamic> res) {
    final bond = res['bond'] as Map<String, dynamic>?;
    final presence = res['presence'] as Map<String, dynamic>?;
    return SaathiSessionState(
      sessionId: res['session_id'] as String,
      proactiveMessagesToday: res['proactive_messages_today'] as int? ?? 0,
      isPaused: res['is_paused'] as bool? ?? false,
      proactiveOptIn: res['proactive_opt_in'] as bool? ?? false,
      bondStage: bond?['stage'] as String?,
      intimacyLevel: (bond?['intimacy_level'] as num?)?.toInt() ?? 0,
      intimacyCap: (bond?['tier_cap'] as num?)?.toInt() ?? 25,
      streakDays: (bond?['streak_days'] as num?)?.toInt() ?? 0,
      characterMood: bond?['mood'] as String?,
      presenceActivity: presence?['activity'] as String?,
      presenceState: presence?['state'] as String?,
      isAiCharacter: res['is_ai'] as bool? ?? true,
      characterDisplayName:
          res['character_name'] as String? ?? 'Saathi · AI',
    );
  }
}

class SaathiSessionController
    extends FamilyAsyncNotifier<SaathiSessionState, String> {
  @override
  Future<SaathiSessionState> build(String characterId) async {
    final res = await ref.read(apiClientProvider).post<Map<String, dynamic>>(
        '/saathi/$characterId/sessions');
    return SaathiSessionState.fromSessionDto(res);
  }

  /// Sends [body]; [regenerateVariant] re-rolls the LAST reply for the same
  /// user text (swipe-to-regenerate, master plan §12.2 #26). [toneChip]
  /// steers this reply's tone (director chips #33).
  Future<void> send(String body,
      {int regenerateVariant = 0, String? toneChip}) async {
    final current = state.valueOrNull;
    if (current == null || current.isPaused) return;
    List<SaathiMessageItem> optimistic = current.messages;
    if (regenerateVariant == 0) {
      optimistic = [...current.messages, SaathiMessageItem(role: 'user', content: body)];
      state = AsyncData(current.copyWith(messages: optimistic));
    } else {
      // drop trailing AI bubble(s) being re-rolled
      final trimmed = [...current.messages];
      while (trimmed.isNotEmpty && trimmed.last.isAi) {
        trimmed.removeLast();
      }
      state = AsyncData(current.copyWith(messages: trimmed));
    }
    try {
      final res = await ref.read(apiClientProvider).post<Map<String, dynamic>>(
          '/saathi/sessions/${current.sessionId}/messages',
          body: {
            'body': body,
            if (regenerateVariant > 0) 'regenerate_variant': regenerateVariant,
            if (toneChip != null && toneChip.isNotEmpty) 'tone_chip': toneChip,
          });
      final delaySeconds =
          ((res['typing_delay_seconds'] as num?)?.toDouble() ?? 1.2)
              .clamp(0.8, 4.0);
      await Future<void>.delayed(Duration(milliseconds: (delaySeconds * 1000).round()));
      final updated = state.valueOrNull ?? current;
      final segments = (res['segments'] as List?) ??
          [if (res['reply'] != null) res['reply']];
      final bond = res['bond'] as Map<String, dynamic>?;
      state = AsyncData(updated.copyWith(
        messages: [
          ...updated.messages,
          for (final s in segments)
            SaathiMessageItem(role: 'saathi', content: s.toString()),
        ],
        showCrisisCard: res['show_crisis_card'] as bool? ?? false,
        bondStage: bond?['stage'] as String? ?? updated.bondStage,
        intimacyLevel:
            (bond?['intimacy_level'] as num?)?.toInt() ?? updated.intimacyLevel,
        streakDays: (bond?['streak_days'] as num?)?.toInt() ?? updated.streakDays,
        characterMood: bond?['mood'] as String? ?? updated.characterMood,
      ));
    } on AppException catch (e) {
      if (e.statusCode == 503) {
        state = AsyncData((state.valueOrNull ?? current).copyWith(degraded: true));
      }
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> memoryItems() async {
    final current = state.valueOrNull;
    if (current == null) return const [];
    final res = await ref.read(apiClientProvider).get<Map<String, dynamic>>(
        '/saathi/sessions/${current.sessionId}/memory');
    return (res['items'] as List).cast<Map<String, dynamic>>();
  }

  Future<void> deleteMemory(String itemId) async {
    final current = state.valueOrNull;
    if (current == null) return;
    await ref.read(apiClientProvider).delete(
        '/saathi/sessions/${current.sessionId}/memory/$itemId');
  }

  Future<void> clearAllMemory() async {
    final current = state.valueOrNull;
    if (current == null) return;
    await ref
        .read(apiClientProvider)
        .delete('/saathi/sessions/${current.sessionId}/memory');
  }

  /// P1-10: seeds the message list from GET /saathi/sessions/:id/messages so
  /// history survives leaving and re-opening the chat. Never wipes messages
  /// already appended optimistically in this session.
  Future<void> loadHistory() async {
    try {
      final current = await future;
      final res = await ref.read(apiClientProvider).get<Map<String, dynamic>>(
          '/saathi/sessions/${current.sessionId}/messages');
      final history = (res['messages'] as List)
          .map((e) => SaathiMessageItem(
                role: e['role'] as String,
                content: e['content'] as String,
              ))
          .toList();
      final live = state.valueOrNull;
      if (live == null || live.messages.isNotEmpty) return;
      state = AsyncData(live.copyWith(messages: history));
    } on AppException {
      // history is best-effort; the chat still works without it
    }
  }

  Future<void> updateSettings({bool? isPaused, bool? proactiveOptIn}) async {
    final current = state.valueOrNull;
    if (current == null) return;
    final previous = current;
    // Optimistic flip; reverted below if the PUT fails (P1-9).
    state = AsyncData(current.copyWith(
      isPaused: isPaused ?? current.isPaused,
      proactiveOptIn: proactiveOptIn ?? current.proactiveOptIn,
    ));
    try {
      final res = await ref.read(apiClientProvider).put<Map<String, dynamic>>(
          '/saathi/sessions/${current.sessionId}/settings',
          body: {
            if (isPaused != null) 'is_paused': isPaused,
            if (proactiveOptIn != null) 'proactive_opt_in': proactiveOptIn,
          });
      state = AsyncData((state.valueOrNull ?? current).copyWith(
        isPaused: res['is_paused'] as bool?,
        proactiveOptIn: res['proactive_opt_in'] as bool?,
      ));
    } on AppException {
      state = AsyncData(previous);
      rethrow; // caller surfaces the error
    }
  }
}

final saathiSessionProvider = AsyncNotifierProvider.family<
    SaathiSessionController, SaathiSessionState, String>(
  SaathiSessionController.new,
);

/// §14 companion roster — loaded from the API, never hardcoded. Each card is
/// a real companion account that lives in the unified inbox once started.
class CompanionCard {
  const CompanionCard({
    required this.key,
    required this.name,
    required this.description,
    required this.accentColor,
    this.locked = false,
    this.avatarUrl,
  });
  final String key;
  final String name;
  final String description;
  final bool locked;
  final String? avatarUrl;
  // Stable per-key hue for the fallback initial (no hardcoded per-character art).
  final Color accentColor;
}

class CompanionRosterState {
  const CompanionRosterState({required this.characters});
  final List<CompanionCard> characters;
}

class CompanionRosterController extends AsyncNotifier<CompanionRosterState> {
  static const _palette = [
    Color(0xFF7B1E3A), Color(0xFFB8791A), Color(0xFF1F6F54),
    Color(0xFF43535C), Color(0xFF5B3E91), Color(0xFF8C2F39),
  ];

  @override
  Future<CompanionRosterState> build() async {
    final res = await ref.read(apiClientProvider).get<Map<String, dynamic>>(
        '/saathi/characters');
    final cards = <CompanionCard>[];
    for (final c in (res['characters'] as List)) {
      final map = c as Map<String, dynamic>;
      final key = map['key'] as String;
      final codePoint = key.codeUnits.fold<int>(0, (a, b) => a + b);
      cards.add(CompanionCard(
        key: key,
        name: map['name'] as String? ?? key,
        description: map['persona_description'] as String? ?? '',
        locked: map['locked'] as bool? ?? false,
        avatarUrl: map['illustrated_avatar_url'] as String?,
        accentColor: _palette[codePoint % _palette.length],
      ));
    }
    return CompanionRosterState(characters: cards);
  }

  Future<void> refresh() async {
    ref.invalidateSelf();
    await future;
  }
}

final companionRosterProvider = AsyncNotifierProvider<CompanionRosterController,
    CompanionRosterState>(CompanionRosterController.new);
