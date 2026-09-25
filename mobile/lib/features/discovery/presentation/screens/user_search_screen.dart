import 'dart:async';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../shared/widgets/chat_bubble.dart';
import '../../../../shared/widgets/presence_dot.dart';
import '../../application/user_search_provider.dart';

/// Dedicated people search (doc 8 §A4.9) — Instagram-style: autofocus field,
/// live debounced results with verification/trust/distance signals, and
/// persisted recent searches. Server does the ranking (§C8).
class UserSearchScreen extends ConsumerStatefulWidget {
  const UserSearchScreen({super.key});

  @override
  ConsumerState<UserSearchScreen> createState() => _UserSearchScreenState();
}

class _UserSearchScreenState extends ConsumerState<UserSearchScreen> {
  final _field = TextEditingController();
  final _focus = FocusNode();
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    // Instagram behaviour: keyboard is up before the first frame settles.
    WidgetsBinding.instance.addPostFrameCallback((_) => _focus.requestFocus());
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _field.dispose();
    _focus.dispose();
    super.dispose();
  }

  void _onChanged(String value) {
    final search = ref.read(userSearchProvider.notifier);
    search.updateQuery(value);
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () => search.search());
  }

  void _runRecent(String q) {
    _field.text = q;
    _field.selection = TextSelection.collapsed(offset: q.length);
    _focus.requestFocus();
    final search = ref.read(userSearchProvider.notifier);
    search.updateQuery(q);
    search.search();
  }

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    final state = ref.watch(userSearchProvider);

    return Scaffold(
      backgroundColor: milan.paper0,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(64),
        child: SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(Spacing.lg, Spacing.xs, Spacing.lg, Spacing.sm),
            child: Row(children: [
              InkWell(
                borderRadius: BorderRadius.circular(20),
                onTap: () => context.pop(),
                child: const Padding(
                  padding: EdgeInsets.all(6),
                  child: Icon(Icons.arrow_back, size: 22),
                ),
              ),
              SizedBox(width: Spacing.md),
              Expanded(child: _SearchField(
                controller: _field,
                focus: _focus,
                onChanged: _onChanged,
                onClear: () {
                  _field.clear();
                  _onChanged('');
                },
                onSubmitted: (_) {
                  _debounce?.cancel();
                  ref.read(userSearchProvider.notifier).search();
                },
              )),
            ]),
          ),
        ),
      ),
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 180),
        child: _buildBody(context, state),
      ),
    );
  }

  Widget _buildBody(BuildContext context, UserSearchState state) {
    if (state.query.trim().isEmpty) {
      if (state.recent.isEmpty) {
        return _MessageState(
          key: const ValueKey('empty-start'),
          icon: Icons.search_rounded,
          title: 'Search Milan',
          body: 'Find people by name, city or interest.',
          hintChips: const ['momo', 'Kathmandu', 'hiking', 'music', 'Pokhara'],
          onChip: _runRecent,
        );
      }
      return _RecentSection(
        key: const ValueKey('recent'),
        recents: state.recent,
        onTap: _runRecent,
        onRemove: (q) => ref.read(userSearchProvider.notifier).removeRecent(q),
        onClearAll: () => ref.read(userSearchProvider.notifier).clearRecent(),
      );
    }
    if (state.loading) {
      return const _SearchSkeleton(key: ValueKey('loading'));
    }
    if (state.error != null) {
      return _MessageState(
        key: const ValueKey('error'),
        icon: Icons.wifi_off_rounded,
        title: 'Search is unreachable',
        body: state.error!,
        actionLabel: 'Try again',
        onAction: () => ref.read(userSearchProvider.notifier).search(),
      );
    }
    if (state.results.isEmpty) {
      return _MessageState(
        key: const ValueKey('empty'),
        icon: Icons.person_search_rounded,
        title: 'No people found',
        body: 'Nothing matches "${state.query.trim()}". Try a name, city or interest.',
      );
    }
    return ListView.builder(
      key: const ValueKey('results'),
      padding: const EdgeInsets.only(bottom: 24),
      itemCount: state.results.length,
      itemBuilder: (context, i) => _ResultRow(hit: state.results[i]),
    );
  }
}

class _SearchField extends StatelessWidget {
  const _SearchField({
    required this.controller,
    required this.focus,
    required this.onChanged,
    required this.onClear,
    required this.onSubmitted,
  });
  final TextEditingController controller;
  final FocusNode focus;
  final ValueChanged<String> onChanged;
  final VoidCallback onClear;
  final ValueChanged<String> onSubmitted;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      focusNode: focus,
      onChanged: onChanged,
      textInputAction: TextInputAction.search,
      onSubmitted: onSubmitted,
      decoration: InputDecoration(
        hintText: 'Search people',
        filled: true,
        fillColor: const Color(0xFFF1F3F6),
        isDense: true,
        prefixIcon: const Icon(Icons.search, color: Color(0xFF8A919C), size: 20),
        suffixIcon: ValueListenableBuilder<TextEditingValue>(
          valueListenable: controller,
          builder: (context, value, _) => value.text.isEmpty
              ? const SizedBox.shrink()
              : InkWell(
                  onTap: onClear,
                  borderRadius: BorderRadius.circular(12),
                  child: const Icon(Icons.close, size: 18, color: Color(0xFF8A919C)),
                ),
        ),
        contentPadding: const EdgeInsets.symmetric(vertical: 10),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(22),
          borderSide: BorderSide.none,
        ),
      ),
    );
  }
}

class _ResultRow extends StatelessWidget {
  const _ResultRow({required this.hit});
  final UserSearchHit hit;

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    final subtitleParts = <String>[
      if (hit.city != null && hit.city!.isNotEmpty) hit.city!,
      if (hit.age != null) '${hit.age}',
      if (hit.distanceKm != null)
        hit.distanceKm! < 1 ? '<1 km' : '${hit.distanceKm!.toStringAsFixed(hit.distanceKm! < 10 ? 1 : 0)} km',
    ];
    return ListTile(
      contentPadding: EdgeInsets.symmetric(horizontal: Spacing.lg, vertical: 2),
      leading: CircleAvatar(
        radius: 26,
        backgroundColor: milan.paper100,
        backgroundImage: hit.photoUrl != null
            ? CachedNetworkImageProvider(hit.photoUrl!)
            : null,
        child: hit.photoUrl == null
            ? const Icon(Icons.person, size: 26)
            : null,
      ),
      title: Row(children: [
        Flexible(
          child: Text(hit.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w600)),
        ),
        if (hit.isVerified) ...[
          const SizedBox(width: 4),
          Icon(Icons.verified, size: 15, color: ChatBubble.defaultAccent),
        ],
        if (hit.isBoosted) ...[
          const SizedBox(width: 3),
          Icon(Icons.bolt, size: 14, color: milan.marigold500),
        ],
      ]),
      subtitle: Text(
        subtitleParts.isEmpty ? 'On Milan' : subtitleParts.join(' · '),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: TextStyle(fontSize: 13, color: milan.ink400),
      ),
      trailing: hit.compatibilityScore != null
          ? Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(
                color: milan.marigold100,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text('${hit.compatibilityScore!.round()}%',
                  style: TextStyle(
                      fontSize: 12, fontWeight: FontWeight.w700, color: milan.ink900)),
            )
          : const PresenceDot(level: PresenceLevel.away, size: 8),
      onTap: () => context.push('/profile/${hit.id}/public'),
    );
  }
}

class _RecentSection extends StatelessWidget {
  const _RecentSection({
    super.key,
    required this.recents,
    required this.onTap,
    required this.onRemove,
    required this.onClearAll,
  });
  final List<String> recents;
  final ValueChanged<String> onTap;
  final ValueChanged<String> onRemove;
  final VoidCallback onClearAll;

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    return ListView(padding: const EdgeInsets.only(top: 4), children: [
      Padding(
        padding: EdgeInsets.symmetric(horizontal: Spacing.lg, vertical: Spacing.sm),
        child: Row(children: [
          Text('Recent', style: context.h4),
          const Spacer(),
          TextButton(onPressed: onClearAll, child: const Text('Clear all')),
        ]),
      ),
      for (final q in recents)
        ListTile(
          contentPadding: EdgeInsets.symmetric(horizontal: Spacing.lg),
          leading: Icon(Icons.history, color: milan.ink400),
          title: Text(q),
          trailing: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => onRemove(q),
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: Icon(Icons.close, size: 16, color: milan.ink400),
            ),
          ),
          onTap: () => onTap(q),
        ),
    ]);
  }
}

class _MessageState extends StatelessWidget {
  const _MessageState({
    super.key,
    required this.icon,
    required this.title,
    required this.body,
    this.actionLabel,
    this.onAction,
    this.hintChips,
    this.onChip,
  });
  final IconData icon;
  final String title;
  final String body;
  final String? actionLabel;
  final VoidCallback? onAction;
  final List<String>? hintChips;
  final ValueChanged<String>? onChip;

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    return Center(
      child: Padding(
        padding: EdgeInsets.all(Spacing.xxl),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 52, color: milan.line200),
          SizedBox(height: Spacing.lg),
          Text(title, style: context.h4, textAlign: TextAlign.center),
          SizedBox(height: Spacing.xs),
          Text(body,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 13.5, color: milan.ink600)),
          if (hintChips != null) ...[
            SizedBox(height: Spacing.lg),
            Wrap(
              spacing: Spacing.sm,
              runSpacing: Spacing.sm,
              alignment: WrapAlignment.center,
              children: [
                for (final chip in hintChips!)
                  ActionChip(label: Text(chip), onPressed: () => onChip?.call(chip)),
              ],
            ),
          ],
          if (actionLabel != null) ...[
            SizedBox(height: Spacing.lg),
            FilledButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ]),
      ),
    );
  }
}

class _SearchSkeleton extends StatefulWidget {
  const _SearchSkeleton({super.key});
  @override
  State<_SearchSkeleton> createState() => _SearchSkeletonState();
}

class _SearchSkeletonState extends State<_SearchSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 1200))
    ..repeat(reverse: true);

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
        return Opacity(
          opacity: opacity,
          child: Column(children: [
            for (var i = 0; i < 8; i++)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: Spacing.lg, vertical: 10),
                child: Row(children: [
                  Container(width: 52, height: 52,
                      decoration: const BoxDecoration(color: Color(0xFFECEFF3), shape: BoxShape.circle)),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Container(height: 13, width: 150, color: const Color(0xFFECEFF3)),
                      const SizedBox(height: 8),
                      Container(height: 11, width: 210, color: const Color(0xFFECEFF3)),
                    ]),
                  ),
                ]),
              ),
          ]),
        );
      },
    );
  }
}
