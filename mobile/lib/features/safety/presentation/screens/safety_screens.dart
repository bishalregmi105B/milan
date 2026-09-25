import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/common.dart' show VerifiedBadge;

/// Screen 54 — safety hub.
class SafetyCenterScreen extends StatelessWidget {
  const SafetyCenterScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Safety Center')),
      body: ListView(
        padding: EdgeInsets.all(Spacing.xl),
        children: [
          for (final card in [
            (
              'Block list',
              Icons.block_outlined,
              '/safety/blocklist',
              milan.ink600,
            ),
            (
              'How verification works',
              Icons.verified_user_outlined,
              '/safety/verification',
              milan.pine500,
            ),
          ])
            Card(
              margin: EdgeInsets.only(bottom: Spacing.md),
              elevation: 0,
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(Spacing.radiusMd),
              ),
              child: ListTile(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(Spacing.radiusMd),
                ),
                leading: Icon(card.$2, color: card.$4),
                title: Text(card.$1),
                trailing: Icon(Icons.chevron_right, color: milan.ink400),
                onTap: () => context.push(card.$3),
              ),
            ),
          SizedBox(height: Spacing.xl),
          FilledButton.tonalIcon(
            icon: Icon(Icons.emergency, color: milan.error500),
            label: const Text('Emergency'),
            style: FilledButton.styleFrom(
              backgroundColor: milan.error500.withValues(alpha: .1),
            ),
            onPressed: () => context.push('/safety/panic'),
          ),
        ],
      ),
    );
  }
}

/// Screen 55 — multi-step report flow.
class ReportFlowScreen extends ConsumerStatefulWidget {
  const ReportFlowScreen({super.key, required this.targetId});
  final String targetId;

  @override
  ConsumerState<ReportFlowScreen> createState() => _ReportFlowScreenState();
}

class _ReportFlowScreenState extends ConsumerState<ReportFlowScreen> {
  static const _reasons = {
    'scam_or_fraud': 'Scam or fraud',
    'harassment': 'Harassment',
    'inappropriate_photos': 'Inappropriate photos',
    'fake_profile': 'Fake profile',
    'underage': 'Underage',
    'threats': 'Threats',
  };
  int _step = 0;
  String? _reason;
  bool _submitting = false;
  final _details = TextEditingController();

  @override
  void dispose() {
    _details.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: Text('Report · step ${_step + 1} of 2')),
      body: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_step == 0) ...[
              Wrap(
                spacing: Spacing.md,
                runSpacing: Spacing.md,
                children: [
                  for (final entry in _reasons.entries)
                    ChoiceChip(
                      label: Text(entry.value),
                      selected: _reason == entry.key,
                      onSelected: (_) => setState(() => _reason = entry.key),
                    ),
                ],
              ),
              Spacer(),
              // Continue only when a reason IS picked (was inverted — the
              // report flow could never proceed)
              FilledButton(
                onPressed: _reason == null
                    ? null
                    : () => setState(() => _step = 1),
                child: const Text('Continue'),
              ),
            ] else ...[
              TextField(
                controller: _details,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'What happened? (optional)',
                  alignLabelWithHint: true,
                ),
              ),
              const SizedBox(height: Spacing.md),
              Text(
                'Evidence upload is not available in this flow yet.',
                style: TextStyle(color: milan.ink600, fontSize: 12),
              ),
              Spacer(),
              FilledButton.icon(
                icon: Icon(Icons.send),
                label: Text(_submitting ? 'Submitting…' : 'Submit report'),
                onPressed: _submitting || _reason == null
                    ? null
                    : () async {
                        setState(() => _submitting = true);
                        try {
                          final response = await ref
                              .read(apiClientProvider)
                              .post<Map<String, dynamic>>(
                                '/safety/reports',
                                body: {
                                  'target_id': widget.targetId,
                                  'reason': _reason,
                                  'details': _details.text.trim(),
                                },
                              );
                          if (!context.mounted) return;
                          final reportId = response['id']?.toString();
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                'Report received${reportId == null ? '' : ' · $reportId'}',
                              ),
                            ),
                          );
                          context.pop();
                        } on AppException catch (e) {
                          if (mounted) {
                            setState(() => _submitting = false);
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  'Could not submit: ${e.displayMessage}',
                                ),
                              ),
                            );
                          }
                        } catch (_) {
                          if (mounted) {
                            setState(() => _submitting = false);
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text(
                                  'Could not submit the report. Try again.',
                                ),
                              ),
                            );
                          }
                        }
                      },
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Screen 56 — block list management.
class BlockListScreen extends ConsumerStatefulWidget {
  const BlockListScreen({super.key});

  @override
  ConsumerState<BlockListScreen> createState() => _BlockListScreenState();
}

class _BlockListScreenState extends ConsumerState<BlockListScreen> {
  List<Map<String, dynamic>>? _blocked;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await ref
          .read(apiClientProvider)
          .get<Map<String, dynamic>>('/safety/blocks');
      if (!mounted) return;
      setState(
        () => _blocked = (res['blocked'] as List).cast<Map<String, dynamic>>(),
      );
    } on AppException {
      if (!mounted) return;
      setState(() => _blocked = const []);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final items = _blocked ?? const <Map<String, dynamic>>[];
    return Scaffold(
      appBar: AppBar(title: const Text('Blocked users')),
      body: items.isEmpty
          ? Center(
              child: Text(
                'No one blocked.',
                style: TextStyle(color: milan.ink600),
              ),
            )
          : ListView.separated(
              padding: EdgeInsets.all(Spacing.xl),
              itemCount: items.length,
              separatorBuilder: (_, __) => Divider(color: milan.line200),
              itemBuilder: (context, i) => ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(
                  items[i]['display_name']?.toString() ??
                      (items[i]['id'] as String).substring(0, 8),
                ),
                trailing: OutlinedButton(
                  onPressed: () async {
                    await ref
                        .read(apiClientProvider)
                        .delete('/safety/blocks/${items[i]['id']}');
                    _load();
                  },
                  child: const Text('Unblock'),
                ),
              ),
            ),
    );
  }
}

/// Screen 57 — scam warning interstitial shown to the recipient.
class ScamWarningInterstitial extends StatelessWidget {
  const ScamWarningInterstitial({super.key, required this.patterns});
  final List<String> patterns;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Dialog(
      backgroundColor: milan.paper0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Spacing.radiusLg),
      ),
      child: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.warning_amber_rounded,
              size: 48,
              color: milan.warning500,
            ),
            SizedBox(height: Spacing.lg),
            Text('Be careful', style: context.h3),
            SizedBox(height: Spacing.md),
            Text(
              'This conversation shows patterns common in romance scams'
              '${patterns.isEmpty ? "" : " (${patterns.take(2).join(", ")})"}. '
              'Never send money, gift cards or bank details to anyone you met online.',
              style: TextStyle(height: 1.5, fontSize: 13),
            ),
            SizedBox(height: Spacing.xl),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Dismiss'),
                  ),
                ),
                SizedBox(width: Spacing.md),
                Expanded(
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: milan.error500,
                    ),
                    onPressed: null,
                    child: const Text('Report unavailable'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Screen 58 — panic / emergency quick action.
class PanicScreen extends StatelessWidget {
  const PanicScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Emergency')),
      body: Center(
        child: Padding(
          padding: EdgeInsets.all(Spacing.xl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: double.infinity,
                height: 120,
                child: FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: milan.error500,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(Spacing.radiusLg),
                    ),
                  ),
                  onPressed: () async {
                    final uri = Uri(scheme: 'tel', path: '100');
                    if (await canLaunchUrl(uri)) {
                      await launchUrl(uri);
                    } else {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Dial 100 from your phone app.'),
                          ),
                        );
                      }
                    }
                  },
                  child: Text(
                    'CALL 100\n(Nepal Police)',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
                  ),
                ),
              ),
              SizedBox(height: Spacing.xl),
              for (final contact in [
                ('Nepal Police', '100'),
                ('Ambulance', '102'),
                ('Women Helpline', '1677'),
              ])
                ListTile(
                  title: Text(contact.$1),
                  subtitle: Text('Free helpline — tap to call'),
                  trailing: Text(contact.$2),
                  onTap: () async {
                    final uri = Uri(scheme: 'tel', path: contact.$2);
                    if (await canLaunchUrl(uri)) await launchUrl(uri);
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Screen 59 — verification explainer.
class VerificationDetailScreen extends StatelessWidget {
  const VerificationDetailScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Verification')),
      body: ListView(
        padding: EdgeInsets.all(Spacing.xl),
        children: [
          Center(child: VerifiedBadge()),
          SizedBox(height: Spacing.lg),
          for (final (i, step) in [
            'Take a short live selfie video at signup',
            'Milan checks it matches your profile photos',
            'Your face embedding is cross-checked against other accounts to catch duplicates',
            'The selfie is discarded immediately after processing — only the result is kept',
          ].indexed)
            Padding(
              padding: EdgeInsets.only(bottom: Spacing.lg),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 14,
                    backgroundColor: milan.marigold100,
                    child: Text(
                      '${i + 1}',
                      style: TextStyle(fontSize: 12, color: milan.marigold700),
                    ),
                  ),
                  SizedBox(width: Spacing.md),
                  Expanded(
                    child: Text(step, style: const TextStyle(height: 1.45)),
                  ),
                ],
              ),
            ),
          FilledButton(
            onPressed: () => context.go('/onboarding/liveness'),
            child: const Text('Re-verify now'),
          ),
        ],
      ),
    );
  }
}
