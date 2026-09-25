import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/websocket_client.dart';
import '../../../core/realtime/realtime_bridge.dart';
import '../../../core/storage/local_db.dart';
import '../../auth/application/auth_provider.dart';

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.senderId,
    this.body,
    this.mediaUrl,
    this.mediaType,
    this.readAt,
    this.isAiSuggested = false,
    required this.createdAt,
  });

  final String id;
  final String senderId;
  final String? body;
  final String? mediaUrl;
  // image | gif | audio — picks the bubble renderer (doc 8 §A2.6/§A2.12)
  final String? mediaType;
  final DateTime? readAt;
  final bool isAiSuggested;
  final DateTime createdAt;

  bool get isRead => readAt != null;

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
        id: (json['id'] ?? '').toString(),
        senderId: (json['sender_id'] ?? '').toString(),
        body: json['body'] as String?,
        mediaUrl: json['media_url'] as String?,
        mediaType: json['media_type'] as String?,
        readAt: json['read_at'] == null
            ? null
            : DateTime.tryParse(json['read_at'] as String),
        isAiSuggested: json['is_ai_suggested'] as bool? ?? false,
        // tryParse + fallback so one malformed row can never throw and turn the
        // whole thread into an unrecoverable error screen (the socket path is
        // already this defensive; the REST path was not).
        createdAt: DateTime.tryParse((json['created_at'] ?? '').toString()) ??
            DateTime.now(),
      );

  Map<String, Object?> toCacheRow(String matchId) => {
        'id': id,
        'match_id': matchId,
        'sender_id': senderId,
        'body': body,
        'media_url': mediaUrl,
        'media_type': mediaType,
        'read_at': readAt?.toIso8601String(),
        'is_ai_suggested': isAiSuggested ? 1 : 0,
        'created_at': createdAt.toIso8601String(),
      };
}

class MatchSummary {
  const MatchSummary({
    required this.matchId,
    required this.otherUserId,
    required this.otherName,
    this.otherPhotoUrl,
    this.lastMessage,
    this.lastMessageAt,
    this.lastMessageIsMedia = false,
    this.unread = false,
    this.unreadCount = 0,
    this.kind = 'human',
    this.isAi = false,
  });
  final String matchId;
  final String otherUserId;
  final String otherName;
  final String? otherPhotoUrl;
  final String? lastMessage;
  final DateTime? lastMessageAt;
  final bool lastMessageIsMedia;
  final bool unread;
  final int unreadCount;
  // human | companion — used ONLY for the AI badge; the row and the chat
  // screen it opens are identical (§14 unified inbox).
  final String kind;
  final bool isAi;

  factory MatchSummary.fromJson(Map<String, dynamic> json) {
    final user = json['user'] as Map<String, dynamic>?;
    // doc 8 §A2.4: `last_message` was returned by the server and never
    // parsed — every inbox row read "Say namaste 👋".
    final lastBody = json['last_message'] as String?;
    return MatchSummary(
      matchId: json['id'] as String,
      otherUserId: (json['other_user_id'] ?? '') as String,
      otherName: (user?['display_name'] as String?) ?? 'Milan user',
      otherPhotoUrl: user?['photo_url'] as String?,
      lastMessage: lastBody,
      lastMessageAt: json['last_message_at'] == null
          ? null
          : DateTime.tryParse(json['last_message_at'] as String),
      lastMessageIsMedia: lastBody == null && json['last_message_at'] != null,
      unread: (json['unread_count'] as num?)?.toInt() != null && (json['unread_count'] as num).toInt() > 0,
      unreadCount: (json['unread_count'] as num?)?.toInt() ?? 0,
      kind: json['kind'] as String? ?? 'human',
      isAi: (user?['is_ai'] as bool?) ?? json['kind'] == 'companion',
    );
  }
}

class MatchesController extends AsyncNotifier<List<MatchSummary>> {
  @override
  Future<List<MatchSummary>> build() async {
    // The bridge owns the socket subscription and bumps this tick on any live
    // message. listen + invalidateSelf rather than watch: a watched dependency
    // makes the rebuild a *reload*, which AsyncValue.when renders as loading —
    // the inbox would flash its skeleton on every arriving message. A self
    // refresh keeps the current rows on screen while the refetch runs.
    ref.listen(matchesRefreshTick, (_, __) => ref.invalidateSelf());
    // Let load failures propagate to AsyncError so the inbox's error+Retry UI
    // actually runs. Swallowing them returned [] — indistinguishable from a
    // real empty inbox, with no way to recover from a network blip.
    final res =
        await ref.read(apiClientProvider).get<Map<String, dynamic>>('/matches');
    return (res['matches'] as List? ?? const [])
        .map((e) => MatchSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

final matchesProvider =
    AsyncNotifierProvider<MatchesController, List<MatchSummary>>(
        MatchesController.new);

class ChatThreadController
    extends AutoDisposeFamilyAsyncNotifier<List<ChatMessage>, String> {
  /// Messages delivered by the socket during (or before) the REST refetch.
  /// The refetch's server snapshot can lag the socket — a companion reply
  /// generated AFTER the snapshot was taken would otherwise be overwritten
  /// and vanish from the thread (the "typing shows but message never
  /// appears" bug). Socket truth always wins over a stale snapshot.
  final Set<String> _socketReceivedIds = {};

  @override
  Future<List<ChatMessage>> build(String matchId) async {
    final db = ref.read(localDbProvider);
    final ws = ref.read(websocketClientProvider);
    final bridge = ref.read(realtimeBridgeProvider);
    // joinMatchRoom is idempotent and connects if needed; the client's
    // watchdog re-joins any room whose ack never came back.
    ws.joinMatchRoom(matchId);

    // Be visible to others the moment the thread opens (doc 8 Part D.2 —
    // real presence; the heartbeat also touches last_active_at server-side).
    final myId = ref.read(currentUserIdProvider);
    if (myId != null) {
      ws.emit('presence:heartbeat', {'user_id': myId, 'at': DateTime.now().toIso8601String()});
    }

    // Live messages come from the session-scoped bridge, NOT from a socket
    // listener owned by this provider: this notifier is disposed whenever the
    // route is popped or the family key is re-read, and a listener that dies
    // with it is why messages stopped landing in the open thread.
    final sub = bridge.messagesFor(matchId).listen((inbound) {
      final message = ChatMessage(
        id: inbound.id,
        senderId: inbound.senderId,
        body: inbound.body,
        mediaUrl: inbound.mediaUrl,
        mediaType: inbound.mediaType,
        isAiSuggested: inbound.isAiSuggested,
        createdAt: inbound.createdAt,
      );
      _socketReceivedIds.add(message.id);
      _lastSocketMessages[message.id] = message;
      _append(message);
      if (message.senderId != myId) {
        ref.read(companionPendingProvider(matchId).notifier).clear();
      }
    });
    ref.onDispose(sub.cancel);

    // doc 8 §A2.5: cache-first for an instant paint, then ALWAYS refetch —
    // the thread used to hydrate once from sqflite and never reconcile, so
    // messages sent while offline (auto-texts, human replies) never appeared.
    // The bridge caches every inbound message even when no thread is open, so
    // this first paint already contains whatever arrived while we were away.
    final cached = await db.messagesForMatch(matchId);
    if (cached.isNotEmpty) {
      state = AsyncData(cached.map(_fromCacheRow).toList());
    }
    try {
      final res = await ref.read(apiClientProvider).get<Map<String, dynamic>>(
          '/matches/$matchId/messages');
      final server =
          (res['messages'] as List).map((e) => ChatMessage.fromJson(e as Map<String, dynamic>)).toList();
      _mergeServer(server);
      for (final m in state.valueOrNull ?? const <ChatMessage>[]) {
        db.cacheMessage(m.toCacheRow(matchId));
      }
      return state.valueOrNull ?? server;
    } on AppException {
      if (cached.isNotEmpty) return state.valueOrNull ?? const [];
      rethrow;
    }
  }

  ChatMessage _fromCacheRow(Map<String, Object?> row) => ChatMessage(
        id: (row['id'] ?? '').toString(),
        senderId: (row['sender_id'] ?? '').toString(),
        body: row['body'] as String?,
        mediaUrl: row['media_url'] as String?,
        mediaType: row['media_type'] as String?,
        readAt: row['read_at'] == null
            ? null
            : DateTime.tryParse(row['read_at'] as String),
        isAiSuggested: row['is_ai_suggested'] == 1,
        createdAt: DateTime.tryParse((row['created_at'] ?? '').toString()) ??
            DateTime.now(),
      );

  /// Server snapshot MERGES with current state — never replaces it. Rows the
  /// socket already delivered are kept even when the (older) REST snapshot
  /// does not contain them; server rows only ADD or refresh (read receipts).
  void _mergeServer(List<ChatMessage> server) {
    final current = [...(state.valueOrNull ?? const <ChatMessage>[])];
    for (final m in server) {
      final index = current.indexWhere((c) => c.id == m.id);
      if (index >= 0) {
        current[index] = m;
      } else {
        current.add(m);
      }
    }
    // Re-add anything the socket delivered that the stale snapshot lacks.
    for (final id in _socketReceivedIds) {
      if (!current.any((c) => c.id == id)) {
        final cached = _lastSocketMessages[id];
        if (cached != null) current.add(cached);
      }
    }
    current.sort((a, b) => a.createdAt.compareTo(b.createdAt));
    state = AsyncData(current);
  }

  final Map<String, ChatMessage> _lastSocketMessages = {};

  /// Dedups by id: the backend broadcasts `chat:message` to the whole match
  /// room, so the sender's own client receives an echo of what [send] already
  /// appended optimistically (same server id).
  void _append(ChatMessage message) {
    final current = state.valueOrNull ?? <ChatMessage>[];
    final next = [...current];
    final existing = next.indexWhere((m) => m.id == message.id);
    if (existing >= 0) {
      next[existing] = message;
    } else {
      next.add(message);
    }
    state = AsyncData(next);
  }

  Future<void> send(String body, {int regenerateVariant = 0}) async {
    final matchId = arg;
    final pending = ref.read(companionPendingProvider(matchId).notifier);
    // Show a typing bubble only if the reply takes a beat. A human message
    // POST returns in a few hundred ms, so the delayed arm never fires for it;
    // a companion reply takes a couple of seconds to generate, so the bubble
    // appears during the wait and is cleared the moment her reply is appended.
    pending.arm();

    final Map<String, dynamic> res;
    try {
      res = await ref.read(apiClientProvider).post<Map<String, dynamic>>(
          '/matches/$matchId/messages',
          body: {
            'body': body,
            if (regenerateVariant > 0) 'regenerate_variant': regenerateVariant,
          });
    } catch (_) {
      pending.clear();
      rethrow;
    }

    _append(ChatMessage(
      id: res['id'] as String,
      senderId: ref.read(currentUserIdProvider) ?? 'me',
      body: body,
      createdAt: DateTime.now(),
    ));

    // Primary path: the companion's reply is generated synchronously and
    // returned right here. No socket dependency — the reply can never get
    // stuck behind a dropped `chat:message`. The socket still echoes each
    // segment for other devices; _append dedups by id.
    final reply = res['companion_reply'] as Map<String, dynamic>?;
    if (reply != null) {
      pending.clear();
      for (final m in (reply['messages'] as List? ?? const [])) {
        final map = m as Map<String, dynamic>;
        _append(ChatMessage(
          id: map['id'] as String,
          senderId: map['sender_id'] as String,
          body: map['body'] as String?,
          mediaUrl: map['media_url'] as String?,
          mediaType: map['media_type'] as String?,
          createdAt: DateTime.tryParse((map['created_at'] ?? '') as String) ??
              DateTime.now(),
        ));
      }
      return;
    }

    // Back-compat: an older server may still answer asynchronously with
    // `companion_pending` and deliver over the socket. Keep the deferred bubble
    // (with its own fail-safe) for that case only.
    if (res['companion_pending'] == true) {
      pending.armDeferred();
      return;
    }

    // Plain human message — nothing pending.
    pending.clear();
  }

  /// Media message (image/GIF/audio — no video in chat): optimistic bubble +
  /// socket echo dedupes against the server broadcast.
  Future<void> sendMedia({required String mediaUrl, String? mediaType, String? caption}) async {
    final matchId = arg;
    final res = await ref.read(apiClientProvider).post<Map<String, dynamic>>(
        '/matches/$matchId/messages',
        body: {
          'media_url': mediaUrl,
          if (mediaType != null) 'media_type': mediaType,
          if (caption != null) 'body': caption,
        });
    _append(ChatMessage(
      id: res['id'] as String,
      senderId: ref.read(currentUserIdProvider) ?? 'me',
      mediaUrl: mediaUrl,
      mediaType: mediaType ?? 'image',
      body: caption,
      createdAt: DateTime.now(),
    ));
  }

  Future<List<String>> icebreakers() async {
    try {
      final res = await ref
          .read(apiClientProvider)
          .post<Map<String, dynamic>>('/matches/$arg/icebreakers');
      return (res['suggestions'] as List).cast<String>();
    } on AppException {
      // graceful degradation: silently hide rather than break chat (doc 5 §1)
      return const [];
    }
  }
}

final chatThreadProvider = AsyncNotifierProvider.autoDispose.family<
    ChatThreadController, List<ChatMessage>, String>(ChatThreadController.new);

/// True while the companion's reply is on its way — drives the local typing
/// bubble until the socket delivers her message (the server's typing hint can
/// be missed entirely if the socket reconnects mid-generation).
///
/// It is NOT armed the instant you press send: she has to read the message
/// first. [armDeferred] waits [readingDelay] before the bubble appears, which
/// is what makes the indicator honest — the server's own `chat:typing` usually
/// arrives inside that window and takes over.
final companionPendingProvider =
    NotifierProvider.autoDispose.family<CompanionPendingController, bool, String>(
        CompanionPendingController.new);

class CompanionPendingController extends AutoDisposeFamilyNotifier<bool, String> {
  Timer? _failsafe;
  Timer? _delay;

  static const readingDelay = Duration(milliseconds: 2200);

  @override
  bool build(String arg) {
    ref.onDispose(() {
      _failsafe?.cancel();
      _delay?.cancel();
    });
    return false;
  }

  /// Show the bubble after a short pause while a synchronous reply is being
  /// generated, then clear it explicitly when the reply is appended. The 30s
  /// fail-safe only matters if the request hangs. Used by the synchronous send
  /// path — the delay is short because we are already awaiting the reply.
  void arm() {
    _delay?.cancel();
    _failsafe?.cancel();
    _delay = Timer(const Duration(milliseconds: 600), () {
      state = true;
      _failsafe = Timer(const Duration(seconds: 30), () {
        if (state) state = false;
      });
    });
  }

  /// Show the bubble after a short reading pause, with a 120s fail-safe: a
  /// crashed generation must never leave "typing…" up forever. Used only by the
  /// legacy asynchronous (socket-delivered) reply path.
  void armDeferred() {
    _delay?.cancel();
    _failsafe?.cancel();
    _delay = Timer(readingDelay, () {
      state = true;
      _failsafe = Timer(const Duration(seconds: 120), () {
        if (state) state = false;
      });
    });
  }

  /// Her message arrived (or generation failed) — take the bubble down and
  /// cancel a pending arm so it cannot pop up after the reply.
  void clear() {
    _delay?.cancel();
    _failsafe?.cancel();
    if (state) state = false;
  }
}

class PresenceState {
  const PresenceState(
      {required this.online, this.lastActiveAt, this.minutesAgo, this.fetchedAt});
  final bool online;
  final DateTime? lastActiveAt;
  final int? minutesAgo;
  final DateTime? fetchedAt;

  /// Minutes since the peer was last seen, aged forward from when we learned
  /// it. Without this a header fetched once said "Active 2m ago" an hour later.
  int? get minutesAgoNow {
    if (online) return 0;
    final base = minutesAgo;
    final at = fetchedAt;
    if (base == null) {
      final last = lastActiveAt;
      if (last == null) return null;
      return DateTime.now().difference(last).inMinutes;
    }
    if (at == null) return base;
    return base + DateTime.now().difference(at).inMinutes;
  }
}

/// Presence for peers: socket `presence:update` events merged with a REST
/// cold-open fetch (`/presence/<id>`) so the header's living indicator is
/// real from the first frame (doc 8 §B signature presence dot).
class PresenceController extends Notifier<Map<String, PresenceState>> {
  @override
  Map<String, PresenceState> build() {
    final ws = ref.read(websocketClientProvider);
    void onUpdate(dynamic payload) {
      if (payload is! Map) return;
      final userId = payload['user_id']?.toString();
      if (userId == null) return;
      final online = payload['online'] as bool? ?? false;
      final next = {...state};
      next[userId] = PresenceState(
        online: online,
        lastActiveAt: payload['last_active_at'] == null
            ? DateTime.now()
            : DateTime.tryParse('${payload['last_active_at']}'),
        // An online peer is 0 minutes ago; going offline starts the clock now.
        minutesAgo: 0,
        fetchedAt: DateTime.now(),
      );
      state = next;
    }

    ws.on('presence:update', onUpdate);
    ref.onDispose(() => ws.off('presence:update', onUpdate));
    return {};
  }

  /// REST lookup, refreshed when the cached entry is older than 45s so a chat
  /// header that stays open keeps telling the truth. Concurrent calls for the
  /// same user collapse into one request.
  final Set<String> _inFlight = {};

  Future<void> ensure(String userId) async {
    final existing = state[userId];
    final fresh = existing?.fetchedAt != null &&
        DateTime.now().difference(existing!.fetchedAt!) <
            const Duration(seconds: 45);
    if (fresh || _inFlight.contains(userId)) return;
    _inFlight.add(userId);
    try {
      final res =
          await ref.read(apiClientProvider).get<Map<String, dynamic>>('/presence/$userId');
      final next = {...state};
      next[userId] = PresenceState(
        online: res['online'] as bool? ?? false,
        lastActiveAt: res['last_active_at'] == null
            ? null
            : DateTime.tryParse(res['last_active_at'] as String),
        minutesAgo: (res['minutes_ago'] as num?)?.toInt(),
        fetchedAt: DateTime.now(),
      );
      state = next;
    } on AppException {
      // offline service: header falls back to "offline"
    } finally {
      _inFlight.remove(userId);
    }
  }

  /// Announce ourselves. The socket emit is the fast path; the REST call is the
  /// one that survives a dead socket, and it is what makes "Active now" true
  /// for a user whose realtime layer is still reconnecting.
  void heartbeat(String userId) {
    final ws = ref.read(websocketClientProvider);
    ws.emit('presence:heartbeat',
        {'user_id': userId, 'at': DateTime.now().toIso8601String()});
    ref
        .read(apiClientProvider)
        .post<Map<String, dynamic>>('/presence/heartbeat')
        .catchError((Object _) => <String, dynamic>{});
  }
}

final presenceProvider =
    NotifierProvider<PresenceController, Map<String, PresenceState>>(
        PresenceController.new);

/// Peer typing state for one match, read from the session-scoped bridge (which
/// owns the single `chat:typing` subscription and its expiry). A provider that
/// held its own listener lost typing the moment it was disposed — and its 6s
/// expiry raced the server's 4s heartbeats during a long companion generation.
class ChatTypingController extends AutoDisposeFamilyNotifier<bool, String> {
  @override
  bool build(String matchId) {
    final bridge = ref.read(realtimeBridgeProvider);
    final sub = bridge.typingChanges.where((id) => id == matchId).listen((_) {
      state = bridge.typingFor(matchId);
    });
    ref.onDispose(sub.cancel);
    return bridge.typingFor(matchId);
  }
}

final chatTypingProvider = NotifierProvider.autoDispose.family<
    ChatTypingController, bool, String>(ChatTypingController.new);
