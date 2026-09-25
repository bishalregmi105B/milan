import 'dart:async';
import 'dart:developer';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/application/auth_provider.dart';
import '../feedback/sfx.dart';
import '../network/websocket_client.dart';
import '../storage/local_db.dart';

/// One inbound realtime envelope, normalised.
class InboundMessage {
  const InboundMessage({
    required this.matchId,
    required this.id,
    required this.senderId,
    this.body,
    this.mediaUrl,
    this.mediaType,
    this.isAiSuggested = false,
    required this.createdAt,
  });

  final String matchId;
  final String id;
  final String senderId;
  final String? body;
  final String? mediaUrl;
  final String? mediaType;
  final bool isAiSuggested;
  final DateTime createdAt;

  /// Socket payloads arrive as `Map<String, dynamic>`; every field is treated
  /// as optional because a malformed envelope must not kill the subscription
  /// for every other message.
  static InboundMessage? tryParse(dynamic payload) {
    if (payload is! Map) return null;
    final matchId = payload['match_id']?.toString();
    final id = payload['id']?.toString();
    final senderId = payload['sender_id']?.toString();
    if (matchId == null || id == null || senderId == null) return null;
    return InboundMessage(
      matchId: matchId,
      id: id,
      senderId: senderId,
      body: payload['body'] as String?,
      mediaUrl: payload['media_url'] as String?,
      mediaType: payload['media_type'] as String?,
      isAiSuggested: payload['is_ai_suggested'] as bool? ?? false,
      createdAt:
          DateTime.tryParse('${payload['created_at'] ?? ''}') ?? DateTime.now(),
    );
  }

  Map<String, Object?> toCacheRow() => {
        'id': id,
        'match_id': matchId,
        'sender_id': senderId,
        'body': body,
        'media_url': mediaUrl,
        'media_type': mediaType,
        'read_at': null,
        'is_ai_suggested': isAiSuggested ? 1 : 0,
        'created_at': createdAt.toIso8601String(),
      };
}

/// Peer typing for one match, with the timestamp it arrived.
class TypingSignal {
  const TypingSignal({required this.typing, required this.at});
  final bool typing;
  final DateTime at;
}

/// THE single socket subscriber for chat traffic, alive for the whole signed-in
/// session (created by the app root, never auto-disposed).
///
/// Why this exists: the chat thread, the inbox and the typing indicator each
/// registered their own `chat:message` listener inside a provider that Riverpod
/// is free to dispose. When the thread provider was recreated — a rebuild, a
/// route change, an `invalidateSelf` from the inbox — the listener went away
/// with it, so a message that arrived in that window updated nothing and only
/// showed up after a manual refresh. Now the socket has exactly one subscriber
/// whose lifetime is the session; screens listen to [messages], which they can
/// come and go from freely.
///
/// The bridge also writes every inbound message straight to the sqflite cache,
/// so anything that arrives while a thread is closed is on screen the instant
/// it is opened — no network round-trip needed.
class RealtimeBridge {
  RealtimeBridge(this._ref);

  final Ref _ref;

  final StreamController<InboundMessage> _messages =
      StreamController<InboundMessage>.broadcast();
  final Map<String, TypingSignal> _typing = {};
  final StreamController<String> _typingChanges =
      StreamController<String>.broadcast();
  final Map<String, Timer> _typingExpiry = {};

  /// Latest inbound message per match — lets a screen that attaches late
  /// reconcile without a refetch.
  final Map<String, InboundMessage> lastByMatch = {};

  Stream<InboundMessage> get messages => _messages.stream;

  /// Emits a matchId whenever its typing state changes.
  Stream<String> get typingChanges => _typingChanges.stream;

  bool typingFor(String matchId) => _typing[matchId]?.typing ?? false;

  Stream<InboundMessage> messagesFor(String matchId) =>
      _messages.stream.where((m) => m.matchId == matchId);

  void Function(dynamic)? _onMessage;
  void Function(dynamic)? _onTyping;
  Timer? _inboxDebounce;

  void start() {
    if (_onMessage != null) return;
    final ws = _ref.read(websocketClientProvider);

    _onMessage = (dynamic payload) {
      final message = InboundMessage.tryParse(payload);
      if (message == null) {
        log('milan realtime: unparseable chat:message $payload');
        return;
      }
      lastByMatch[message.matchId] = message;
      // Cache first: this is what makes the message survive a cold open.
      _ref.read(localDbProvider).cacheMessage(message.toCacheRow());
      _messages.add(message);

      final myId = _ref.read(currentUserIdProvider);
      final mine = myId != null && message.senderId == myId;
      if (!mine) {
        _ref.read(sfxProvider.notifier).play(Sfx.messageReceived);
        // Her reply (or his) landing is the definitive end of "typing…".
        _setTyping(message.matchId, false);
      }
      _refreshInboxSoon();
    };

    _onTyping = (dynamic payload) {
      if (payload is! Map) return;
      final matchId = payload['match_id']?.toString();
      if (matchId == null) return;
      final myId = _ref.read(currentUserIdProvider);
      if (myId != null && '${payload['user_id']}' == myId) return; // self-echo
      _setTyping(matchId, payload['typing'] as bool? ?? false);
    };

    ws.on('chat:message', _onMessage!);
    ws.on('chat:typing', _onTyping!);
  }

  void _setTyping(String matchId, bool typing) {
    _typingExpiry.remove(matchId)?.cancel();
    _typing[matchId] = TypingSignal(typing: typing, at: DateTime.now());
    if (typing) {
      // The server heartbeats typing every 4s during a long generation; 10s
      // without one means the sender stopped or the emit was lost. A missed
      // `typing:false` must never leave the bubble up forever.
      _typingExpiry[matchId] = Timer(const Duration(seconds: 10), () {
        _typing[matchId] = TypingSignal(typing: false, at: DateTime.now());
        if (!_typingChanges.isClosed) _typingChanges.add(matchId);
      });
    }
    if (!_typingChanges.isClosed) _typingChanges.add(matchId);
  }

  /// Inbox refresh is coalesced: a companion answering in three segments would
  /// otherwise fire three full `/matches` refetches back to back.
  void _refreshInboxSoon() {
    _inboxDebounce?.cancel();
    _inboxDebounce = Timer(const Duration(milliseconds: 600), () {
      final tick = _ref.read(matchesRefreshTick.notifier);
      tick.state = tick.state + 1;
    });
  }

  void dispose() {
    final ws = _ref.read(websocketClientProvider);
    if (_onMessage != null) ws.off('chat:message', _onMessage!);
    if (_onTyping != null) ws.off('chat:typing', _onTyping!);
    _onMessage = null;
    _onTyping = null;
    _inboxDebounce?.cancel();
    for (final timer in _typingExpiry.values) {
      timer.cancel();
    }
    _typingExpiry.clear();
    _messages.close();
    _typingChanges.close();
  }
}

/// Bumped by the bridge; the inbox watches it so a live message refreshes the
/// list without the inbox itself having to hold a socket listener.
final matchesRefreshTick = StateProvider<int>((ref) => 0);

final realtimeBridgeProvider = Provider<RealtimeBridge>((ref) {
  final bridge = RealtimeBridge(ref);
  // Subscribe on creation: a screen that reads this provider must never be the
  // thing that decides whether the socket is being listened to.
  bridge.start();
  ref.onDispose(bridge.dispose);
  return bridge;
});
