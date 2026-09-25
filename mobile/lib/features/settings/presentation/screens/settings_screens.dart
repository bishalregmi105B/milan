import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../../app/settings/a11y_settings.dart';
import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../core/feedback/sfx.dart';
import '../../../../core/localization/app_localizations.dart';
import '../../../../core/network/api_client.dart';

/// Doc 2 §2.6 — category label + toggle + frequency stepper.
class NotificationPreferenceRow extends StatefulWidget {
  const NotificationPreferenceRow({
    super.key,
    required this.category,
    required this.enabled,
    required this.maxPerDay,
    required this.onChanged,
  });
  final String category;
  final bool enabled;
  final int maxPerDay;
  final void Function(bool enabled, int maxPerDay) onChanged;

  @override
  State<NotificationPreferenceRow> createState() => _NotificationPreferenceRowState();
}

class _NotificationPreferenceRowState extends State<NotificationPreferenceRow> {
  late bool _enabled = widget.enabled;
  late int _cap = widget.maxPerDay;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Padding(padding: EdgeInsets.symmetric(vertical: Spacing.md),
        child: Row(children: [
          Expanded(child: Text(widget.category,
              style: TextStyle(color: _enabled ? milan.ink900 : milan.ink400))),
          IconButton(icon: Icon(Icons.remove_circle_outline, size: 20),
              onPressed: _enabled && _cap > 0
                  ? () { setState(() => _cap--); widget.onChanged(_enabled, _cap); }
                  : null),
          Text('$_cap/day', style: TextStyle(fontSize: 12, color: milan.ink600)),
          IconButton(icon: Icon(Icons.add_circle_outline, size: 20),
              onPressed: _enabled
                  ? () { setState(() => _cap++); widget.onChanged(_enabled, _cap); }
                  : null),
          Switch(value: _enabled, activeColor: milan.marigold500, onChanged: (v) {
            setState(() => _enabled = v);
            widget.onChanged(v, _cap);
          }),
        ]));
  }
}

/// Screen 60 — in-app notification feed grouped by category.
class NotificationCenterScreen extends ConsumerWidget {
  const NotificationCenterScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications'), actions: [
        TextButton(onPressed: () {}, child: const Text('Mark all read')),
      ]),
      body: FutureBuilder<Map<String, dynamic>>(
        future: ref.read(apiClientProvider).get('/notifications/feed'),
        builder: (context, snap) {
          final items = ((snap.data?['notifications'] as List?) ?? []).cast<Map<String, dynamic>>();
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (items.isEmpty) {
            return Center(child: Text('Nothing yet.', style:
                TextStyle(color: Theme.of(context).extension<MilanColors>()!.ink600)));
          }
          final byCategory = <String, List<Map<String, dynamic>>>{};
          for (final n in items) {
            byCategory.putIfAbsent(n['category'] as String? ?? 'other', () => []).add(n);
          }
          return ListView(padding: EdgeInsets.all(Spacing.xl), children: [
            for (final entry in byCategory.entries) ...[
              Text(entry.key.toUpperCase(),
                  style: TextStyle(fontSize: 11, letterSpacing: .04, color: milanOf(context).ink400)),
              for (final n in entry.value)
                ListTile(contentPadding: EdgeInsets.zero,
                    leading: Icon(Icons.circle_notifications_outlined),
                    title: Text(n['title'] ?? ''),
                    subtitle: Text(n['body'] ?? '', maxLines: 1, overflow: TextOverflow.ellipsis)),
              SizedBox(height: Spacing.lg),
            ],
          ]);
        },
      ),
    );
  }
}

MilanColors milanOf(BuildContext context) =>
    Theme.of(context).extension<MilanColors>()!;

/// Screen 61 — per-category control with caps.
class NotificationPreferencesScreen extends ConsumerStatefulWidget {
  const NotificationPreferencesScreen({super.key});

  @override
  ConsumerState<NotificationPreferencesScreen> createState() =>
      _NotificationPreferencesScreenState();
}

class _NotificationPreferencesScreenState
    extends ConsumerState<NotificationPreferencesScreen> {
  Map<String, dynamic>? _prefs;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await ref.read(apiClientProvider).get<Map<String, dynamic>>(
          '/notifications/preferences');
      if (!mounted) return;
      setState(() {
        _prefs = res;
        _loading = false;
      });
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.displayMessage;
      });
    }
  }

  Future<void> _update(String category, bool enabled, int cap) async {
    try {
      await ref.read(apiClientProvider).put('/notifications/preferences', body: {
        'preferences': [{'category': category, 'enabled': enabled, 'max_per_day': cap}],
      });
    } on AppException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not save: ${e.displayMessage}')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final entries = (( _prefs?['preferences'] as List?) ?? <dynamic>[]).cast<Map<String, dynamic>>();
    return Scaffold(
      appBar: AppBar(title: const Text('Notification preferences')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Text(_error!, textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 13)),
                  SizedBox(height: Spacing.md),
                  FilledButton(onPressed: _load, child: const Text('Retry')),
                ]))
              : entries.isEmpty
                  ? const Center(child: Text('No preference categories.'))
                  : ListView(padding: EdgeInsets.all(Spacing.xl), children: [
              for (final pref in entries)
                NotificationPreferenceRow(
                  key: ValueKey(pref['category']),
                  category: pref['category'].toString(),
                  enabled: pref['enabled'] as bool? ?? true,
                  maxPerDay: pref['max_per_day'] as int? ?? 3,
                  onChanged: (enabled, cap) => _update(pref['category'].toString(), enabled, cap),
                ),
              Padding(padding: EdgeInsets.only(top: Spacing.lg),
                  child: Text('Saathi proactive messages also respect these caps.',
                      style: TextStyle(fontSize: 12, color: milanOf(context).ink400))),
            ]),
    );
  }
}

/// Screen 62 — account management.
class AccountSettingsScreen extends StatelessWidget {
  const AccountSettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Account')),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.email_outlined),
            title: const Text('Change email'), trailing: const Icon(Icons.chevron_right),
            onTap: () {}),
        ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.phone_outlined),
            title: const Text('Change phone'), trailing: const Icon(Icons.chevron_right),
            onTap: () {}),
        ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.download_outlined),
            title: const Text('Export my data'), onTap: () {}),
        Divider(color: milan.line200),
        ListTile(contentPadding: EdgeInsets.zero,
            leading: Icon(Icons.delete_forever_outlined, color: milan.error500),
            title: Text('Delete account', style: TextStyle(color: milan.error500)),
            onTap: () => showDialog<void>(
                context: context,
                builder: (_) => AlertDialog(
                    title: const Text('Delete account?'),
                    content: const Text(
                        'This permanently removes your profile, matches and messages.'),
                    actions: [
                      TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text('Cancel')),
                    ]),
              ),
            ),
      ]),
    );
  }
}

/// Screen 63 — language, text size, reduced motion.
class LanguageAccessibilityScreen extends ConsumerWidget {
  const LanguageAccessibilityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final a11y = ref.watch(a11yProvider);
    return Scaffold(
      appBar: AppBar(title: Text(AppLocalizations.of(context)!.settingsLanguage)),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        Text('App language', style: context.h4),
        SizedBox(height: Spacing.sm),
        Wrap(spacing: Spacing.md, children: [
          ChoiceChip(
              label: const Text('System'),
              selected: a11y.languageCode == 'system',
              onSelected: (_) =>
                  ref.read(a11yProvider.notifier).setLanguage('system')),
          ChoiceChip(
              label: const Text('English'),
              selected: a11y.languageCode == 'en',
              onSelected: (_) => ref.read(a11yProvider.notifier).setLanguage('en')),
          ChoiceChip(
              label: const Text('नेपाली'),
              selected: a11y.languageCode == 'ne',
              onSelected: (_) => ref.read(a11yProvider.notifier).setLanguage('ne')),
        ]),
        SizedBox(height: Spacing.xl),
        Text('Chat text size — ${(a11y.textScale * 100).round()}%', style: context.h4),
        Slider(
            value: a11y.textScale,
            min: .8,
            max: 1.4,
            divisions: 4,
            label: '${(a11y.textScale * 100).round()}%',
            activeColor: milan.marigold500,
            onChanged: (v) => ref.read(a11yProvider.notifier).setTextScale(v)),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Reduce motion'),
            subtitle: Text(
                'Replaces swipe springs and wallpaper crossfades with fades.',
                style: TextStyle(fontSize: 12)),
            value: a11y.reduceMotion,
            onChanged: (v) => ref.read(a11yProvider.notifier).setReduceMotion(v)),
        SizedBox(height: Spacing.xl),
        // doc 8 §A3.7: the sound/haptics toggles were persisted but had no
        // UI anywhere — the settings surface finally exposes them.
        Text('Sounds & vibration', style: context.h4),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Sounds'),
            subtitle: Text('Send, receive, match and swipe sounds.',
                style: TextStyle(fontSize: 12)),
            value: ref.watch(sfxProvider).soundOn,
            onChanged: (v) => ref.read(sfxProvider.notifier).setSound(v)),
        SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Haptics'),
            subtitle: Text('Vibration feedback for the same moments.',
                style: TextStyle(fontSize: 12)),
            value: ref.watch(sfxProvider).hapticsOn,
            onChanged: (v) => ref.read(sfxProvider.notifier).setHaptics(v)),
        SizedBox(height: Spacing.lg),
        Text('Changes apply instantly across the whole app and are saved on this device.',
            style: TextStyle(fontSize: 12, color: milan.ink400)),
      ]),
    );
  }
}

/// Screen 64 — payment methods (eSewa/Khalti/Fonepay/ConnectIPS).
class PaymentMethodsScreen extends StatelessWidget {
  const PaymentMethodsScreen({super.key});

  static const _providers = [('eSewa', Icons.account_balance_wallet_outlined),
      ('Khalti', Icons.payment_outlined), ('Fonepay', Icons.qr_code_2),
      ('ConnectIPS', Icons.account_balance)];

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: Text(AppLocalizations.of(context)!.settingsPaymentMethods)),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        for (final provider in _providers)
          Card(margin: EdgeInsets.only(bottom: Spacing.md), elevation: 0,
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Spacing.radiusMd)),
              child: ListTile(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Spacing.radiusMd)),
                  leading: Icon(provider.$2, color: milan.dhaka500),
                  title: Text(provider.$1),
                  trailing: const Text('Coming soon',
                      style: TextStyle(fontSize: 12, color: Colors.grey)))),
        Padding(padding: EdgeInsets.only(top: Spacing.lg),
            child: Text('Wallets link automatically after merchant onboarding — for now, passes are paid by scanning a QR in Subscription Plans.',
                style: TextStyle(fontSize: 12, color: milan.ink400))),
      ]),
    );
  }
}

/// Screen 65 — NPR tier comparison + REAL Phase-1 payment flow: pick a tier →
/// pay via the wallet's own app by scanning the admin's QR → submit the
/// transaction reference + screenshot → entitlement unlocks ONLY after human
/// verification (no fake success states — every button does a real API call).
class SubscriptionPlansScreen extends ConsumerStatefulWidget {
  const SubscriptionPlansScreen({super.key});

  @override
  ConsumerState<SubscriptionPlansScreen> createState() =>
      _SubscriptionPlansScreenState();
}

class _SubscriptionPlansScreenState
    extends ConsumerState<SubscriptionPlansScreen> {
  static const tiers = [
    ('basic', 'Basic', 'NPR 299', ['See who liked you (count)', '50 likes/day', '1 AI companion']),
    ('plus', 'Plus', 'NPR 699', ['Unlimited likes & rewind', 'Monthly boost', '4 AI companions']),
    ('premium', 'Premium', 'NPR 1,299', ['Everything in Plus', '8 companions & voice', '25 rewinds + priority']),
  ];
  static const _methods = [
    ('esewa', 'eSewa', Icons.account_balance_wallet_outlined),
    ('khalti', 'Khalti', Icons.payment_outlined),
    ('fonepay', 'Fonepay', Icons.qr_code_2),
    ('connectips', 'Connect IPS', Icons.account_balance),
  ];

  String? _selectedTier;
  String? _selectedMethod;
  final _referenceController = TextEditingController();
  final _noteController = TextEditingController();
  String? _screenshotUrl;
  bool _submitting = false;
  List<Map<String, dynamic>> _mySubmissions = const [];
  Map<String, dynamic>? _activeQr;

  @override
  void initState() {
    super.initState();
    _loadMine();
  }

  @override
  void dispose() {
    _referenceController.dispose();
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _loadMine() async {
    try {
      final res = await ref
          .read(apiClientProvider)
          .get<Map<String, dynamic>>('/billing/submissions/mine');
      if (!mounted) return;
      setState(() =>
          _mySubmissions = (res['submissions'] as List).cast<Map<String, dynamic>>());
    } on AppException {
      // submissions list is best-effort; the checkout itself still works
    }
  }

  Future<void> _loadQr(String method) async {
    try {
      final res = await ref
          .read(apiClientProvider)
          .get<Map<String, dynamic>>('/billing/qr/$method');
      if (!mounted) return;
      setState(() => _activeQr = res);
    } on AppException {
      if (!mounted) return;
      setState(() => _activeQr = {'configured': false, 'method': method});
    }
  }

  Future<void> _pickScreenshot() async {
    final picker = ImagePicker();
    final picked = await picker.pickImage(source: ImageSource.gallery, imageQuality: 85);
    if (picked == null) return;
    if (!mounted) return;
    setState(() => _submitting = true);
    try {
      final res = await ref.read(apiClientProvider).uploadMultipart(
            '/media/upload?kind=photo',
            filePath: picked.path,
            field: 'file',
          );
      if (!mounted) return;
      setState(() => _screenshotUrl = res['url'] as String?);
    } on AppException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Screenshot upload failed: ${e.displayMessage}')));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  String _priceFor(String? tier) {
    for (final (id, _, price, _) in tiers) {
      if (id == (tier ?? 'plus')) return price;
    }
    return 'NPR 699';
  }

  Future<void> _submitProof() async {
    final tier = _selectedTier;
    final method = _selectedMethod;
    final reference = _referenceController.text.trim();
    if (tier == null || method == null || reference.isEmpty) return;
    setState(() => _submitting = true);
    try {
      final res = await ref.read(apiClientProvider).post<Map<String, dynamic>>(
          '/billing/submissions',
          body: {
            'tier': tier,
            'method': method,
            'reference_id': reference,
            if (_screenshotUrl != null) 'screenshot_url': _screenshotUrl,
            if (_noteController.text.trim().isNotEmpty) 'note': _noteController.text.trim(),
          });
      if (!mounted) return;
      final flags = (res['fraud_flags'] as List?) ?? const [];
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(flags.isEmpty
            ? (res['message'] as String? ?? 'Payment under review.')
            : 'Submitted, but our team will look carefully: ${flags.join(", ")}'),
      ));
      setState(() {
        _referenceController.clear();
        _noteController.clear();
        _screenshotUrl = null;
      });
      _loadMine();
    } on AppException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.displayMessage)));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: Text(AppLocalizations.of(context)!.settingsSubscription)),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        if (_mySubmissions.any((s) => s['status'] == 'pending'))
          Container(margin: EdgeInsets.only(bottom: Spacing.lg), padding: EdgeInsets.all(Spacing.lg),
              decoration: BoxDecoration(color: milan.paper100,
                  borderRadius: BorderRadius.circular(Spacing.radiusMd),
                  border: Border.all(color: milan.marigold500)),
              child: Row(children: [
                Icon(Icons.hourglass_top, color: milan.marigold500),
                SizedBox(width: Spacing.md),
                Expanded(child: Text(
                    'A payment is under review. Your pass unlocks as soon as it is verified.',
                    style: TextStyle(fontSize: 13))),
              ])),
        for (final (id, name, price, features) in tiers)
          GestureDetector(
            onTap: () => setState(() => _selectedTier = id),
            child: Container(margin: EdgeInsets.only(bottom: Spacing.lg), padding: EdgeInsets.all(Spacing.xl),
                decoration: BoxDecoration(
                  color: _selectedTier == id ? milan.dhaka500 : Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(Spacing.radiusLg),
                  border: _selectedTier == id
                      ? Border.all(color: milan.marigold500, width: 2)
                      : null,
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                    Text(name, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 18,
                        color: _selectedTier == id ? Colors.white : null)),
                    Text(price, style: TextStyle(fontWeight: FontWeight.w700,
                        color: _selectedTier == id ? milan.marigold100 : milan.dhaka500)),
                  ]),
                  SizedBox(height: Spacing.md),
                  for (final f in features)
                    Padding(padding: EdgeInsets.only(bottom: Spacing.sm),
                        child: Text('✓ $f', style: TextStyle(fontSize: 13,
                            color: _selectedTier == id ? Colors.white70 : milan.ink600))),
                ])),
          ),
        const Text('How it works: scan the QR with your wallet app, pay, then submit the transaction ID + a screenshot. Milan verifies manually (usually within 12 hours) — your pass unlocks right after.',
            style: TextStyle(fontSize: 12)),
        SizedBox(height: Spacing.lg),
        Text('1. Choose payment method', style: TextStyle(fontWeight: FontWeight.w700)),
        SizedBox(height: Spacing.sm),
        Wrap(spacing: Spacing.md, runSpacing: Spacing.sm, children: [
          for (final (id, label, icon) in _methods)
            ChoiceChip(
              avatar: Icon(icon, size: 16),
              label: Text(label),
              selected: _selectedMethod == id,
              onSelected: (_) {
                setState(() => _selectedMethod = id);
                _loadQr(id);
              },
            ),
        ]),
        if (_activeQr != null) ...[
          SizedBox(height: Spacing.lg),
          Text('2. Pay ${_priceFor(_selectedTier)} by scanning',
              style: TextStyle(fontWeight: FontWeight.w700)),
          SizedBox(height: Spacing.sm),
          if (_activeQr!['configured'] == true)
            Container(
              padding: EdgeInsets.all(Spacing.lg),
              decoration: BoxDecoration(color: milan.paper100,
                  borderRadius: BorderRadius.circular(Spacing.radiusMd)),
              child: Column(children: [
                if ((_activeQr!['image_url'] as String?)?.isNotEmpty ?? false)
                  ConstrainedBox(constraints: const BoxConstraints(maxWidth: 220),
                      child: Image.network(_activeQr!['image_url'] as String)),
                SizedBox(height: Spacing.sm),
                if (_activeQr!['account_label'] != null)
                  Text(_activeQr!['account_label'] as String, style: const TextStyle(fontWeight: FontWeight.w600)),
                if (_activeQr!['instructions'] != null)
                  Padding(padding: EdgeInsets.only(top: Spacing.sm),
                      child: Text(_activeQr!['instructions'] as String,
                          style: TextStyle(fontSize: 12, color: milan.ink600))),
              ]),
            )
          else
            Text('No QR configured for this method yet — pick another, or contact support.',
                style: TextStyle(fontSize: 13, color: milan.error500)),
          SizedBox(height: Spacing.lg),
          Text('3. Submit your payment proof', style: TextStyle(fontWeight: FontWeight.w700)),
          SizedBox(height: Spacing.sm),
          // onChanged rebuild is what activates the submit button — without
          // it the enabled condition only re-evaluated on the next setState
          // from another widget, so the button looked dead (§payment fix).
          TextField(controller: _referenceController,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                  labelText: 'Transaction / reference ID from your wallet app')),
          SizedBox(height: Spacing.sm),
          OutlinedButton.icon(
              icon: Icon(_screenshotUrl == null ? Icons.upload_outlined : Icons.check_circle),
              label: Text(_screenshotUrl == null ? 'Attach payment screenshot' : 'Screenshot attached ✓'),
              onPressed: _submitting ? null : _pickScreenshot),
          SizedBox(height: Spacing.sm),
          TextField(controller: _noteController,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Note for the team (optional)')),
          SizedBox(height: Spacing.lg),
          FilledButton(
              onPressed: (_selectedTier != null &&
                      _selectedMethod != null &&
                      _referenceController.text.trim().isNotEmpty &&
                      !_submitting)
                  ? _submitProof
                  : null,
              child: Text(_submitting ? 'Submitting…' : 'Submit for verification')),
        ],
        SizedBox(height: Spacing.xl),
      ]),
    );
  }
}

/// Screen 66 — searchable FAQ + support CTA.
class HelpFaqScreen extends ConsumerStatefulWidget {
  const HelpFaqScreen({super.key});

  static const faqs = [
    ('How does verification work?', 'A live selfie is checked against your photos and discarded right after.'),
    ('Is Saathi a real person?', 'No — Saathi is clearly-labeled AI for practice only.'),
    ('How do I stay safe meeting up?', "Use Share My Date and meet in public places first."),
    ('What do boosts do?', 'They place your profile near the top of nearby decks temporarily.'),
  ];

  @override
  ConsumerState<HelpFaqScreen> createState() => _HelpFaqScreenState();
}

class _HelpFaqScreenState extends ConsumerState<HelpFaqScreen> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final results = HelpFaqScreen.faqs.where((f) =>
        f.$1.toLowerCase().contains(_query) || f.$2.toLowerCase().contains(_query)).toList();
    return Scaffold(
      appBar: AppBar(title: Text(AppLocalizations.of(context)!.settingsHelp)),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        TextField(onChanged: (v) => setState(() => _query = v.toLowerCase()),
            decoration: const InputDecoration(prefixIcon: Icon(Icons.search),
                hintText: 'Search help topics')),
        for (final faq in results)
          ExpansionTile(
              tilePadding: EdgeInsets.zero,
              title: Text(faq.$1, style: const TextStyle(fontWeight: FontWeight.w600)),
              children: [Align(alignment: Alignment.centerLeft,
                  child: Padding(padding: EdgeInsets.only(bottom: Spacing.lg),
                      child: Text(faq.$2, style: const TextStyle(height: 1.45))))]),
        SizedBox(height: Spacing.xl),
        OutlinedButton.icon(icon: Icon(Icons.support_agent_outlined),
            label: const Text('Contact support'),
            onPressed: () {}),
      ]),
    );
  }
}
