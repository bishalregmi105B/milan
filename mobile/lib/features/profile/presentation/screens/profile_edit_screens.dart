import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/common.dart' show VerifiedBadge;

/// Screen 13 — edit all profile fields inline.
class EditProfileScreen extends ConsumerStatefulWidget {
  const EditProfileScreen({super.key});

  @override
  ConsumerState<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends ConsumerState<EditProfileScreen> {
  final _name = TextEditingController();
  final _bio = TextEditingController();
  final _city = TextEditingController();
  bool _discreet = false;
  String _intent = 'serious';
  bool _loaded = false;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final me = await ref.read(apiClientProvider).get<Map<String, dynamic>>('/profile/me');
      final profile = me['profile'] as Map<String, dynamic>;
      if (!mounted) return;
      setState(() {
        _name.text = (profile['display_name'] as String?) ?? '';
        _bio.text = (profile['bio'] as String?) ?? '';
        _city.text = (profile['city'] as String?) ?? '';
        _discreet = (me['user']['discreet_mode'] as bool?) ?? false;
        _intent = (me['user']['intent_mode'] as String?) ?? 'serious';
        _loaded = true;
      });
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.code;
        _loaded = true; // never spin forever on a load failure
      });
    }
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await ref.read(apiClientProvider).put('/profile/me', body: {
        'display_name': _name.text.trim(),
        'bio': _bio.text.trim(),
        'city': _city.text.trim(),
        'discreet_mode': _discreet,
        'intent_mode': _intent,
      });
      if (mounted) context.pop();
    } on AppException catch (e) {
      setState(() => _error = e.code);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Edit Profile')),
      body: !_loaded
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: EdgeInsets.all(Spacing.xl), children: [
              TextField(controller: _name,
                  decoration: const InputDecoration(labelText: 'Name')),
              SizedBox(height: Spacing.lg),
              TextField(controller: _bio, maxLines: 4,
                  decoration: const InputDecoration(labelText: 'Bio')),
              SizedBox(height: Spacing.lg),
              TextField(controller: _city,
                  decoration: const InputDecoration(labelText: 'City')),
              SizedBox(height: Spacing.xl),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Discreet mode'),
                subtitle: Text('Hide from contacts, blur photos until mutual interest.',
                    style: TextStyle(fontSize: 12, color: milan.ink600)),
                value: _discreet,
                onChanged: (v) => setState(() => _discreet = v),
              ),
              Row(children: [
                Text('Intent', style: TextStyle(color: milan.ink600)),
                Spacer(),
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'serious', label: Text('Serious')),
                    ButtonSegment(value: 'casual', label: Text('Casual')),
                  ],
                  selected: {_intent},
                  onSelectionChanged: (s) => setState(() => _intent = s.first),
                ),
              ]),
              if (_error != null)
                Padding(padding: EdgeInsets.only(top: Spacing.md),
                    child: Text(_error!, style: TextStyle(color: milan.error500))),
              SizedBox(height: Spacing.xl),
              FilledButton(
                onPressed: _saving ? null : _save,
                child: Text(_saving ? 'Saving…' : 'Save'),
              ),
            ]),
    );
  }
}

/// Screen 14 — Hinge-style prompt bank picker with 3 active slots.
class PromptsEditorScreen extends ConsumerStatefulWidget {
  const PromptsEditorScreen({super.key});

  static const _bank = [
    'A life goal of mine…',
    'The way to win me over is…',
    'My simple pleasures…',
    'Two truths and a lie…',
    'I geek out on…',
    'Typical Sunday…',
  ];

  @override
  ConsumerState<PromptsEditorScreen> createState() => _PromptsEditorScreenState();
}

class _PromptsEditorScreenState extends ConsumerState<PromptsEditorScreen> {
  final List<int> _slots = [];
  final Map<int, TextEditingController> _answers = {};
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _loadExisting();
  }

  Future<void> _loadExisting() async {
    try {
      final me = await ref.read(apiClientProvider).get<Map<String, dynamic>>('/profile/me');
      final prompts = (me['profile']?['prompts'] as List?) ?? const [];
      if (!mounted) return;
      setState(() {
        for (final p in prompts) {
          final map = p as Map<String, dynamic>;
          final question = (map['question'] ?? map['prompt'] ?? '') as String;
          final slot = PromptsEditorScreen._bank.indexOf(question);
          if (slot >= 0 && !_slots.contains(slot)) {
            _slots.add(slot);
            _answers[slot] = TextEditingController(text: (map['answer'] ?? '') as String);
          }
        }
      });
    } on AppException {
      // editing starts empty if load fails — nothing breaks
    }
  }

  @override
  void dispose() {
    for (final c in _answers.values) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Prompt answers')),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        Text('Pick up to 3 prompts.', style: TextStyle(color: milan.ink600)),
        Wrap(spacing: Spacing.md, runSpacing: Spacing.md, children: [
          for (var i = 0; i < PromptsEditorScreen._bank.length; i++)
            FilterChip(
              label: Text(PromptsEditorScreen._bank[i]),
              selected: _slots.contains(i),
              onSelected: (sel) => setState(() {
                if (sel && _slots.length < 3) {
                  _slots.add(i);
                  _answers[i] = TextEditingController();
                } else if (!sel) {
                  _answers.remove(i)?.dispose();
                  _slots.remove(i);
                }
              }),
            ),
        ]),
        SizedBox(height: Spacing.xl),
        for (final slot in _slots)
          Padding(
            padding: EdgeInsets.only(bottom: Spacing.lg),
            child: TextField(
              controller: _answers[slot],
              maxLines: 2,
              decoration: InputDecoration(
                labelText: PromptsEditorScreen._bank[slot],
                suffixIcon: IconButton(
                  icon: Icon(Icons.auto_fix_high, color: milan.dhaka500),
                  tooltip: 'Get AI feedback',
                  onPressed: () =>
                      context.push('/profile/prompt-feedback?answer=${Uri.encodeComponent(_answers[slot]!.text)}'),
                ),
              ),
            ),
          ),
        FilledButton(
            onPressed: _saving ? null : _savePrompts,
            child: Text(_saving ? 'Saving…' : 'Save prompts')),
      ]),
    );
  }

  Future<void> _savePrompts() async {
    setState(() => _saving = true);
    try {
      final prompts = <Map<String, String>>[
        for (var i = 0; i < PromptsEditorScreen._bank.length; i++)
          if ((_answers[i]?.text ?? '').trim().isNotEmpty)
            {'question': PromptsEditorScreen._bank[i],
             'answer': _answers[i]!.text.trim()},
      ];
      await ref.read(apiClientProvider).put('/profile/me', body: {'prompts': prompts});
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Prompts saved to your profile.')));
      context.pop();
    } on AppException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not save: ${e.displayMessage}')));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}

/// Screen 15 — rough notes → 3 AI bio drafts.
class BioAssistantScreen extends ConsumerStatefulWidget {
  const BioAssistantScreen({super.key});

  @override
  ConsumerState<BioAssistantScreen> createState() => _BioAssistantScreenState();
}

class _BioAssistantScreenState extends ConsumerState<BioAssistantScreen> {
  final _notes = TextEditingController();
  List<String>? _drafts;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _notes.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final res = await ref.read(apiClientProvider).post<Map<String, dynamic>>(
          '/profile/bio/generate',
          body: {'notes': _notes.text.trim(), 'language': 'en'});
      setState(() => _drafts = (res['drafts'] as List).cast<String>());
    } on AppException catch (e) {
      setState(() => _error = e.statusCode == 503
          ? "Milan's AI is taking a breather — try again shortly."
          : e.code);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('AI Bio Assistant')),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        TextField(controller: _notes, maxLines: 5,
            decoration: const InputDecoration(
                labelText: 'Rough notes about yourself', alignLabelWithHint: true)),
        SizedBox(height: Spacing.lg),
        FilledButton.icon(icon: Icon(Icons.auto_awesome),
            label: Text(_busy ? 'Thinking…' : 'Generate drafts'),
            onPressed: _busy ? null : _generate),
        if (_error != null)
          Padding(padding: EdgeInsets.symmetric(vertical: Spacing.md),
              child: Text(_error!, style: TextStyle(color: milan.error500))),
        SizedBox(height: Spacing.xl),
        for (final draft in _drafts ?? <String>[])
          Container(
            margin: EdgeInsets.only(bottom: Spacing.lg),
            padding: EdgeInsets.all(Spacing.lg),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(Spacing.radiusMd),
            ),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Text('AI DRAFT',
                    style: TextStyle(fontSize: 10, letterSpacing: .04, color: milan.ink400)),
                Spacer(),
                Icon(Icons.auto_awesome, size: 12, color: milan.dhaka500),
              ]),
              SizedBox(height: Spacing.sm),
              Text(draft, style: TextStyle(height: 1.4)),
              Align(alignment: Alignment.bottomRight,
                  child: TextButton(onPressed: () {}, child: const Text('Use this'))),
            ]),
          ),
      ]),
    );
  }
}

/// Screen 16 — AI prompt grading.
class PromptFeedbackScreen extends ConsumerStatefulWidget {
  const PromptFeedbackScreen({super.key, required this.initialAnswer});
  final String initialAnswer;

  @override
  ConsumerState<PromptFeedbackScreen> createState() => _PromptFeedbackScreenState();
}

class _PromptFeedbackScreenState extends ConsumerState<PromptFeedbackScreen> {
  late final _controller = TextEditingController(text: widget.initialAnswer);
  Map<String, dynamic>? _result;
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _grade() async {
    setState(() => _busy = true);
    try {
      final res = await ref.read(apiClientProvider).post<Map<String, dynamic>>(
          '/profile/prompts/feedback',
          body: {'answer': _controller.text.trim()});
      setState(() => _result = res);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final tag = _result?['tag'] as String?;
    final tagColor = switch (tag) {
      'specific' => milan.pine500,
      'could-read-as-a-red-flag' => milan.error500,
      _ => milan.warning500,
    };
    return Scaffold(
      appBar: AppBar(title: const Text('Prompt Feedback')),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        TextField(controller: _controller, maxLines: 3,
            decoration: const InputDecoration(labelText: 'Your prompt answer')),
        SizedBox(height: Spacing.lg),
        FilledButton.icon(icon: Icon(Icons.grade_outlined),
            label: Text(_busy ? 'Grading…' : 'Grade my answer'),
            onPressed: _busy ? null : _grade),
        if (_result != null) ...[
          SizedBox(height: Spacing.xl),
          Chip(backgroundColor: tagColor.withValues(alpha: .12),
              label: Text(tag ?? '', style: TextStyle(color: tagColor))),
          SizedBox(height: Spacing.md),
          Text(_result!['suggestion'] as String? ?? '',
              style: TextStyle(height: 1.45)),
          Padding(padding: EdgeInsets.only(top: Spacing.sm),
              child: Text('AI feedback', style: TextStyle(fontSize: 10, color: milan.ink400))),
        ],
      ]),
    );
  }
}

/// Screen 17 — verification status detail.
class VerificationStatusScreen extends StatelessWidget {
  const VerificationStatusScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Verification')),
      body: Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          VerifiedBadge(),
          SizedBox(height: Spacing.lg),
          Text('Verified profile', style: context.h3),
          SizedBox(height: Spacing.sm),
          Text('Your live selfie matched your profile photos.\nSelfie images are never stored.',
              textAlign: TextAlign.center, style: TextStyle(color: milan.ink600)),
          SizedBox(height: Spacing.xl),
          OutlinedButton(onPressed: () {}, child: const Text('Re-verify')),
        ]),
      ),
    );
  }
}
