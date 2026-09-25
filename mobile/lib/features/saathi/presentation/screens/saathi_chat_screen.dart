import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/chat_theme_presets.dart';
import '../../../../app/theme/chat_theme_tokens.dart';
import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/motion_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../shared/widgets/chat_bubble.dart';
import '../../../../shared/widgets/common.dart';
import '../../../../shared/widgets/typing_indicator.dart';
import '../../../personalization/application/theme_provider.dart';
import '../../application/saathi_session_provider.dart';

/// Screen 49 — Saathi chat. AI-labeled everywhere: persistent header tag,
/// dashed AI bubbles, signature character theme by default (doc 3 §6).
class SaathiChatScreen extends ConsumerStatefulWidget {
  const SaathiChatScreen({super.key, required this.characterId});
  final String characterId;

  @override
  ConsumerState<SaathiChatScreen> createState() => _SaathiChatScreenState();
}

class _SaathiChatScreenState extends ConsumerState<SaathiChatScreen> {
  final _composer = TextEditingController();
  final _scroll = ScrollController();
  bool _typing = false;
  String? _toneChip;

  static const _toneChips = ['playful', 'honest', 'serious', 'sweet'];

  ChatThemeScopeKey get scope => ChatThemeScopeKey.saathi(widget.characterId);

  @override
  void initState() {
    super.initState();
    // P1-10: reload persisted history every time the chat is opened.
    Future.microtask(() async {
      await ref
          .read(saathiSessionProvider(widget.characterId).notifier)
          .loadHistory();
      _scrollToBottom();
    });
  }

  @override
  void dispose() {
    _composer.dispose();
    _scroll.dispose();
    super.dispose();
  }

  /// Keep the newest message in view — the list had no controller, so sent and
  /// received bubbles landed below the fold until the user scrolled by hand.
  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(_scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
    });
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final session = ref.watch(saathiSessionProvider(widget.characterId));
    final themeAsync = ref.watch(themeProvider(scope));
    final resolved =
        themeAsync.valueOrNull?.theme ?? MilanChatPresets.defaultForSaathiCharacter(widget.characterId);
    final dark = Theme.of(context).brightness == Brightness.dark;
    final showTyping = _typing && !Motion.prefersReducedMotion(context);

    return Scaffold(
      appBar: AppBar(
        title: Row(children: [
          // server-provided display name already carries the "· AI" tag;
          // the badge stays as a persistent visual marker (AI disclosure)
          Text(session.valueOrNull?.characterDisplayName ?? 'Saathi',
              style: const TextStyle(fontWeight: FontWeight.w600)),
          SizedBox(width: Spacing.md),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              border: Border.all(color: milan.dhaka500),
              borderRadius: BorderRadius.circular(Spacing.radiusSm),
            ),
            child: Text('AI',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: milan.dhaka500)),
          ),
        ]),
        actions: [
          IconButton(
              icon: Icon(Icons.palette_outlined),
              tooltip: 'Chat theme',
              onPressed: () =>
                  context.push('/saathi/chat/${widget.characterId}/theme')),
          IconButton(icon: Icon(Icons.settings_outlined), onPressed: () =>
              context.push('/saathi/settings?character=${widget.characterId}')),
        ],
      ),
      body: Container(
        decoration: resolveWallpaperDecoration(resolved, dark ? Brightness.dark : Brightness.light),
        child: SafeArea(
          child: Column(children: [
            session.when(
              loading: () => const LinearProgressIndicator(minHeight: 2),
              error: (e, _) => Padding(
                padding: EdgeInsets.all(Spacing.lg),
                child: Text("Milan's AI is taking a breather — try again shortly.",
                    style: TextStyle(color: milan.error500)),
              ),
              data: (state) => Expanded(
                child: Column(children: [
                  if (state.bondStage != null) _bondHud(state, milan),
                  if (state.showCrisisCard) _crisisCard(milan),
                  Expanded(
                    child: ListView.builder(
                      controller: _scroll,
                      padding: EdgeInsets.symmetric(vertical: Spacing.lg),
                      itemCount: state.messages.length + (showTyping ? 1 : 0),
                      itemBuilder: (context, i) {
                        if (i == state.messages.length && showTyping) {
                          return Align(
                            alignment: Alignment.centerLeft,
                            child: Padding(
                              padding: EdgeInsets.symmetric(horizontal: Spacing.xl),
                              child: TypingIndicator(color: milan.dhaka500),
                            ),
                          );
                        }
                        final m = state.messages[i];
                        final isLastAi = m.isAi && i == state.messages.length - 1 && !showTyping;
                        return GestureDetector(
                          // swipe-to-regenerate (#26): long-press the latest
                          // AI bubble to re-roll the reply
                          onLongPress: isLastAi && state.lastUserBody != null
                              ? () => _send(state.lastUserBody!,
                                  regenerateVariant: 1)
                              : null,
                          child: ChatBubble(
                            text: m.content,
                            isSent: !m.isAi,
                            isAi: m.isAi,
                            bubbleColor: m.isAi
                                ? resolved.bubbleColorReceived
                                : resolved.bubbleColorSent,
                            bubbleShape: resolved.bubbleShape,
                          ),
                        );
                      },
                    ),
                  ),
                  // Director chips (#33): tap-to-steer the next reply's tone
                  SizedBox(
                    height: 40,
                    child: ListView(
                      scrollDirection: Axis.horizontal,
                      padding: EdgeInsets.symmetric(horizontal: Spacing.lg),
                      children: [
                        for (final chip in _toneChips)
                          Padding(
                            padding: EdgeInsets.only(right: Spacing.sm),
                            child: ChoiceChip(
                              label: Text(chip),
                              selected: _toneChip == chip,
                              onSelected: (_) => setState(() =>
                                  _toneChip = _toneChip == chip ? null : chip),
                            ),
                          ),
                      ],
                    ),
                  ),
                ]),
              ),
            ),
            if (session.valueOrNull?.degraded ?? false)
              Padding(
                padding: EdgeInsets.only(bottom: Spacing.sm),
                child: Text("Milan's AI is taking a breather — try again shortly.",
                    style: TextStyle(fontSize: 12, color: milan.warning500)),
              ),
            Padding(
              padding: EdgeInsets.fromLTRB(Spacing.lg, Spacing.sm, Spacing.lg, Spacing.md),
              child: Row(children: [
                Expanded(
                  child: TextField(
                    controller: _composer,
                    onSubmitted: (v) => _send(v.trim()),
                    decoration: InputDecoration(hintText: 'Practice a conversation...'),
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.send, color: milan.dhaka500),
                  onPressed: () => _send(_composer.text.trim()),
                ),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  /// Slim bond HUD: stage name + streak only — NO numeric intimacy meter is
  /// ever shown (master plan §4.6, CA SB 243 / FTC 6(b) pattern).
  Widget _bondHud(SaathiSessionState state, MilanColors milan) {
    return Padding(
      padding: EdgeInsets.fromLTRB(Spacing.lg, Spacing.sm, Spacing.lg, 0),
      child: Row(children: [
        Icon(Icons.favorite_border, size: 14, color: milan.dhaka500),
        SizedBox(width: Spacing.sm),
        Text('${state.bondStage ?? ''} · day ${state.streakDays}',
            style: TextStyle(fontSize: 12, color: milan.ink600)),
        const Spacer(),
        if (state.presenceState != null)
          Text(
            state.presenceState == 'busy'
                ? (state.presenceActivity ?? 'busy')
                : state.presenceState!,
            style: TextStyle(fontSize: 12, color: milan.ink600),
          ),
      ]),
    );
  }

  Widget _crisisCard(MilanColors milan) {
    return Container(
      margin: EdgeInsets.fromLTRB(Spacing.lg, Spacing.lg, Spacing.lg, 0),
      padding: EdgeInsets.all(Spacing.lg),
      decoration: BoxDecoration(
        color: milan.pine100,
        borderRadius: BorderRadius.circular(Spacing.radiusMd),
        border: Border.all(color: milan.pine500),
      ),
      child: Row(children: [
        Icon(Icons.support_agent, color: milan.pine500),
        SizedBox(width: Spacing.md),
        Expanded(
          child: Text(
            'It sounds like things are heavy right now. Support resources are here whenever you need them.',
            style: TextStyle(color: milan.ink900, fontSize: 13),
          ),
        ),
      ]),
    );
  }

  Future<void> _send(String body, {int regenerateVariant = 0}) async {
    if (body.isEmpty || _typing) return;
    if (regenerateVariant == 0) _composer.clear();
    setState(() => _typing = true);
    _scrollToBottom();
    try {
      await ref.read(saathiSessionProvider(widget.characterId).notifier).send(
            body,
            regenerateVariant: regenerateVariant,
            toneChip: _toneChip,
          );
    } finally {
      if (mounted) setState(() => _typing = false);
      _scrollToBottom();
    }
  }
}

/// Screen 47 — curated persona gallery (illustrated cards, never photoreal).
class SaathiCharacterGalleryScreen extends ConsumerWidget {
  const SaathiCharacterGalleryScreen({super.key});

  static const _roster = [
    (key: 'asha', name: 'Asha', desc: 'Warm and curious — great for general conversation flow and active-listening practice.', color: Color(0xFF7B1E3A)),
    (key: 'bibek', name: 'Bibek', desc: 'Witty and quick — practice playful banter and handling teasing.', color: Color(0xFFB8791A)),
    (key: 'priya', name: 'Priya', desc: 'Calm and patient — eases nerves before a first message or a real date.', color: Color(0xFF1F6F54)),
    (key: 'sagar', name: 'Sagar', desc: 'Direct and constructive — gives real feedback on your draft messages.', color: Color(0xFF43535C)),
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Choose your practice companion')),
      body: GridView.count(
        crossAxisCount: 2,
        mainAxisSpacing: Spacing.lg,
        crossAxisSpacing: Spacing.lg,
        padding: EdgeInsets.all(Spacing.xl),
        childAspectRatio: 0.78,
        children: [
          for (final c in _roster)
            AICharacterCard(
              key: ValueKey(c.key),
              name: c.name,
              description: c.desc,
              initial: c.name.characters.first,
              color: c.color,
              onTap: () => context.push('/saathi/chat/${c.key}'),
            ),
        ],
      ),
    );
  }
}
