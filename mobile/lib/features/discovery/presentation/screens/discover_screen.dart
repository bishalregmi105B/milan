import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/feedback/sfx.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/swipe_card.dart';
import '../../../../shared/widgets/states.dart';
import '../../application/discovery_provider.dart';

/// Screen 19 — Discover swipe deck; default authenticated home.
/// Per-candidate command channel: the action buttons fire the SAME animated
/// fly-out a drag does (§A3.9 — the deck previously snapped with no motion).
final swipeCardControllerProvider = ChangeNotifierProvider.autoDispose
    .family<SwipeCardController, String>((ref, id) => SwipeCardController());

class DiscoverScreen extends ConsumerWidget {
  const DiscoverScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final candidates = ref.watch(discoveryProvider);

    return Scaffold(
      appBar: AppBar(
        titleSpacing: Spacing.lg,
        title: Row(
          children: [
            Text('Milan', style: context.h2),
            SizedBox(width: Spacing.sm),
            Icon(Icons.join_full, size: 18, color: milan.marigold500),
          ],
        ),
        actions: [
          // Dedicated people search (doc 8 §A4.9) — Instagram-style entry.
          IconButton(
            tooltip: 'Search people',
            icon: const Icon(Icons.search),
            onPressed: () => context.push('/discover/search'),
          ),
          // Mode strip so users always know Serious vs Casual (doc 3 §6).
          IconButton(
            tooltip: 'Who liked you',
            icon: const Icon(Icons.favorite_border),
            onPressed: () => context.push('/discover/who-liked-you'),
          ),
          IconButton(
            tooltip: 'Who visited you',
            icon: const Icon(Icons.visibility_outlined),
            onPressed: () => context.push('/discover/who-visited'),
          ),
          Padding(
            padding: EdgeInsets.only(right: Spacing.lg),
            child: ActionChip(
              avatar: Icon(Icons.swap_horiz, size: 16, color: milan.dhaka500),
              label: const Text('Serious'),
              onPressed: () => context.push('/discover/mode'),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.tune),
            onPressed: () => context.push('/discover/filters'),
          ),
        ],
      ),
      body: candidates.when(
        loading: () => const MilanCardSkeleton(),
        error: (e, _) => MilanErrorState(
          onRetry: () => ref.invalidate(discoveryProvider),
        ),
        data: (list) {
          if (list.isEmpty) {
            return _EmptyState(milan: milan);
          }
          final candidate = list.first;
          return Column(
            children: [
              Expanded(
                child: Padding(
                  padding: EdgeInsets.all(Spacing.xl),
                  child: Stack(
                    children: [
                      // Peeking next card (scaled + nudged down) so the deck
                      // reads as a stack, not a single floating card.
                      if (list.length > 1)
                        Positioned.fill(
                          child: Transform.scale(
                            scale: 0.94,
                            alignment: Alignment.topCenter,
                            child: Padding(
                              padding: const EdgeInsets.only(top: 14),
                              child: IgnorePointer(
                                child: SwipeCard(
                                  key: ValueKey('peek-${list[1].id}'),
                                  mediaUrls: list[1].gallery,
                                  name: list[1].name,
                                  age: list[1].age,
                                  distanceKm: list[1].distanceKm,
                                  verified: list[1].verified,
                                ),
                              ),
                            ),
                          ),
                        ),
                      SwipeCard(
                        key: ValueKey(candidate.id),
                        heroTag: 'photo-${candidate.id}',
                        controller: ref.watch(
                          swipeCardControllerProvider(candidate.id),
                        ),
                        mediaUrls: candidate.gallery,
                        name: candidate.name,
                        age: candidate.age,
                        distanceKm: candidate.distanceKm,
                        verified: candidate.verified,
                        onLike: () => _swipe(context, ref, candidate.id, 'like'),
                        onPass: () => _swipe(context, ref, candidate.id, 'pass'),
                        onSuperlike: () =>
                            _swipe(context, ref, candidate.id, 'superlike'),
                        onTapProfile: () =>
                            context.push('/profile/${candidate.id}/public'),
                      ),
                    ],
                  ),
                ),
              ),
              Padding(
                padding: EdgeInsets.only(bottom: Spacing.xxxl),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    _ActionCircle(
                      icon: Icons.replay,
                      color: milan.ink400,
                      onTap: () async {
                        final res = await ref
                            .read(discoveryProvider.notifier)
                            .rewind();
                        if (res['rewound'] != true && context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                            content: Text(res['reason'] == 'rewind_cap'
                                ? 'Rewind is a premium feature.'
                                : 'Nothing to rewind.'),
                          ));
                        }
                      },
                    ),
                    SizedBox(width: Spacing.xl),
                    _ActionCircle(
                      icon: Icons.close,
                      color: milan.ink400,
                      onTap: () => ref
                          .read(
                            swipeCardControllerProvider(candidate.id).notifier,
                          )
                          .pass(),
                    ),
                    SizedBox(width: Spacing.xl),
                    _ActionCircle(
                      icon: Icons.favorite,
                      color: milan.marigold500,
                      onTap: () => ref
                          .read(
                            swipeCardControllerProvider(candidate.id).notifier,
                          )
                          .like(),
                    ),
                    SizedBox(width: Spacing.xl),
                    _ActionCircle(
                      icon: Icons.diamond_outlined,
                      color: milan.dhaka500,
                      onTap: () => ref
                          .read(
                            swipeCardControllerProvider(candidate.id).notifier,
                          )
                          .superlike(),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<bool> _swipe(
    BuildContext context,
    WidgetRef ref,
    String id,
    String direction,
  ) async {
    final sfx = ref.read(sfxProvider.notifier);
    sfx.play(
      direction == 'superlike'
          ? Sfx.superlike
          : direction == 'like'
          ? Sfx.swipeLike
          : Sfx.swipeLight,
    );
    try {
      final result = await ref
          .read(discoveryProvider.notifier)
          .swipe(id, direction);
      if (!context.mounted) return false;
      if (result != null &&
          result['match'] == true &&
          result['match_id'] is String) {
        sfx.play(Sfx.match);
        // Celebration moment rides the detail route (screens 22-23).
        context.push('/discover/match/${result['match_id']}?celebration=true');
      }
      if (result != null && result['error'] == 'daily_like_cap') {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              result['message'] as String? ?? "You've used today's likes.",
            ),
          ),
        );
        return false;
      }
      return true;
    } on AppException catch (e) {
      if (!context.mounted) return false;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.displayMessage)));
      return false;
    } catch (_) {
      if (!context.mounted) return false;
      // never silently swallow intent — tell the user the swipe didn't land
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("That swipe didn't send — check your connection."),
        ),
      );
      return false;
    }
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.milan});
  final MilanColors milan;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(Spacing.xxl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.join_inner_outlined, size: 64, color: milan.line200),
            SizedBox(height: Spacing.xl),
            Text("That's everyone for today", style: context.h3),
            SizedBox(height: Spacing.md),
            Text(
              'Quality over quantity — check back tomorrow for fresh matches.',
              textAlign: TextAlign.center,
              style: TextStyle(color: milan.ink600),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionCircle extends StatelessWidget {
  const _ActionCircle({required this.icon, required this.color, this.onTap});
  final IconData icon;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(Spacing.pill),
      onTap: onTap,
      child: CircleAvatar(
        radius: 30,
        backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
        child: Icon(icon, color: color, size: 26),
      ),
    );
  }
}
