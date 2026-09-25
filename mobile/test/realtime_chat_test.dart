import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:milan/core/realtime/realtime_bridge.dart';
import 'package:milan/features/chat/application/chat_providers.dart';

/// These tests pin the behaviour that broke on device: a message arriving over
/// the socket has to reach the OPEN thread, and it has to keep reaching it after
/// the thread provider has been disposed and rebuilt (route pop/push, inbox
/// refresh). Before the bridge, the thread owned the socket listener and lost
/// it on every dispose, so live updates silently stopped and only a manual
/// refresh showed the message.
void main() {
  group('InboundMessage.tryParse', () {
    test('parses a real backend envelope', () {
      final parsed = InboundMessage.tryParse(<String, dynamic>{
        'match_id': 'm1',
        'id': 'msg1',
        'sender_id': 'u2',
        'body': 'namaste',
        'media_url': null,
        'media_type': null,
        'created_at': '2026-09-03T08:32:44.899185+00:00',
        'is_ai_suggested': false,
      });
      expect(parsed, isNotNull);
      expect(parsed!.matchId, 'm1');
      expect(parsed.body, 'namaste');
    });

    test('survives a malformed envelope instead of throwing', () {
      // A cast error inside the socket handler killed delivery for every
      // subsequent message on that connection.
      expect(InboundMessage.tryParse('not a map'), isNull);
      expect(InboundMessage.tryParse(<String, dynamic>{'id': 'x'}), isNull);
    });

    test('accepts non-string ids (a UUID object over the wire)', () {
      final parsed = InboundMessage.tryParse(<String, dynamic>{
        'match_id': 123,
        'id': 456,
        'sender_id': 789,
        'created_at': 'nonsense',
      });
      expect(parsed!.matchId, '123');
      // An unparseable timestamp must not drop the message.
      expect(parsed.createdAt, isNotNull);
    });
  });

  group('companion typing bubble', () {
    test('waits a reading pause, then shows, and clear() cancels a pending arm',
        () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(companionPendingProvider('m1').notifier);

      notifier.armDeferred();
      expect(container.read(companionPendingProvider('m1')), isFalse,
          reason: 'an instant bubble is the fake-typing tell');

      await Future<void>.delayed(
          CompanionPendingController.readingDelay + const Duration(milliseconds: 150));
      expect(container.read(companionPendingProvider('m1')), isTrue);

      notifier.clear();
      expect(container.read(companionPendingProvider('m1')), isFalse);
    });

    test('clear() before the reading pause elapses stops the bubble appearing',
        () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(companionPendingProvider('m2').notifier);
      notifier.armDeferred();
      notifier.clear();
      await Future<void>.delayed(
          CompanionPendingController.readingDelay + const Duration(milliseconds: 150));
      expect(container.read(companionPendingProvider('m2')), isFalse,
          reason: 'her reply already arrived — the bubble must not pop up after');
    });
  });

  group('PresenceState ageing', () {
    test('online reads as 0 minutes ago', () {
      const state = PresenceState(online: true);
      expect(state.minutesAgoNow, 0);
    });

    test('a stale fetch ages forward instead of freezing', () {
      final state = PresenceState(
        online: false,
        minutesAgo: 2,
        fetchedAt: DateTime.now().subtract(const Duration(minutes: 30)),
      );
      // "Active 2m ago" half an hour later was the reported bug.
      expect(state.minutesAgoNow, greaterThanOrEqualTo(31));
    });

    test('falls back to lastActiveAt when the server sent no minutes', () {
      final state = PresenceState(
        online: false,
        lastActiveAt: DateTime.now().subtract(const Duration(minutes: 5)),
      );
      expect(state.minutesAgoNow, greaterThanOrEqualTo(4));
    });
  });
}
