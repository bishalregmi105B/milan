import 'package:flutter/material.dart';

import '../../app/theme/color_tokens.dart';

/// The signature presence dot (doc 8 §B): a small living indicator carrying a
/// real presence state — online, recently active, or asleep — used on avatars
/// in the inbox, chat header and profile. Nothing else in the category shows
/// a companion's (or a human's) day this way.
enum PresenceLevel { online, recent, away }

PresenceLevel presenceLevelFrom({required bool online, int? minutesAgo}) {
  if (online) return PresenceLevel.online;
  if (minutesAgo != null && minutesAgo <= 60) return PresenceLevel.recent;
  return PresenceLevel.away;
}

String presenceLabel({required bool online, int? minutesAgo}) {
  if (online) return 'Active now';
  if (minutesAgo == null) return 'Offline';
  if (minutesAgo < 60) return 'Active ${minutesAgo}m ago';
  if (minutesAgo < 60 * 24) return 'Active ${minutesAgo ~/ 60}h ago';
  return 'Active ${minutesAgo ~/ (60 * 24)}d ago';
}

class PresenceDot extends StatelessWidget {
  const PresenceDot({super.key, required this.level, this.size = 12});
  final PresenceLevel level;
  final double size;

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    final color = switch (level) {
      PresenceLevel.online => const Color(0xFF31C48D), // status.online
      PresenceLevel.recent => const Color(0xFFF5A623), // status.away
      PresenceLevel.away => const Color(0xFF8A919C), // status.asleep
    };
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: milan.paper0, width: 2),
      ),
    );
  }
}
