import 'dart:async';
import 'dart:developer';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:socket_io_client/socket_io_client.dart' as io;

import 'api_client.dart';

/// Real-time layer matching the Flask-SocketIO backend (doc 4 §4):
/// chat rooms per match, presence room per user, audio-room signaling.
///
/// TRANSPORT — read before changing:
/// socket_io_client picks its transport factory by conditional import. On
/// native (dart.library.io → `io_transports.dart`) `Transports.newInstance`
/// ALWAYS returns a WebSocketTransport regardless of the requested name, so
/// listing 'polling' first makes the client open a websocket against the
/// `?transport=polling` URL, which nginx answers with "Invalid websocket
/// upgrade" (HTTP 400). The connection then dies before any retry: on Android
/// that is a total realtime blackout, which is exactly why live messages never
/// arrived on device while the server tested clean. Native = websocket only;
/// web keeps the polling→upgrade ladder because there the factory is real.
class WebSocketClient {
  WebSocketClient(this.baseUrl);

  final String baseUrl;
  String _token = '';
  io.Socket? _socket;
  bool _wantConnected = false;
  final Map<String, List<void Function(dynamic)>> _listeners = {};
  final Set<String> _joinedMatches = {};
  final Set<String> _confirmedRooms = {};
  Timer? _watchdog;
  int _connectErrors = 0;

  /// Fired when the socket cannot authenticate (expired token) so the session
  /// layer can refresh and hand us a new one instead of retrying forever.
  void Function()? onAuthFailure;

  /// Diagnostics surfaced in Settings → About (a user can tell us what the
  /// realtime layer is doing without a debug build).
  String status = 'idle';

  bool get isConnected => _socket != null && _socket!.connected;

  /// Rooms whose `chat:join` the server acked. A thread that is joined but not
  /// confirmed will not receive broadcasts, so the bridge re-joins it.
  bool isJoined(String matchId) => _confirmedRooms.contains(matchId);

  /// Access token used for chat:join verification; reconnects with the fresh
  /// token after a refresh (P0-2).
  set authToken(String value) {
    if (_token == value) return;
    _token = value;
    if (_wantConnected) reconnect();
  }

  void connect() {
    if (_token.isEmpty) return; // never open an unauthenticated socket
    _wantConnected = true;
    _open();
  }

  /// Best-effort (re)connect used on app resume and before joining a thread:
  /// no-op when signed out or already connected. If a socket object exists but
  /// is not connected, nudge socket.io to reconnect rather than leaving a dead
  /// handle in place (the old version returned early and stayed offline).
  void ensureConnected() {
    if (!_wantConnected || _token.isEmpty) return;
    if (isConnected) return;
    final socket = _socket;
    if (socket == null) {
      _open();
    } else {
      socket.connect();
    }
  }

  /// Re-opens the socket with the current token (after token refresh).
  void reconnect() {
    _teardown();
    _open();
  }

  void _teardown() {
    _watchdog?.cancel();
    _watchdog = null;
    _confirmedRooms.clear();
    final socket = _socket;
    _socket = null;
    if (socket == null) return;
    // Detach our handlers first: dispose() fires onDisconnect, and a handler
    // that reconnects would resurrect the socket we are discarding.
    for (final entry in _listeners.entries) {
      for (final handler in entry.value) {
        socket.off(entry.key, handler);
      }
    }
    socket.dispose();
  }

  void _open() {
    if (_socket != null || _token.isEmpty) return;
    status = 'connecting';
    _socket = io.io(
      baseUrl,
      io.OptionBuilder()
          // See the class doc: native has no polling transport.
          .setTransports(kIsWeb ? ['polling', 'websocket'] : ['websocket'])
          // Handshake auth only — never the query string: a token in the URL
          // is written to nginx and CDN access logs.
          .setAuth({'token': _token})
          .setReconnectionAttempts(1 << 30)
          .setReconnectionDelay(800)
          .setReconnectionDelayMax(6000)
          .enableReconnection()
          .enableForceNew()
          .build(),
    );
    _socket!.onConnect((_) {
      _connectErrors = 0;
      status = 'connected';
      log('milan ws connected');
      _rejoinRooms();
    });
    _socket!.onReconnect((_) {
      status = 'connected';
      log('milan ws reconnected — rejoining ${_joinedMatches.length} room(s)');
      _rejoinRooms();
    });
    _socket!.onConnectError((e) {
      _connectErrors++;
      status = 'connect error: $e';
      log('milan ws connect error ($_connectErrors): $e');
      // A rejected handshake is almost always an expired JWT — the server
      // returns False from on_connect. Ask the session layer for a fresh
      // token instead of hammering a doomed reconnect loop.
      if (_connectErrors == 3) onAuthFailure?.call();
    });
    _socket!.onDisconnect((reason) {
      status = 'disconnected: $reason';
      _confirmedRooms.clear();
      log('milan ws disconnected: $reason');
    });
    for (final entry in _listeners.entries) {
      for (final handler in entry.value) {
        _socket!.on(entry.key, handler);
      }
    }
    _startWatchdog();
  }

  /// Every 20s: if we want to be online but aren't, or we are online with an
  /// unconfirmed room, repair it. socket.io's own reconnect covers clean drops;
  /// this covers the ugly ones (radio switch, doze, proxy idle-kill) and the
  /// case where a join ack never came back.
  void _startWatchdog() {
    _watchdog?.cancel();
    _watchdog = Timer.periodic(const Duration(seconds: 20), (_) {
      if (!_wantConnected) return;
      if (!isConnected) {
        ensureConnected();
        return;
      }
      if (_joinedMatches.length != _confirmedRooms.length) _rejoinRooms();
    });
  }

  void _rejoinRooms() {
    for (final matchId in _joinedMatches) {
      _emitJoin(matchId);
    }
  }

  void _emitJoin(String matchId) {
    final socket = _socket;
    if (socket == null) return;
    socket.emitWithAck('chat:join', {'match_id': matchId, 'token': _token},
        ack: (dynamic res) {
      final ok = res is Map && res['ok'] == true;
      if (ok) {
        _confirmedRooms.add(matchId);
      } else {
        _confirmedRooms.remove(matchId);
      }
      log('chat:join ${ok ? 'ok' : 'DENIED'} match=$matchId res=$res');
    });
  }

  /// Registers an additional handler for [event]; handlers stack (chat thread
  /// and inbox both listen to `chat:message`) instead of overwriting.
  void on(String event, void Function(dynamic) handler) {
    _listeners.putIfAbsent(event, () => []).add(handler);
    _socket?.on(event, handler);
  }

  void off(String event, void Function(dynamic) handler) {
    _listeners[event]?.remove(handler);
    _socket?.off(event, handler);
  }

  void emit(String event, Object payload) {
    _socket?.emit(event, payload);
  }

  /// Idempotent: remembers the room, connects if needed, and acks the join.
  /// Safe to call on every thread build.
  void joinMatchRoom(String matchId) {
    _joinedMatches.add(matchId);
    ensureConnected();
    if (isConnected) {
      _emitJoin(matchId);
    }
    // Not connected yet: onConnect/_rejoinRooms will emit the acked join.
  }

  void joinAudioRoom(String roomId) => emit('audio_room:join', {'room_id': roomId});

  void raiseHand(String roomId, String userId) =>
      emit('audio_room:raise_hand', {'room_id': roomId, 'user_id': userId});

  void typingStart(String matchId, String userId) =>
      emit('chat:typing_start', {'match_id': matchId, 'user_id': userId});

  void typingStop(String matchId, String userId) =>
      emit('chat:typing_stop', {'match_id': matchId, 'user_id': userId});

  void disconnect() {
    _wantConnected = false;
    status = 'idle';
    _teardown();
  }

  /// Drops session-scoped state (rooms + token) on sign-out.
  void clearSession() {
    _joinedMatches.clear();
    _confirmedRooms.clear();
    _token = '';
  }
}

final websocketClientProvider = Provider<WebSocketClient>((ref) {
  final client = WebSocketClient(
    const String.fromEnvironment(
      'MILAN_WS_URL',
      defaultValue: 'https://milanapi.pukarphulara.com.np',
    ),
  );
  final api = ref.watch(apiClientProvider);
  // Keep the socket auth in sync with token refreshes; drop everything on a
  // failed refresh (signed out) — see ApiClient hooks (P0-1/P0-2).
  api.onTokenRefreshed((token) => client.authToken = token);
  api.onSessionExpired(() {
    client.clearSession();
    client.disconnect();
  });
  // Repeated handshake rejections mean the access token expired while the app
  // sat in the background; a cheap authenticated GET drives ApiClient's
  // refresh interceptor, which hands the new token back through the hook above.
  client.onAuthFailure = () => api.get<Map<String, dynamic>>('/profile/me')
      .catchError((Object _) => <String, dynamic>{});
  ref.onDispose(client.disconnect);
  return client;
});
