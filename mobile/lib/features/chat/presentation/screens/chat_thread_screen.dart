import 'dart:async';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/feedback/sfx.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/websocket_client.dart';
import '../../../../core/realtime/realtime_bridge.dart';
import '../../../../shared/widgets/chat_bubble.dart';
import '../../../../shared/widgets/presence_dot.dart';
import '../../../../shared/widgets/theme_picker_sheet.dart';
import '../../../../shared/widgets/voice_note_player.dart';
import '../../../auth/application/auth_provider.dart';
import '../../../saathi/application/saathi_session_provider.dart';
import '../../application/chat_providers.dart';
import '../../../personalization/application/theme_provider.dart';
import '../../../../app/theme/chat_theme_presets.dart';
import '../../../../app/theme/accent_theme.dart';
import '../../../../app/theme/chat_theme_tokens.dart';

/// Screen 29 — 1:1 chat thread, Messenger rebuild (doc 8 Part D.2): presence
/// header with the living indicator, media/GIF/voice bubbles, delivered/read
/// ticks, suggestion chips that fill the composer, human reply timing.
class ChatThreadScreen extends ConsumerStatefulWidget {
  const ChatThreadScreen({super.key, required this.matchId});
  final String matchId;

  @override
  ConsumerState<ChatThreadScreen> createState() => _ChatThreadScreenState();
}

class _ChatThreadScreenState extends ConsumerState<ChatThreadScreen> {
  final _composer = TextEditingController();
  final _scrollController = ScrollController();
  Timer? _typingTimer;
  Timer? _presenceTimer;
  StreamSubscription<InboundMessage>? _inbound;
  bool _typingEmitted = false;
  bool _busySend = false;
  int _lastCount = 0;

  ChatThemeScopeKey get scope => ChatThemeScopeKey.match(widget.matchId);

  @override
  void initState() {
    super.initState();
    // the icebreaker chips write into the same composer
    Future.microtask(() {
      ref.read(composerProvider).add(_composer);
      ref.read(composerProvider).onChanged = () => setState(() {});
    });
    // Messenger behaviour: a thread always opens at the newest message
    WidgetsBinding.instance.addPostFrameCallback((_) => _jumpToBottom());
    // opening the thread clears the inbox dot (server-side read receipt)
    Future.microtask(_markRead);
    // While a thread is open, keep the room join and the peer's presence
    // honest: a socket that dropped in the background is repaired here rather
    // than waiting for the next app resume.
    _presenceTimer = Timer.periodic(const Duration(seconds: 20), (_) {
      if (!mounted) return;
      final ws = ref.read(websocketClientProvider);
      ws.joinMatchRoom(widget.matchId);
      final peerId = _peerId();
      if (peerId != null) ref.read(presenceProvider.notifier).ensure(peerId);
    });
    // A message that lands while you are LOOKING at the thread is read. Without
    // this the inbox kept an unread badge for the chat currently on screen.
    _inbound = ref
        .read(realtimeBridgeProvider)
        .messagesFor(widget.matchId)
        .listen((message) {
          final myId = ref.read(currentUserIdProvider);
          if (message.senderId == myId) return;
          _markRead();
        });
  }

  Future<void> _markRead() async {
    try {
      await ref.read(apiClientProvider).post('/matches/${widget.matchId}/read');
      if (mounted) ref.invalidate(matchesProvider);
    } on AppException {
      // read state is cosmetic; never block the chat on it
    }
  }

  String? _peerId() {
    final matches =
        ref.read(matchesProvider).valueOrNull ?? const <MatchSummary>[];
    for (final m in matches) {
      if (m.matchId == widget.matchId && !m.isAi) return m.otherUserId;
    }
    return null;
  }

  void _jumpToBottom() {
    if (!_scrollController.hasClients) return;
    _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
    _lastCount =
        ref.read(chatThreadProvider(widget.matchId)).valueOrNull?.length ?? 0;
  }

  void _maybeScrollToBottom(int count) {
    if (count <= _lastCount) return;
    _lastCount = count;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
      );
    });
  }

  static bool _sameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  @override
  void dispose() {
    ref.read(composerProvider).remove(_composer);
    _inbound?.cancel();
    _presenceTimer?.cancel();
    _scrollController.dispose();
    _stopTyping();
    _composer.dispose();
    super.dispose();
  }

  /// Debounced chat:typing_start / chat:typing_stop emissions (P0-2); the
  /// backend relays them to the match room as `chat:typing`.
  void _onComposerChanged(String text) {
    final ws = ref.read(websocketClientProvider);
    final myId = ref.read(currentUserIdProvider);
    if (myId == null) return;
    if (text.isEmpty) {
      _stopTyping();
      return;
    }
    if (!_typingEmitted) {
      ws.typingStart(widget.matchId, myId);
      _typingEmitted = true;
    }
    _typingTimer?.cancel();
    _typingTimer = Timer(const Duration(seconds: 2), _stopTyping);
  }

  void _stopTyping() {
    _typingTimer?.cancel();
    _typingTimer = null;
    if (_typingEmitted) {
      final myId = ref.read(currentUserIdProvider);
      if (myId != null) {
        ref.read(websocketClientProvider).typingStop(widget.matchId, myId);
      }
      _typingEmitted = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    final messages = ref.watch(chatThreadProvider(widget.matchId));
    final themeAsync = ref.watch(themeProvider(scope));
    final resolved =
        themeAsync.valueOrNull?.theme ?? ChatWallpaperTheme.factoryDefault;
    final dark = Theme.of(context).brightness == Brightness.dark;
    final myId = ref.watch(currentUserIdProvider);
    final peerTyping = ref.watch(chatTypingProvider(widget.matchId));
    // Her reply generates off the request path — the local pending state
    // keeps the typing bubble up for however long the generation takes.
    final companionPending = ref.watch(
      companionPendingProvider(widget.matchId),
    );
    final showTyping = (peerTyping || companionPending);
    final accent = ref.watch(accentThemeProvider).accent;

    final matches =
        ref.watch(matchesProvider).valueOrNull ?? const <MatchSummary>[];
    MatchSummary? peer;
    for (final m in matches) {
      if (m.matchId == widget.matchId) peer = m;
    }

    // Real presence for the header (doc 8 §A2.8: no presence line existed).
    // Companions keep their simulated-day presence from the roster payload.
    if (peer != null && !peer.isAi) {
      final peerId = peer.otherUserId;
      Future.microtask(
        () => ref.read(presenceProvider.notifier).ensure(peerId),
      );
    }
    final presence = peer == null
        ? null
        : ref.watch(presenceProvider)[peer.otherUserId];

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 0,
        title: Row(
          children: [
            Stack(
              children: [
                CircleAvatar(
                  radius: 18,
                  backgroundImage: peer?.otherPhotoUrl != null
                      ? CachedNetworkImageProvider(peer!.otherPhotoUrl!)
                      : null,
                  child: peer?.otherPhotoUrl == null
                      ? const Icon(Icons.person)
                      : null,
                ),
                if (peer != null && (presence != null || peer.isAi))
                  Positioned(
                    right: 0,
                    bottom: 0,
                    child: PresenceDot(
                      size: 13,
                      level: peer.isAi
                          // companion presence is simulated-day state; the dot
                          // mirrors it until a dedicated level arrives
                          ? PresenceLevel.online
                          : presenceLevelFrom(
                              online: presence?.online ?? false,
                              minutesAgo: presence?.minutesAgoNow,
                            ),
                    ),
                  ),
              ],
            ),
            SizedBox(width: Spacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    peer?.otherName ?? '',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 16,
                    ),
                  ),
                  Text(
                    _presenceLine(peer, presence),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 11.5,
                      color: presence?.online == true
                          ? const Color(0xFF31C48D)
                          : milan.ink400,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: peer?.otherUserId == null || peer!.otherUserId.isEmpty
                ? 'Report unavailable'
                : 'Report',
            icon: const Icon(Icons.flag_outlined),
            onPressed: peer?.otherUserId == null || peer!.otherUserId.isEmpty
                ? null
                : () => context.push('/safety/report/${peer!.otherUserId}'),
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'theme') _openThemeSheet(context);
            },
            itemBuilder: (_) => [
              const PopupMenuItem(value: 'theme', child: Text('Chat theme')),
            ],
          ),
        ],
      ),
      body: Container(
        decoration:
            // wallpaper crossfade on theme layer only (doc 2 §2.4)
            resolveWallpaperDecoration(
              resolved,
              dark ? Brightness.dark : Brightness.light,
            ),
        child: SafeArea(
          child: Column(
            children: [
              Expanded(
                child: messages.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (e, _) => Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text("Couldn't load this chat."),
                        const SizedBox(height: 12),
                        OutlinedButton.icon(
                          onPressed: () =>
                              ref.invalidate(chatThreadProvider(widget.matchId)),
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                  data: (list) {
                    _maybeScrollToBottom(list.length);
                    return ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      itemCount: list.length + (showTyping ? 1 : 0),
                      itemBuilder: (context, i) {
                        if (i == list.length && showTyping) {
                          // Messenger 3-dot bubble while the peer (or companion)
                          // composes
                          return const TypingBubble();
                        }
                        final m = list[i];
                        final sent = myId != null && m.senderId == myId;
                        // Day separator when the calendar day changes (or on the
                        // first message) — the thread used to run every day
                        // together with no time context.
                        final prev = i > 0 ? list[i - 1] : null;
                        final showDay = prev == null ||
                            !_sameDay(prev.createdAt, m.createdAt);
                        final bubble = _buildMessage(
                          context,
                          m,
                          sent,
                          accent,
                          resolved.bubbleShape,
                        );
                        if (!showDay) return bubble;
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [_DaySeparator(day: m.createdAt), bubble],
                        );
                      },
                    );
                  },
                ),
              ),
              if (resolved.textScale != null) SizedBox(height: Spacing.xs),
              _IcebreakerRow(matchId: widget.matchId),
              SafeArea(
                top: false,
                child: Padding(
                  padding: EdgeInsets.fromLTRB(
                    Spacing.lg,
                    Spacing.sm,
                    Spacing.lg,
                    Spacing.md,
                  ),
                  child: Row(
                    children: [
                      _busySend
                          ? const Padding(
                              padding: EdgeInsets.all(12),
                              child: SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              ),
                            )
                          : IconButton(
                              icon: Icon(
                                (peer?.isAi ?? false)
                                    ? Icons.auto_awesome_outlined
                                    : Icons.photo_outlined,
                                color: accent,
                              ),
                              tooltip: (peer?.isAi ?? false)
                                  ? 'Ask for a moment'
                                  : 'Send photo',
                              onPressed: (peer?.isAi ?? false)
                                  ? _requestCompanionMoment
                                  : _sendGalleryImage,
                            ),
                      Expanded(
                        child: TextField(
                          controller: _composer,
                          textInputAction: TextInputAction.send,
                          onChanged: (v) {
                            _onComposerChanged(v);
                            setState(() {});
                          },
                          onSubmitted: (_) => _send(),
                          decoration: InputDecoration(
                            hintText: 'Type a message',
                            filled: true,
                            fillColor: const Color(0xFFF1F3F6),
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 10,
                            ),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(22),
                              borderSide: BorderSide.none,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 6),
                      // Send↔mic morph: an empty field shows the voice-note
                      // mic; the moment there's text it becomes the send button.
                      if (_composer.text.trim().isEmpty)
                        IconButton(
                          icon: const Icon(
                            Icons.mic_none,
                            color: Color(0xFF8A919C),
                          ),
                          tooltip: 'Voice note',
                          onPressed: () =>
                              context.push('/chat/${widget.matchId}/voice-note'),
                        )
                      else
                        CircleAvatar(
                          radius: 19,
                          backgroundColor: accent,
                          child: IconButton(
                            padding: EdgeInsets.zero,
                            icon: Icon(
                              Icons.send,
                              size: 18,
                              color: AccentThemeState.readableOn(accent),
                            ),
                            onPressed: _send,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMessage(
    BuildContext context,
    ChatMessage m,
    bool sent,
    Color accent,
    BubbleShape bubbleShape,
  ) {
    // doc 8 §A2.9/§A2.11: media renders inside a proper bubble — cached image
    // or GIF with a shimmer placeholder, or an inline voice player.
    if (m.mediaUrl != null) {
      final isVoice = m.mediaType == 'audio';
      if (isVoice) {
        return Align(
          key: ValueKey(m.id),
          alignment: sent ? Alignment.centerRight : Alignment.centerLeft,
          child: Padding(
            padding: const EdgeInsets.symmetric(
              vertical: 3,
              horizontal: Spacing.lg,
            ),
            child: VoiceNoteBubble(
              url: m.mediaUrl!,
              isSent: sent,
              accent: accent,
            ),
          ),
        );
      }
      return Align(
        key: ValueKey(m.id),
        alignment: sent ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          margin: const EdgeInsets.symmetric(
            vertical: 3,
            horizontal: Spacing.lg,
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(Spacing.radiusLg),
            child: ConstrainedBox(
              constraints: BoxConstraints(
                maxWidth: MediaQuery.sizeOf(context).width * 0.7,
                maxHeight: 280,
              ),
              // CachedNetworkImage handles GIFs too — cached thumbnails fix
              // the "very lag, slow image loading" complaint (doc 8 Part D.10).
              child: CachedNetworkImage(
                imageUrl: m.mediaUrl!,
                fit: BoxFit.cover,
                placeholder: (_, __) => Container(
                  width: 160,
                  height: 120,
                  color: const Color(0xFFF1F3F6),
                ),
                errorWidget: (_, __, ___) => Container(
                  width: 160,
                  height: 120,
                  color: const Color(0xFFF1F3F6),
                  child: const Icon(Icons.broken_image_outlined),
                ),
              ),
            ),
          ),
        ),
      );
    }
    return ChatBubble(
      key: ValueKey(m.id),
      text: m.body ?? '',
      isSent: sent,
      isAi: m.isAiSuggested,
      bubbleShape: bubbleShape,
      timestamp: m.createdAt,
      read: m.isRead,
    );
  }

  String _presenceLine(MatchSummary? peer, PresenceState? presence) {
    if (peer == null) return '';
    if (peer.isAi) {
      // companion day-presence surfaces through the roster payload; the
      // header keeps a stable human-feeling line
      return 'Companion · always up for a chat';
    }
    return presenceLabel(
      online: presence?.online ?? false,
      minutesAgo: presence?.minutesAgoNow,
    );
  }

  /// Companion threads: ask for an illustrated "moment from my day" — the
  /// server generates an identity-locked scene with the character's exact
  /// face, writes it into the thread with a human-feeling delay.
  Future<void> _requestCompanionMoment() async {
    if (_busySend) return;
    final matches =
        ref.read(matchesProvider).valueOrNull ?? const <MatchSummary>[];
    MatchSummary? peer;
    for (final m in matches) {
      if (m.matchId == widget.matchId) peer = m;
    }
    // resolve the session through the roster (character key -> session)
    setState(() => _busySend = true);
    try {
      final roster = await ref.read(companionRosterProvider.future);
      final card = roster.characters
          .where((c) => peer?.otherName.startsWith(c.name) ?? false)
          .firstOrNull;
      if (card == null) {
        throw AppException(
          'companion_not_found',
          message: 'Open the companion from the roster to request moments.',
        );
      }
      final session = await ref
          .read(apiClientProvider)
          .post<Map<String, dynamic>>('/saathi/${card.key}/sessions');
      final sessionId = session['session_id'] as String;
      final res = await ref
          .read(apiClientProvider)
          .post<Map<String, dynamic>>('/saathi/sessions/$sessionId/selfie');
      final delayMs =
          ((res['typing_delay_seconds'] as num?)?.toDouble() ?? 2.0) * 1000;
      await Future<void>.delayed(Duration(milliseconds: delayMs.round()));
      if (!mounted) return;
      // The caption already landed via the unified thread broadcast; fetch
      // history so the thread shows it + refresh moments list.
      ref.invalidate(chatThreadProvider(widget.matchId));
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(res['ai_label'] as String? ?? 'AI-illustrated moment'),
          duration: const Duration(seconds: 2),
        ),
      );
    } on AppException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.displayMessage)));
    } finally {
      if (mounted) setState(() => _busySend = false);
    }
  }

  /// Gallery image → upload → media message. No video in chat (product rule).
  Future<void> _sendGalleryImage() async {
    final picked = await ImagePicker().pickImage(
      source: ImageSource.gallery,
      imageQuality: 85,
    );
    if (picked == null || !mounted) return;
    setState(() => _busySend = true);
    try {
      final uploaded = await ref
          .read(apiClientProvider)
          .uploadMultipart('/media/upload?kind=photo', filePath: picked.path);
      final url = uploaded['url'] as String?;
      if (url == null || url.isEmpty) throw AppException('upload_failed');
      await ref
          .read(chatThreadProvider(widget.matchId).notifier)
          .sendMedia(mediaUrl: url, mediaType: 'image');
      ref.read(sfxProvider.notifier).play(Sfx.messageSent);
    } on AppException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not send: ${e.displayMessage}')),
      );
    } finally {
      if (mounted) setState(() => _busySend = false);
    }
  }

  Future<void> _send() async {
    final body = _composer.text.trim();
    if (body.isEmpty) return;
    ref.read(sfxProvider.notifier).play(Sfx.messageSent);
    _composer.clear();
    _stopTyping();
    await ref.read(chatThreadProvider(widget.matchId).notifier).send(body);
  }

  void _openThemeSheet(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => ThemePickerSheet(scope: scope),
    );
  }
}

/// Screen 30 — AI icebreaker suggestions; tap-to-insert-then-edit, never auto-send.
class _IcebreakerRow extends ConsumerStatefulWidget {
  const _IcebreakerRow({required this.matchId});
  final String matchId;

  @override
  ConsumerState<_IcebreakerRow> createState() => _IcebreakerRowState();
}

class _IcebreakerRowState extends ConsumerState<_IcebreakerRow> {
  List<String>? _suggestions;
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    // Load once for quiet/empty threads only — a busy chat has no need for
    // starter chips (they push content down).
    _loadIfQuiet();
  }

  Future<void> _loadIfQuiet() async {
    final current = ref.read(chatThreadProvider(widget.matchId)).valueOrNull;
    if (current != null && current.length > 2) return;
    if (_loading || _suggestions != null) return;
    _loading = true;
    try {
      final suggestions = await ref
          .read(chatThreadProvider(widget.matchId).notifier)
          .icebreakers();
      if (!mounted || suggestions.isEmpty) return;
      setState(() => _suggestions = suggestions);
    } finally {
      _loading = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_suggestions == null || _suggestions!.isEmpty)
      return const SizedBox.shrink();
    return SizedBox(
      height: 48,
      child: ListView.separated(
        padding: EdgeInsets.symmetric(horizontal: Spacing.lg),
        scrollDirection: Axis.horizontal,
        itemCount: _suggestions!.length,
        separatorBuilder: (_, __) => SizedBox(width: Spacing.md),
        itemBuilder: (context, i) => ActionChip(
          label: Text(_suggestions![i], overflow: TextOverflow.ellipsis),
          onPressed: () {
            // tap-to-insert for editing — never auto-send (doc 1 §4.1).
            // The registry notifies the screen so the send state rebuilds
            // (doc 8 §A2.7: the button state used to stay stale).
            ref.read(composerProvider).text = _suggestions![i];
          },
        ),
      ),
    );
  }
}

/// Registry so the icebreaker chips can insert into the thread's composer
/// (they render in a different widget subtree).
final composerProvider = Provider<ComposerRegistry>(
  (ref) => ComposerRegistry(),
);

class ComposerRegistry {
  final List<TextEditingController> _controllers = [];
  VoidCallback? onChanged;
  void add(TextEditingController c) => _controllers.add(c);
  void remove(TextEditingController c) => _controllers.remove(c);
  set text(String value) {
    for (final c in _controllers) {
      c.text = value;
      c.selection = TextSelection.collapsed(offset: value.length);
    }
    onChanged?.call();
  }
}

/// Centered day chip between messages from different calendar days.
class _DaySeparator extends StatelessWidget {
  const _DaySeparator({required this.day});
  final DateTime day;

  String _label(BuildContext context) {
    final now = DateTime.now();
    final d = DateTime(day.year, day.month, day.day);
    final today = DateTime(now.year, now.month, now.day);
    final diff = today.difference(d).inDays;
    if (diff == 0) return 'Today';
    if (diff == 1) return 'Yesterday';
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ];
    final y = d.year == now.year ? '' : ', ${d.year}';
    return '${months[d.month - 1]} ${d.day}$y';
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Center(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
          decoration: BoxDecoration(
            color: milan.paper100,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: milan.line200),
          ),
          child: Text(
            _label(context),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: milan.ink600,
            ),
          ),
        ),
      ),
    );
  }
}
