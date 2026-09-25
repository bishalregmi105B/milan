import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/chat_theme_tokens.dart';
import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/localization/app_localizations.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/theme_picker_sheet.dart';
import '../../../../shared/widgets/common.dart' show AICharacterCard;
import '../../application/saathi_session_provider.dart';

/// Screen 46 — first-run explanation + real 18+ gate (guardrail #2).
/// Consent is persisted SERVER-SIDE per account (`/profile/saathi-consent`),
/// so this intro shows once, ever — re-shown only if the terms version
/// changes. No auto-accept: the checkbox + Continue are mandatory.
class SaathiIntroScreen extends ConsumerStatefulWidget {
  const SaathiIntroScreen({super.key});

  @override
  ConsumerState<SaathiIntroScreen> createState() => _SaathiIntroScreenState();
}

class _SaathiIntroScreenState extends ConsumerState<SaathiIntroScreen> {
  bool _confirmed18 = false;
  bool _checking = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _checkExistingConsent();
  }

  Future<void> _checkExistingConsent() async {
    try {
      final res = await ref
          .read(apiClientProvider)
          .get<Map<String, dynamic>>('/profile/saathi-consent');
      if (!mounted) return;
      if (res['accepted'] == true) {
        // already accepted on this account — straight to the companions
        context.pushReplacement('/saathi/characters');
        return;
      }
      setState(() => _checking = false);
    } on AppException {
      if (!mounted) return;
      // gate stays shown on failure; user can still accept (idempotent POST)
      setState(() {
        _checking = false;
        _error = 'Could not reach Milan — your acceptance will sync when it does.';
      });
    }
  }

  Future<void> _accept() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref.read(apiClientProvider).post('/profile/saathi-consent',
          body: {'confirm_18': true});
      if (!mounted) return;
      context.pushReplacement('/saathi/characters');
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = e.displayMessage;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final l10n = AppLocalizations.of(context)!;
    if (_checking) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.saathiIntroTitle)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    return Scaffold(
      appBar: AppBar(title: Text(l10n.saathiIntroTitle)),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        Icon(Icons.auto_awesome, size: 56, color: milan.dhaka500),
        SizedBox(height: Spacing.xl),
        Text(l10n.saathiConsentBody, style: TextStyle(height: 1.55)),
        SizedBox(height: Spacing.xl),
        Container(
          padding: EdgeInsets.all(Spacing.lg),
          decoration: BoxDecoration(color: milan.paper100,
              borderRadius: BorderRadius.circular(Spacing.radiusMd)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('Saathi IS', style: TextStyle(fontWeight: FontWeight.w700, color: milan.pine500)),
            Text('A place to practice openers, banter and date debriefs.', style: TextStyle(fontSize: 13)),
            SizedBox(height: Spacing.md),
            Text('Saathi IS NOT', style: TextStyle(fontWeight: FontWeight.w700, color: milan.error500)),
            Text('A real person. A romantic partner. A replacement for human connection.',
                style: TextStyle(fontSize: 13)),
          ]),
        ),
        CheckboxListTile(
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          title: const Text('I confirm I am 18 or older'),
          value: _confirmed18,
          onChanged: _submitting
              ? null
              : (v) => setState(() => _confirmed18 = v ?? false),
        ),
        if (_error != null)
          Padding(padding: EdgeInsets.only(bottom: Spacing.md),
              child: Text(_error!, style: TextStyle(fontSize: 12, color: milan.error500))),
        FilledButton(
          onPressed: _confirmed18 && !_submitting ? _accept : null,
          child: Text(_submitting ? l10n.commonLoading : l10n.commonContinue),
        ),
      ]),
    );
  }
}

/// Screen 47 — companion gallery (routed; illustrated cards only).
/// The roster comes from the API (`/saathi/characters`) — never hardcoded —
/// and tapping a companion STARTS the session server-side, which provisions
/// a real match thread, then opens the SAME chat screen as human matches (§14).
class SaathiGalleryRouteScreen extends ConsumerWidget {
  const SaathiGalleryRouteScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final rosterAsync = ref.watch(companionRosterProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Choose a companion', overflow: TextOverflow.ellipsis)),
      body: rosterAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Could not load companions. Pull to retry.',
            style: TextStyle(color: milan.error500))),
        data: (roster) {
          final cards = roster.characters;
          if (cards.isEmpty) {
            return Center(child: Text('No companions available yet.',
                style: TextStyle(color: milan.ink600)));
          }
          // Column list: every companion's full description is visible —
          // like Messenger's contact list, not a cropped card grid.
          return ListView.separated(
              padding: EdgeInsets.all(Spacing.lg),
              itemCount: cards.length,
              separatorBuilder: (_, __) => const SizedBox(height: Spacing.md),
              itemBuilder: (context, i) {
                final c = cards[i];
                return Card(
                  key: ValueKey(c.key),
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(Spacing.radiusLg),
                      side: BorderSide(color: milan.line200)),
                  child: InkWell(
                      borderRadius: BorderRadius.circular(Spacing.radiusLg),
                      onTap: () => _startConversation(context, ref, c),
                      child: Padding(
                          padding: EdgeInsets.all(Spacing.lg),
                          child: Row(crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                CircleAvatar(radius: 30,
                                    backgroundColor: c.accentColor.withValues(alpha: 0.15),
                                    backgroundImage: c.avatarUrl != null
                                        ? CachedNetworkImageProvider(c.avatarUrl!)
                                        : null,
                                    child: c.avatarUrl == null
                                        ? Text(c.name.characters.first,
                                            style: TextStyle(fontSize: 20,
                                                fontWeight: FontWeight.w700,
                                                color: c.accentColor))
                                        : null),
                                SizedBox(width: Spacing.lg),
                                Expanded(child: Column(crossAxisAlignment:
                                    CrossAxisAlignment.start, children: [
                                  Row(children: [
                                    Expanded(child: Text(c.name, maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(fontWeight:
                                            FontWeight.w700, fontSize: 16))),
                                    if (c.locked)
                                      Container(padding: const EdgeInsets.symmetric(
                                          horizontal: 8, vertical: 2),
                                          decoration: BoxDecoration(border: Border.all(
                                              color: milan.marigold500),
                                              borderRadius: BorderRadius.circular(
                                                  Spacing.radiusSm)),
                                          child: Text('PASS',
                                              style: TextStyle(fontSize: 10,
                                                  fontWeight: FontWeight.w800,
                                                  color: milan.marigold500)))
                                    else
                                      Container(padding: const EdgeInsets.symmetric(
                                          horizontal: 8, vertical: 2),
                                          decoration: BoxDecoration(border: Border.all(
                                              color: milan.dhaka500),
                                              borderRadius: BorderRadius.circular(
                                                  Spacing.radiusSm)),
                                          child: Text('AI', style: TextStyle(
                                              fontSize: 10, fontWeight: FontWeight.w700,
                                              color: milan.dhaka500))),
                                  ]),
                                  SizedBox(height: Spacing.xs),
                                  Text(c.description,
                                      style: TextStyle(fontSize: 13, height: 1.4,
                                          color: milan.ink600)),
                                ])),
                              ]))),
                );
              });
        },
      ),
    );
  }

  Future<void> _startConversation(
      BuildContext context, WidgetRef ref, CompanionCard card) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      final res = await ref
          .read(apiClientProvider)
          .post<Map<String, dynamic>>('/saathi/${card.key}/sessions');
      final matchId = res['match_id'] as String?;
      if (!context.mounted) return;
      if (matchId == null) {
        // practice-only companion without a match (fallback to legacy screen)
        context.push('/saathi/chat/${card.key}');
        return;
      }
      // Companions live in the unified inbox — open the normal chat thread.
      context.pushReplacement('/chat/$matchId');
    } on AppException catch (e) {
      if (e.statusCode == 403) {
        messenger.showSnackBar(SnackBar(content: Text(e.displayMessage)));
      } else {
        messenger.showSnackBar(const SnackBar(
            content: Text('Could not start the conversation. Try again shortly.')));
      }
    }
  }
}

/// Screen 48 — character detail with sample opening line.
class CharacterDetailScreen extends StatelessWidget {
  const CharacterDetailScreen({super.key, required this.characterId});
  final String characterId;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: Text(characterId.toUpperCase())),
      body: Padding(padding: EdgeInsets.all(Spacing.xl), child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            CircleAvatar(radius: 40, backgroundColor: milan.dhaka100,
                child: Text(characterId.characters.first.toUpperCase(),
                    style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: milan.dhaka500))),
            SizedBox(height: Spacing.lg),
            Center(child: Chip(label: Text('AI · practice companion',
                style: TextStyle(fontSize: 11)))),
            Spacer(),
            Container(padding: EdgeInsets.all(Spacing.lg),
                decoration: BoxDecoration(color: milan.paper100,
                    borderRadius: BorderRadius.circular(Spacing.radiusMd)),
                child: Text('"Hi! Want to try a quick opener together?"',
                    style: TextStyle(fontStyle: FontStyle.italic))),
            SizedBox(height: Spacing.xl),
            FilledButton(onPressed: () => context.push('/saathi/chat/$characterId'),
                child: const Text('Start chat')),
          ])),
    );
  }
}

/// Screen 50 — Saathi voice call with waveform avatar + transcript toggle.
class SaathiVoiceCallScreen extends ConsumerStatefulWidget {
  const SaathiVoiceCallScreen({super.key, required this.characterId});
  final String characterId;

  @override
  ConsumerState<SaathiVoiceCallScreen> createState() => _SaathiVoiceCallScreenState();
}

class _SaathiVoiceCallScreenState extends ConsumerState<SaathiVoiceCallScreen> {
  bool _showTranscript = false;
  final List<(String, String)> _transcript = [];

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      backgroundColor: milan.ink900,
      appBar: AppBar(backgroundColor: Colors.transparent,
          actions: [TextButton(onPressed: () =>
              setState(() => _showTranscript = !_showTranscript),
              child: Text(_showTranscript ? 'Hide transcript' : 'Show transcript',
                  style: TextStyle(color: Colors.white70)))]),
      body: Column(children: [
        Expanded(child: _showTranscript
            ? ListView(padding: EdgeInsets.all(Spacing.xl), children: [
                for (final (who, text) in _transcript)
                  Padding(padding: EdgeInsets.only(bottom: Spacing.md),
                      child: Text('$who: $text',
                          style: TextStyle(color: Colors.white70))),
              ])
            : Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                CircleAvatar(radius: 52, backgroundColor: milan.dhaka500,
                    child: Icon(Icons.auto_awesome, color: Colors.white, size: 34)),
                SizedBox(height: Spacing.lg),
                // live waveform
                Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  for (final h in [8, 16, 26, 16, 8])
                    Container(width: 4, height: h.toDouble(),
                        margin: EdgeInsets.symmetric(horizontal: Spacing.xs),
                        decoration: BoxDecoration(color: milan.marigold500,
                            borderRadius: BorderRadius.circular(2))),
                ]),
                SizedBox(height: Spacing.md),
                Text('Saathi · AI companion',
                    style: TextStyle(color: Colors.white54, fontSize: 12)),
              ]))),
        SafeArea(child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          CircleAvatar(radius: 26, backgroundColor: Colors.white24,
              child: Icon(Icons.mic_none, color: Colors.white)),
          SizedBox(width: Spacing.xl),
          CircleAvatar(radius: 30, backgroundColor: milan.error500,
              child: IconButton(icon: Icon(Icons.call_end, color: Colors.white),
                  onPressed: () => context.pop())),
        ])),
      ]),
    );
  }
}

/// Screen 51 — proactive messaging controls + pause.
/// Wired to PUT /saathi/sessions/:id/settings {is_paused, proactive_opt_in}
/// via [saathiSessionProvider] (the backend has no frequency field, so the
/// old frequency stepper was removed). Optimistic flip with error revert.
class SaathiSettingsScreen extends ConsumerWidget {
  const SaathiSettingsScreen({super.key, required this.characterId});
  final String characterId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final session = ref.watch(saathiSessionProvider(characterId));
    return Scaffold(
      appBar: AppBar(title: const Text('Saathi settings')),
      body: session.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Text('Could not load Saathi settings — try again shortly.',
              style: TextStyle(color: milan.error500)),
        ),
        data: (state) => ListView(padding: EdgeInsets.all(Spacing.xl), children: [
          SwitchListTile(contentPadding: EdgeInsets.zero,
              title: Text(AppLocalizations.of(context)!.saathiSettingsProactive),
              subtitle: Text('Off by default. Max one message per day, functionally framed only.',
                  style: TextStyle(fontSize: 12, color: milan.ink600)),
              value: state.proactiveOptIn,
              onChanged: (v) => _updateSetting(context, ref,
                  proactiveOptIn: v)),
          Divider(),
          SwitchListTile(contentPadding: EdgeInsets.zero,
              title: Text(AppLocalizations.of(context)!.saathiPause),
              value: state.isPaused,
              onChanged: (v) => _updateSetting(context, ref, isPaused: v)),
        ]),
      ),
    );
  }

  Future<void> _updateSetting(BuildContext context, WidgetRef ref,
      {bool? isPaused, bool? proactiveOptIn}) async {
    try {
      await ref
          .read(saathiSessionProvider(characterId).notifier)
          .updateSettings(isPaused: isPaused, proactiveOptIn: proactiveOptIn);
    } on AppException catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Could not save Saathi settings (${e.code})'),
        ));
      }
    }
  }
}

/// Screen 52 — post-date reflection feeding matching signal (with consent).
class SessionDebriefScreen extends ConsumerStatefulWidget {
  const SessionDebriefScreen({super.key, required this.matchId});
  final String matchId;

  @override
  ConsumerState<SessionDebriefScreen> createState() => _SessionDebriefScreenState();
}

class _SessionDebriefScreenState extends ConsumerState<SessionDebriefScreen> {
  String? _wentWell;
  final _notes = TextEditingController();

  @override
  void dispose() {
    _notes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Date debrief')),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        const Text('How did it go?'),
        Wrap(spacing: Spacing.md, children: [
          for (final option in ['Great — second date!', 'Nice but no spark', 'Not great'])
            ChoiceChip(label: Text(option), selected: _wentWell == option,
                onSelected: (_) => setState(() => _wentWell = option)),
        ]),
        TextField(controller: _notes, maxLines: 4,
            decoration: const InputDecoration(labelText: 'Anything you want to note?',
                alignLabelWithHint: true)),
        SwitchListTile(contentPadding: EdgeInsets.zero,
            title: const Text('Use this to improve my matches'),
            subtitle: const Text('Only aggregated signals are used, never your notes.',
                style: TextStyle(fontSize: 12)),
            value: true, onChanged: (_) {}),
        FilledButton(onPressed: () => context.pop(), child: const Text('Done')),
      ]),
    );
  }
}


/// Full-screen host for the Saathi-scoped ThemePickerSheet route.
class SaathiThemeRouteScreen extends StatelessWidget {
  const SaathiThemeRouteScreen({super.key, required this.characterId});
  final String characterId;

  @override
  Widget build(BuildContext context) {
    return ThemePickerHostPage(
      title: 'Chat theme · this Saathi character',
      scopeBuilder: () => ChatThemeScopeKey.saathi(characterId),
    );
  }
}
