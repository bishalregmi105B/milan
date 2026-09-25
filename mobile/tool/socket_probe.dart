// Dart-side socket probe: connects to PRODUCTION with the EXACT client config
// the app uses, so it exercises the same library and transport path the phone
// takes. The python diagnostic proved the server broadcasts; this proves the
// Dart/Flutter client receives — that gap is where the "messages only appear
// after refresh" bug actually lived.
//
//   dart run tool/socket_probe.dart <TOKEN_A> <TOKEN_B> <HUMAN_MATCH> <AI_MATCH> <USER_A>
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:socket_io_client/socket_io_client.dart' as io;

const base = 'https://milanapi.pukarphulara.com.np';

var failures = 0;

void say(String step, bool ok, [String detail = '']) {
  if (!ok) failures++;
  stdout.writeln('[${ok ? "PASS" : "FAIL"}] $step${detail.isEmpty ? '' : ' — $detail'}');
}

Future<(int, Map<String, dynamic>)> call(
    String token, String method, String path, [Map<String, Object?>? body]) async {
  final client = HttpClient();
  try {
    final uri = Uri.parse('$base/api/v1$path');
    final req = method == 'GET'
        ? await client.getUrl(uri)
        : await client.postUrl(uri);
    req.headers.set('Authorization', 'Bearer $token');
    if (body != null) {
      req.headers.contentType = ContentType.json;
      req.write(jsonEncode(body));
    }
    final res = await req.close();
    final text = await res.transform(utf8.decoder).join();
    Map<String, dynamic> json;
    try {
      json = jsonDecode(text) as Map<String, dynamic>;
    } catch (_) {
      json = {'raw': text};
    }
    return (res.statusCode, json);
  } finally {
    client.close();
  }
}

Future<void> main(List<String> args) async {
  final tokenA = args[0];
  final tokenB = args[1];
  final humanMatch = args[2];
  final aiMatch = args[3];
  final userA = args[4];

  // Exactly what lib/core/network/websocket_client.dart builds on native.
  final transports =
      (Platform.environment['PROBE_TRANSPORTS'] ?? 'websocket').split(',');
  stdout.writeln('=== transports=$transports ===');
  final socket = io.io(
    base,
    io.OptionBuilder()
        .setTransports(transports)
        .setAuth({'token': tokenA})
        .setReconnectionAttempts(1 << 30)
        .setReconnectionDelay(800)
        .setReconnectionDelayMax(6000)
        .enableReconnection()
        .enableForceNew()
        .build(),
  );

  final connected = Completer<bool>();
  socket.onConnect((_) {
    if (!connected.isCompleted) connected.complete(true);
  });
  socket.onConnectError((e) {
    stdout.writeln('    connect_error: $e');
    if (!connected.isCompleted) connected.complete(false);
  });
  socket.onDisconnect((r) => stdout.writeln('    disconnected: $r'));

  final messages = <Map>[];
  final typings = <(double, Map)>[];
  final presence = <Map>[];
  final t0 = DateTime.now();
  double since() => DateTime.now().difference(t0).inMilliseconds / 1000.0;

  socket.on('chat:message', (dynamic payload) {
    if (payload is Map) messages.add(payload);
  });
  socket.on('chat:typing', (dynamic payload) {
    if (payload is Map) typings.add((since(), payload));
  });
  socket.on('presence:update', (dynamic payload) {
    if (payload is Map) presence.add(payload);
  });

  final ok = await connected.future
      .timeout(const Duration(seconds: 20), onTimeout: () => false);
  say('dart socket connect', ok);
  if (!ok) exit(1);

  Future<dynamic> join(String matchId) {
    final c = Completer<dynamic>();
    socket.emitWithAck('chat:join', {'match_id': matchId, 'token': tokenA},
        ack: (dynamic res) {
      if (!c.isCompleted) c.complete(res);
    });
    return c.future.timeout(const Duration(seconds: 10), onTimeout: () => null);
  }

  final ackHuman = await join(humanMatch);
  say('chat:join human match', ackHuman is Map && ackHuman['ok'] == true, '$ackHuman');

  // B sends over REST -> A must receive it over the socket, in the shape the
  // app's InboundMessage parser expects.
  messages.clear();
  final body = 'dart probe ${DateTime.now().millisecondsSinceEpoch}';
  final (sendStatus, _) =
      await call(tokenB, 'POST', '/matches/$humanMatch/messages', {'body': body});
  say('REST send from B', sendStatus == 201, 'HTTP $sendStatus');
  var deadline = DateTime.now().add(const Duration(seconds: 12));
  while (DateTime.now().isBefore(deadline) &&
      !messages.any((m) => m['body'] == body)) {
    await Future<void>.delayed(const Duration(milliseconds: 300));
  }
  final delivered = messages.firstWhere((m) => m['body'] == body,
      orElse: () => const <String, dynamic>{});
  say('dart client receives B→A', delivered.isNotEmpty,
      'got=${messages.map((m) => m['body']).toList()}');
  // Envelope contract: the app keys off these three fields.
  say('envelope carries match_id/id/sender_id',
      delivered['match_id'] != null &&
          delivered['id'] != null &&
          delivered['sender_id'] != null,
      'keys=${delivered.keys.toList()}');

  // Presence heartbeat over REST — the fallback that keeps "Active now" true
  // while a socket is reconnecting.
  presence.clear();
  final (beatStatus, beatBody) = await call(tokenA, 'POST', '/presence/heartbeat');
  say('REST presence heartbeat', beatStatus == 200 && beatBody['online'] == true,
      'HTTP $beatStatus $beatBody');
  final (presenceStatus, presenceBody) =
      await call(tokenB, 'GET', '/presence/$userA');
  say('peer reads A as online', presenceStatus == 200 && presenceBody['online'] == true,
      'HTTP $presenceStatus online=${presenceBody['online']} minutes_ago=${presenceBody['minutes_ago']}');

  // Companion path: typing must precede the reply, and the reply must land.
  final ackAi = await join(aiMatch);
  say('chat:join companion match', ackAi is Map && ackAi['ok'] == true, '$ackAi');

  messages.clear();
  typings.clear();
  final tSend = since();
  final (aiStatus, aiBody) =
      await call(tokenA, 'POST', '/matches/$aiMatch/messages', {'body': 'probe: aaja k garyo?'});
  say('companion REST send', aiStatus == 201 && aiBody['companion_pending'] == true,
      'HTTP $aiStatus pending=${aiBody['companion_pending']}');
  deadline = DateTime.now().add(const Duration(seconds: 90));
  while (DateTime.now().isBefore(deadline) &&
      !messages.any((m) => '${m['sender_id']}' != userA)) {
    await Future<void>.delayed(const Duration(milliseconds: 400));
  }
  final firstTyping = typings.isEmpty ? null : typings.first.$1 - tSend;
  final reply = messages.where((m) => '${m['sender_id']}' != userA).toList();
  say('companion typing over dart socket', firstTyping != null,
      firstTyping == null ? 'never' : '+${firstTyping.toStringAsFixed(1)}s');
  say('companion reply over dart socket', reply.isNotEmpty,
      reply.isEmpty ? 'never' : 'body=${reply.first['body']}');
  if (firstTyping != null && reply.isNotEmpty) {
    final replyAt = messages.isEmpty ? 0.0 : since() - tSend;
    say('typing precedes reply', firstTyping < replyAt,
        'typing +${firstTyping.toStringAsFixed(1)}s vs reply +${replyAt.toStringAsFixed(1)}s');
  }
  // Heartbeats must keep coming through a long generation, or the client's
  // expiry drops the bubble mid-wait.
  say('typing heartbeats during generation', typings.length >= 3,
      '${typings.length} events: '
      '${typings.map((t) => t.$1.toStringAsFixed(1)).toList()}');

  socket.dispose();
  stdout.writeln(failures == 0 ? '=== ALL PASS ===' : '=== $failures FAILURE(S) ===');
  exit(failures == 0 ? 0 : 1);
}
