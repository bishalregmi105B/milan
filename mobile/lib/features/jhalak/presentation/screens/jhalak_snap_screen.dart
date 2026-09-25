import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../core/network/api_client.dart';
import '../../application/jhalak_snap_provider.dart';

/// Jhalak v2.2 (§Instagram-instant redesign): stories-first layout — a
/// horizontal "My Snap" + friends tray up top (seen rings go grey), then a
/// recents grid of the same snaps below. Viewer: dark stage, squircle media,
/// segmented progress bar, handle chip beneath, emoji quick-reactions.
class JhalakSnapScreen extends ConsumerWidget {
  const JhalakSnapScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = context.milan;
    final feed = ref.watch(jhalakSnapProvider);

    return Scaffold(
      backgroundColor: milan.paper0,
      body: SafeArea(
        child: feed.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => Center(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Text('Could not load Jhalaks.',
                  style: TextStyle(color: milan.ink600)),
              SizedBox(height: Spacing.md),
              FilledButton(
                  onPressed: () => ref.invalidate(jhalakSnapProvider),
                  child: const Text('Retry')),
            ]),
          ),
          data: (tiles) => RefreshIndicator(
            onRefresh: () async => ref.invalidate(jhalakSnapProvider),
            child: CustomScrollView(slivers: [
              // header
              SliverToBoxAdapter(
                child: Padding(
                  padding: EdgeInsets.fromLTRB(Spacing.lg, Spacing.md, Spacing.lg, Spacing.sm),
                  child: Row(children: [
                    Text('Jhalak', style: context.h2),
                    const Spacer(),
                    IconButton(
                      tooltip: 'My snaps',
                      icon: const Icon(Icons.visibility_outlined),
                      onPressed: () => context.push('/jhalak/mine'),
                    ),
                    _ComposePill(onTap: () => context.push('/jhalak/compose')),
                  ]),
                ),
              ),
              if (tiles.isEmpty)
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: _EmptyState(onCompose: () => context.push('/jhalak/compose')),
                )
              else ...[
                // stories tray: unseen first, seen after (Instagram order)
                SliverToBoxAdapter(
                  child: SizedBox(
                    height: 116,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      padding: EdgeInsets.symmetric(horizontal: Spacing.lg),
                      itemCount: tiles.length,
                      separatorBuilder: (_, __) => const SizedBox(width: 14),
                      itemBuilder: (context, i) {
                        final unseenFirst = [...tiles]
                          ..sort((a, b) {
                            final aScore = (a.mine ? 2 : 0) + (a.viewed ? 1 : 0);
                            final bScore = (b.mine ? 2 : 0) + (b.viewed ? 1 : 0);
                            return aScore.compareTo(bScore);
                          });
                        return _TrayItem(
                            tile: unseenFirst[i],
                            hero: i == 0);
                      },
                    ),
                  ),
                ),
                // recents grid
                SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(Spacing.lg, Spacing.lg, Spacing.lg, Spacing.sm),
                    child: Text('Recent', style: context.h4),
                  ),
                ),
                SliverPadding(
                  padding: EdgeInsets.symmetric(horizontal: Spacing.lg),
                  sliver: SliverGrid(
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 2, crossAxisSpacing: 12,
                        mainAxisSpacing: 12, childAspectRatio: 0.92),
                    delegate: SliverChildBuilderDelegate(
                      (context, i) => _SnapCard(tile: tiles[i]),
                      childCount: tiles.length,
                    ),
                  ),
                ),
                const SliverToBoxAdapter(child: SizedBox(height: 32)),
              ],
            ]),
          ),
        ),
      ),
    );
  }
}

class _ComposePill extends StatelessWidget {
  const _ComposePill({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return FilledButton.tonalIcon(
      onPressed: onTap,
      icon: const Icon(Icons.add_a_photo_outlined, size: 18),
      label: const Text('New'),
      style: FilledButton.styleFrom(
          visualDensity: VisualDensity.compact,
          padding: const EdgeInsets.symmetric(horizontal: 14)),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onCompose});
  final VoidCallback onCompose;

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.flash_on_rounded, size: 56, color: milan.line200),
        SizedBox(height: Spacing.lg),
        Text('No Jhalaks from your matches yet',
            textAlign: TextAlign.center, style: TextStyle(color: milan.ink600)),
        SizedBox(height: Spacing.sm),
        Text('Share a 24h snap — each friend sees it once.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: milan.ink400)),
        SizedBox(height: Spacing.lg),
        FilledButton.icon(
            onPressed: onCompose,
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('Snap one')),
      ]),
    );
  }
}

class _TrayItem extends ConsumerWidget {
  const _TrayItem({required this.tile, required this.hero});
  final SnapTile tile;
  final bool hero;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = context.milan;
    final mine = tile.mine;
    final unseen = !tile.viewed;
    final ring = mine
        ? milan.marigold500
        : (unseen ? milan.dhaka500 : milan.line200);
    return GestureDetector(
      onTap: () => _openViewer(context, ref),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Container(
          padding: const EdgeInsets.all(3),
          decoration:
              BoxDecoration(shape: BoxShape.circle, border: Border.all(color: ring, width: 2.6)),
          child: CircleAvatar(
            radius: 30,
            backgroundColor: milan.paper100,
            backgroundImage: tile.authorPhotoUrl != null
                ? CachedNetworkImageProvider(tile.authorPhotoUrl!)
                : null,
            child: tile.authorPhotoUrl == null
                ? Icon(mine ? Icons.add_a_photo : Icons.person,
                    size: 22, color: milan.ink400)
                : null,
          ),
        ),
        const SizedBox(height: 6),
        SizedBox(
          width: 64,
          child: Text(
            mine ? 'My snap' : tile.authorName.split(' ').first,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: TextStyle(
                fontSize: 11.5,
                fontWeight: unseen ? FontWeight.w700 : FontWeight.w500,
                color: milan.ink900),
          ),
        ),
      ]),
    );
  }

  Future<void> _openViewer(BuildContext context, WidgetRef ref) async {
    SnappedMedia media;
    try {
      media = await ref.read(jhalakSnapProvider.notifier).viewOnce(tile);
    } on AppException catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.displayMessage)));
      return;
    }
    if (media.mediaUrl.isEmpty || !context.mounted) return;
    Navigator.of(context).push(MaterialPageRoute<void>(
        fullscreenDialog: true,
        builder: (_) => _SnapViewer(tile: tile, media: media)));
  }
}

class _SnapCard extends ConsumerWidget {
  const _SnapCard({required this.tile});
  final SnapTile tile;

  String _ago(DateTime? posted) {
    if (posted == null) return '';
    final d = DateTime.now().difference(posted);
    if (d.inMinutes < 60) return '${d.inMinutes.clamp(1, 59)}m';
    if (d.inHours < 24) return '${d.inHours}h';
    return '';
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = context.milan;
    final mine = tile.mine;
    final unseen = !tile.viewed;
    final ring = mine
        ? milan.marigold500
        : (unseen ? milan.dhaka500 : milan.line200);

    return InkWell(
      borderRadius: BorderRadius.circular(Spacing.radiusLg),
      onTap: () => _openViewer(context, ref),
      child: Container(
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(Spacing.radiusLg),
            border: Border.all(color: milan.line200)),
        padding: EdgeInsets.all(Spacing.md),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.all(2.5),
              decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: ring, width: 2.4)),
              child: CircleAvatar(
                radius: 17,
                backgroundColor: milan.paper100,
                backgroundImage: tile.authorPhotoUrl != null
                    ? CachedNetworkImageProvider(tile.authorPhotoUrl!)
                    : null,
                child: tile.authorPhotoUrl == null
                    ? const Icon(Icons.person, size: 16)
                    : null,
              ),
            ),
            const Spacer(),
            if (mine)
              Icon(Icons.my_location, size: 14, color: milan.marigold500)
            else if (unseen)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                    color: milan.dhaka500,
                    borderRadius: BorderRadius.circular(9)),
                child: const Text('NEW',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.w800)),
              )
            else
              Icon(Icons.done_all, size: 14, color: milan.line200),
          ]),
          const Spacer(),
          Text(tile.authorName,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
          const SizedBox(height: 2),
          Text(
            mine
                ? '${tile.viewCount} view${tile.viewCount == 1 ? '' : 's'} · ${_ago(tile.postedAt)}'
                : (unseen
                    ? 'Tap to view · once only'
                    : 'Already viewed · ${_ago(tile.postedAt)}'),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 11.5, color: milan.ink400),
          ),
        ]),
      ),
    );
  }

  Future<void> _openViewer(BuildContext context, WidgetRef ref) async {
    SnappedMedia media;
    try {
      media = await ref.read(jhalakSnapProvider.notifier).viewOnce(tile);
    } on AppException catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.displayMessage)));
      return;
    }
    if (media.mediaUrl.isEmpty || !context.mounted) return;
    Navigator.of(context).push(MaterialPageRoute<void>(
        fullscreenDialog: true,
        builder: (_) => _SnapViewer(tile: tile, media: media)));
  }
}

/// Instagram-instant viewer: dark stage, squircle media, author handle
/// beneath, emoji quick-reactions that land in the shared chat thread.
class _SnapViewer extends ConsumerStatefulWidget {
  const _SnapViewer({required this.tile, required this.media});
  final SnapTile tile;
  final SnappedMedia media;

  @override
  ConsumerState<_SnapViewer> createState() => _SnapViewerState();
}

class _SnapViewerState extends ConsumerState<_SnapViewer>
    with SingleTickerProviderStateMixin {
  static const _reactions = ['👀', '😂', '😮', '❤️'];
  String? _sent;
  bool _reported = false;
  late final AnimationController _drain = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
      value: 1.0); // story bar: 10s to decide, but the snap stays yours

  @override
  void dispose() {
    _drain.dispose();
    super.dispose();
  }

  Future<void> _react(String emoji) async {
    if (_sent != null || widget.tile.mine) return;
    setState(() => _sent = emoji);
    try {
      await ref.read(apiClientProvider).post(
          '/jhalak/snaps/${widget.tile.id}/react',
          body: {'emoji': emoji});
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('$emoji sent to the chat'),
          duration: const Duration(seconds: 2)));
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() => _sent = null);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.displayMessage)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(children: [
          // story-style drain bar — the ephemeral feel (view itself is
          // already burned server-side at open)
          Padding(
            padding: EdgeInsets.symmetric(horizontal: Spacing.lg),
            child: AnimatedBuilder(
                animation: _drain,
                builder: (context, _) => LinearProgressIndicator(
                    value: _drain.value,
                    minHeight: 2.5,
                    backgroundColor: Colors.white24,
                    valueColor: const AlwaysStoppedAnimation(Colors.white))),
          ),
          Padding(
            padding: EdgeInsets.symmetric(
                horizontal: Spacing.lg, vertical: Spacing.sm),
            child: Row(children: [
              IconButton(
                  icon: const Icon(Icons.arrow_back, color: Colors.white),
                  onPressed: () => Navigator.of(context).pop()),
              const Spacer(),
              if (!widget.tile.mine && !_reported)
                IconButton(
                    tooltip: 'I took a screenshot',
                    icon: const Icon(Icons.photo_camera, color: Colors.white70),
                    onPressed: () async {
                      setState(() => _reported = true);
                      await ref
                          .read(jhalakSnapProvider.notifier)
                          .reportScreenshot(widget.tile.id);
                    })
              else if (_reported)
                const Text('Author notified 📸',
                    style: TextStyle(color: Colors.white54, fontSize: 12)),
            ]),
          ),
          Expanded(
            child: Center(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(28),
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                        maxWidth: MediaQuery.sizeOf(context).width * 0.88,
                        maxHeight: MediaQuery.sizeOf(context).height * 0.56),
                    child: CachedNetworkImage(
                      imageUrl: widget.media.mediaUrl,
                      fit: BoxFit.cover,
                      placeholder: (_, __) => Container(
                          width: 220, height: 280, color: Colors.white10),
                      errorWidget: (_, __, ___) => Container(
                          width: 220,
                          height: 280,
                          color: Colors.white10,
                          child: const Icon(Icons.broken_image_outlined,
                              size: 48, color: Colors.white38)),
                    ),
                  ),
                ),
                SizedBox(height: Spacing.md),
                Row(mainAxisSize: MainAxisSize.min, children: [
                  CircleAvatar(
                    radius: 11,
                    backgroundColor: Colors.white12,
                    backgroundImage: widget.tile.authorPhotoUrl != null
                        ? CachedNetworkImageProvider(
                            widget.tile.authorPhotoUrl!)
                        : null,
                    child: widget.tile.authorPhotoUrl == null
                        ? const Icon(Icons.person,
                            size: 11, color: Colors.white54)
                        : null,
                  ),
                  const SizedBox(width: 8),
                  Text('@${widget.tile.authorName}',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700)),
                  const SizedBox(width: 8),
                  Text(_agoLabel(),
                      style: const TextStyle(
                          color: Colors.white54, fontSize: 12)),
                  if (widget.media.caption != null &&
                      widget.media.caption!.isNotEmpty) ...[
                    const SizedBox(width: 10),
                    Flexible(
                        child: Text(widget.media.caption!,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                                color: Colors.white70, fontSize: 13))),
                  ],
                ]),
              ]),
            ),
          ),
          if (!widget.tile.mine)
            Padding(
              padding: EdgeInsets.only(bottom: Spacing.xxl),
              child: _sent != null
                  ? Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 22, vertical: 10),
                      decoration: BoxDecoration(
                          color: Colors.white12,
                          borderRadius: BorderRadius.circular(24)),
                      child: Text('$_sent sent',
                          style: const TextStyle(
                              color: Colors.white, fontSize: 15)))
                  : Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                      for (final emoji in _reactions)
                        GestureDetector(
                          onTap: () => _react(emoji),
                          child: Container(
                            margin: const EdgeInsets.symmetric(horizontal: 9),
                            padding: const EdgeInsets.all(9),
                            decoration: const BoxDecoration(
                                color: Colors.white12, shape: BoxShape.circle),
                            child: Text(emoji,
                                style: const TextStyle(fontSize: 24)),
                          ),
                        ),
                    ]),
            )
          else
            Padding(
              padding: EdgeInsets.only(bottom: Spacing.xxl),
              child: Text('${widget.tile.viewCount} views · live 24h',
                  style: const TextStyle(color: Colors.white54, fontSize: 12.5)),
            ),
        ]),
      ),
    );
  }

  String _agoLabel() {
    final posted = widget.tile.postedAt;
    if (posted == null) return '';
    final d = DateTime.now().difference(posted);
    if (d.inMinutes < 60) return '· ${d.inMinutes.clamp(1, 59)}m';
    if (d.inHours < 24) return '· ${d.inHours}h';
    return '';
  }
}
