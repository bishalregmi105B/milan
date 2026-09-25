import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/accent_theme.dart';
import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../shared/widgets/presence_dot.dart';
import '../../application/chat_providers.dart';

/// Screen 28 — matches inbox, Messenger-style: white surface, search bar,
/// avatar rows with name + last-message preview + unread count pill. AI
/// companions render identically to humans with the single AI badge (§14).
class MatchesInboxScreen extends ConsumerStatefulWidget {
  const MatchesInboxScreen({super.key});

  @override
  ConsumerState<MatchesInboxScreen> createState() => _MatchesInboxScreenState();
}

class _MatchesInboxScreenState extends ConsumerState<MatchesInboxScreen> {

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final accent = ref.watch(accentThemeProvider).accent;
    final matches = ref.watch(matchesProvider);
    final presence = ref.watch(presenceProvider);

    // The rows render presence dots, so somebody has to ask for presence —
    // nobody did, and every human row sat on the default "away" grey.
    final rows = matches.valueOrNull;
    if (rows != null) {
      Future.microtask(() {
        if (!mounted) return;
        final notifier = ref.read(presenceProvider.notifier);
        for (final m in rows) {
          if (!m.isAi && m.otherUserId.isNotEmpty) notifier.ensure(m.otherUserId);
        }
      });
    }

    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        surfaceTintColor: Colors.white,
        title: Text('Chats', style: context.h2),
        actions: [
          IconButton(
            tooltip: 'AI companions',
            icon: Icon(Icons.auto_awesome, color: accent),
            onPressed: () => context.push('/saathi/intro'),
          ),
        ],
      ),
      body: Column(children: [
        Padding(
          padding: EdgeInsets.fromLTRB(Spacing.lg, Spacing.sm, Spacing.lg, Spacing.sm),
          child: TextField(
            // tap-through to the dedicated people search (doc 8 §A4.9):
            // Messenger's inbox search finds new people, not just threads.
            readOnly: true,
            onTap: () => context.push('/discover/search'),
            decoration: InputDecoration(
              hintText: 'Search',
              prefixIcon: const Icon(Icons.search, color: Color(0xFF8A919C)),
              filled: true,
              fillColor: const Color(0xFFF1F3F6),
              contentPadding: EdgeInsets.zero,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(24),
                borderSide: BorderSide.none,
              ),
            ),
          ),
        ),
        Expanded(
          child: matches.when(
            loading: () => _InboxSkeleton(),
            error: (e, _) => Center(
                child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text('Could not load your chats.',
                  style: TextStyle(color: milan.ink600)),
              SizedBox(height: Spacing.md),
              FilledButton(
                  onPressed: () => ref.invalidate(matchesProvider),
                  child: const Text('Retry')),
            ])),
            data: (list) {
              final filtered = list;
              if (filtered.isEmpty) {
                return Center(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.favorite_border, size: 56, color: milan.line200),
                    SizedBox(height: Spacing.lg),
                    Text('Your matches will appear here',
                        style: TextStyle(color: milan.ink600)),
                    SizedBox(height: Spacing.sm),
                    FilledButton(
                        onPressed: () => context.push('/discover'),
                        child: const Text('Find people')),
                  ]),
                );
              }
              return RefreshIndicator(
                onRefresh: () async => ref.invalidate(matchesProvider),
                child: ListView.separated(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) =>
                      Divider(height: 1, color: Colors.grey.shade100),
                  itemBuilder: (context, i) {
                    final match = filtered[i];
                    final preview = match.lastMessage ??
                        (match.lastMessageIsMedia ? 'Sent a photo 📷' : 'Say namaste 👋');
                    return ListTile(                      contentPadding:
                          const EdgeInsets.symmetric(horizontal: Spacing.lg, vertical: 4),
                      leading: Stack(children: [
                        CircleAvatar(
                          radius: 27,
                          backgroundColor: milan.paper100,
                          backgroundImage: match.otherPhotoUrl != null
                              ? CachedNetworkImageProvider(match.otherPhotoUrl!)
                              : null,
                          child: match.otherPhotoUrl == null
                              ? const Icon(Icons.person)
                              : null,
                        ),
                        // signature presence dot (doc 8 §B) — humans only;
                        // companion day-presence lives on the roster screen
                        if (!match.isAi)
                          Positioned(
                            right: 0,
                            bottom: 0,
                            child: PresenceDot(
                              size: 14,
                              level: presenceLevelFrom(
                                  online: presence[match.otherUserId]?.online ?? false,
                                  minutesAgo:
                                      presence[match.otherUserId]?.minutesAgoNow),
                            ),
                          ),
                        if (match.isAi)
                          Positioned(
                            right: 0,
                            bottom: 0,
                            child: Container(
                              padding: const EdgeInsets.all(3),
                              decoration: const BoxDecoration(
                                  color: Colors.white, shape: BoxShape.circle),
                              child: Icon(Icons.smart_toy_outlined,
                                  size: 13, color: milan.dhaka500),
                            ),
                          ),
                      ]),
                      title: Text(match.otherName,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                              fontWeight: FontWeight.w600,
                              color: match.unread ? Colors.black : Colors.black87)),
                      subtitle: Text(
                          match.unread ? '${match.otherName.split(' ').first}: $preview' : preview,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                              fontSize: 13.5,
                              fontWeight: match.unread ? FontWeight.w600 : FontWeight.w400,
                              color: match.unread ? Colors.black87 : const Color(0xFF8A919C))),
                      trailing: match.unread
                          ? Container(
                              // explicit size — an unconstrained alignment
                              // Container balloons inside the trailing slot
                              width: 26,
                              height: 26,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                  color: accent, shape: BoxShape.circle),
                              child: Text(
                                  match.unreadCount > 0 ? '${match.unreadCount}' : '•',
                                  style: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w800,
                                      color: Colors.white)))
                          : null,
                      // Same chat screen for human matches and companions (§14).
                      onTap: () => context.push('/chat/${match.matchId}'),
                    );
                  },
                ),
              );
            },
          ),
        ),
      ]),
    );
  }
}

/// Pulse placeholder shown while the inbox loads (skeleton-loading pattern).
class _InboxSkeleton extends StatefulWidget {
  @override
  State<_InboxSkeleton> createState() => _InboxSkeletonState();
}

class _InboxSkeletonState extends State<_InboxSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 1200))..repeat(reverse: true);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) {
        final opacity = 0.35 + 0.35 * _c.value;
        Widget row() => Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.lg, vertical: 10),
              child: Row(children: [
                Container(width: 54, height: 54,
                    decoration: BoxDecoration(color: Colors.grey.shade200, shape: BoxShape.circle)),
                const SizedBox(width: 14),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Container(height: 13, width: 140, color: Colors.grey.shade200),
                  const SizedBox(height: 8),
                  Container(height: 11, width: 220, color: Colors.grey.shade200),
                ])),
              ]),
            );
        return Opacity(
            opacity: opacity,
            child: Column(children: [for (var i = 0; i < 7; i++) row()]));
      },
    );
  }
}
