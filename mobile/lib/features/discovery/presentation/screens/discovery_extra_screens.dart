import 'dart:ui' show ImageFilter;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../core/localization/app_localizations.dart';
import '../../../../core/network/api_client.dart';
import '../../application/discovery_provider.dart';
import '../../../../shared/widgets/common.dart' show CompatibilityMeter;

/// Screen 20 — discovery filters.
class DiscoveryFiltersScreen extends ConsumerStatefulWidget {
  const DiscoveryFiltersScreen({super.key});

  @override
  ConsumerState<DiscoveryFiltersScreen> createState() =>
      _DiscoveryFiltersScreenState();
}

class _DiscoveryFiltersScreenState
    extends ConsumerState<DiscoveryFiltersScreen> {
  RangeValues _age = const RangeValues(21, 40);
  double _distanceKm = 25;
  final _city = TextEditingController();
  bool _verifiedOnly = false;
  String _intent = 'any';
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final controller = ref.read(discoveryProvider.notifier);
      setState(() {
        _age = RangeValues(
          controller.ageMin.toDouble(),
          controller.ageMax.toDouble(),
        );
        _city.text = controller.city ?? '';
        _verifiedOnly = controller.verifiedOnly;
        _intent = controller.intent ?? 'any';
        _initialized = true;
      });
    });
  }

  @override
  void dispose() {
    _city.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Filters')),
      body: ListView(
        padding: EdgeInsets.all(Spacing.xl),
        children: [
          Text('Age', style: context.h4),
          RangeSlider(
            values: _age,
            min: 18,
            max: 60,
            divisions: 42,
            activeColor: milan.marigold500,
            labels: RangeLabels('${_age.start.round()}', '${_age.end.round()}'),
            onChanged: (v) => setState(() => _age = v),
          ),
          SizedBox(height: Spacing.xl),
          Text('Distance — ${_distanceKm.round()} km', style: context.h4),
          Slider(
            value: _distanceKm,
            min: 1,
            max: 100,
            activeColor: milan.marigold500,
            onChanged: (v) => setState(() => _distanceKm = v),
          ),
          SizedBox(height: Spacing.lg),
          TextField(
            controller: _city,
            decoration: const InputDecoration(
              labelText: 'City (e.g. Kathmandu)',
            ),
          ),
          SizedBox(height: Spacing.lg),
          Text('Intent', style: context.h4),
          Wrap(
            spacing: Spacing.md,
            children: [
              for (final intent in ['serious', 'casual', 'any'])
                FilterChip(
                  label: Text(intent),
                  selected: _intent == intent,
                  onSelected: (_) => setState(() => _intent = intent),
                ),
              FilterChip(
                label: const Text('Verified only'),
                selected: _verifiedOnly,
                onSelected: (v) => setState(() => _verifiedOnly = v),
              ),
            ],
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(Spacing.xl),
          child: FilledButton(
            onPressed: () {
              final controller = ref.read(discoveryProvider.notifier);
              controller.applyFilters(
                min: _age.start.round(),
                max: _age.end.round(),
                cityValue: _city.text.trim(),
                verified: _verifiedOnly,
                intentValue: _intent,
              );
              context.pop();
            },
            child: const Text('Apply filters'),
          ),
        ),
      ),
    );
  }
}

/// Screen 21 — Serious vs Casual mode switch.
class ModeSwitchScreen extends ConsumerWidget {
  const ModeSwitchScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final currentMode = ref.read(discoveryProvider.notifier).currentMode;
    return Scaffold(
      appBar: AppBar(),
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(Spacing.xl),
          child: Column(
            children: [
              for (final mode in [
                (
                  'Serious',
                  'For relationships your family could eventually hear about.',
                  milan.dhaka500,
                ),
                (
                  'Casual',
                  'Meeting people, low pressure, no timeline.',
                  milan.pine500,
                ),
              ])
                Padding(
                  padding: EdgeInsets.only(bottom: Spacing.lg),
                  child: Card(
                    elevation: 0,
                    color: Theme.of(
                      context,
                    ).colorScheme.surfaceContainerHighest,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(Spacing.radiusLg),
                    ),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(Spacing.radiusLg),
                      onTap: () {
                        // persist server-side (mode rides every candidates call)
                        ref
                            .read(discoveryProvider.notifier)
                            .setMode(mode.$1.toLowerCase());
                        Navigator.pop(context);
                      },
                      child: Padding(
                        padding: EdgeInsets.all(Spacing.xl),
                        child: Row(
                          children: [
                            Icon(Icons.favorite_outline, color: mode.$3),
                            SizedBox(width: Spacing.lg),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(mode.$1, style: context.h3),
                                  Text(
                                    mode.$2,
                                    style: TextStyle(
                                      fontSize: 12.5,
                                      color: milan.ink600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Screens 22+23 — match celebration → detail via `celebration=true`.
class MatchDetailScreen extends ConsumerStatefulWidget {
  const MatchDetailScreen({
    super.key,
    required this.matchId,
    this.showCelebration = false,
  });
  final String matchId;
  final bool showCelebration;

  @override
  ConsumerState<MatchDetailScreen> createState() => _MatchDetailScreenState();
}

class _MatchDetailScreenState extends ConsumerState<MatchDetailScreen> {
  bool _celebrating = true;
  Map<String, dynamic>? _match;

  @override
  void initState() {
    super.initState();
    if (!widget.showCelebration) _celebrating = false;
    Future.delayed(const Duration(milliseconds: 900), () {
      if (mounted) setState(() => _celebrating = false);
    });
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await ref
          .read(apiClientProvider)
          .get<Map<String, dynamic>>('/matches');
      final found = ((res['matches'] as List).cast<Map<String, dynamic>>())
          .firstWhere((m) => m['id'] == widget.matchId, orElse: () => {});
      if (mounted && found.isNotEmpty) setState(() => _match = found);
    } on AppException {
      // detail stays generic on failure
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final score = ((_match?['compatibility_score'] as num?) ?? 72).round();
    final otherUserId = _match?['other_user_id'] as String?;
    return Scaffold(
      appBar: AppBar(
        actions: [
          IconButton(
            icon: const Icon(Icons.flag_outlined),
            onPressed: otherUserId == null || otherUserId.isEmpty
                ? null
                : () => context.push('/safety/report/$otherUserId'),
            tooltip: otherUserId == null || otherUserId.isEmpty
                ? 'Report unavailable'
                : 'Report',
          ),
        ],
      ),
      body: Stack(
        children: [
          Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircleAvatar(radius: 44, child: Icon(Icons.person, size: 40)),
                SizedBox(height: Spacing.lg),
                Text(
                  _match?['user']?['display_name'] ?? 'Your match',
                  style: context.h2,
                ),
                SizedBox(height: Spacing.xl),
                CompatibilityMeter(score: score, label: 'compatibility'),
                SizedBox(height: Spacing.xl),
                Container(
                  margin: EdgeInsets.symmetric(horizontal: Spacing.xl),
                  padding: EdgeInsets.all(Spacing.lg),
                  decoration: BoxDecoration(
                    color: milan.paper100,
                    borderRadius: BorderRadius.circular(Spacing.radiusMd),
                  ),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.auto_awesome, size: 16, color: milan.dhaka500),
                      SizedBox(width: Spacing.sm),
                      Expanded(
                        child: Text(
                          _match?['match_reason_text'] ??
                              'You share interests worth talking about.',
                          style: TextStyle(height: 1.4),
                        ),
                      ),
                    ],
                  ),
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: Padding(
                    padding: EdgeInsets.only(
                      top: Spacing.sm,
                      left: Spacing.xxxl,
                    ),
                    child: Text(
                      'AI-generated · grounded in shared profile signal',
                      style: TextStyle(fontSize: 10, color: milan.ink400),
                    ),
                  ),
                ),
                Spacer(),
                SafeArea(
                  child: Padding(
                    padding: EdgeInsets.all(Spacing.xl),
                    child: Column(
                      children: [
                        FilledButton(
                          onPressed: () =>
                              context.push('/chat/${widget.matchId}'),
                          child: const Text('Say something'),
                        ),
                        SizedBox(height: Spacing.md),
                        OutlinedButton(
                          onPressed: () => context.push(
                            '/discover/kundali/${widget.matchId}',
                          ),
                          child: const Text('Try Kundali Mode'),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (_celebrating)
            // Marigold-petal confetti burst, ≤900ms, tap to skip (doc 2 §2.4).
            GestureDetector(
              onTap: () => setState(() => _celebrating = false),
              child: Container(
                color: milan.dhaka500.withValues(alpha: .92),
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        "It's a match!",
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 34,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      SizedBox(height: Spacing.md),
                      Text(
                        'मिल्यो!',
                        style: TextStyle(
                          color: milan.marigold100,
                          fontSize: 22,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Screen 24 — Kundali Mode; culturally framed, clearly not science.
class KundaliScreen extends ConsumerStatefulWidget {
  const KundaliScreen({super.key, required this.matchId});
  final String matchId;

  @override
  ConsumerState<KundaliScreen> createState() => _KundaliScreenState();
}

class _KundaliScreenState extends ConsumerState<KundaliScreen> {
  final _birthDate = TextEditingController();
  final _birthTime = TextEditingController(text: '06:30');
  final _birthPlace = TextEditingController();
  String? _narrative;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _birthDate.dispose();
    _birthTime.dispose();
    _birthPlace.dispose();
    super.dispose();
  }

  Future<void> _saveAndFetch() async {
    if (_birthDate.text.isEmpty) {
      setState(() => _error = 'Add your birth date first.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      // PUT /profile/me only accepts `horoscope_details` (profile allow-list);
      // a bare horoscope_opt_in flag is dropped and kundali would 422 with
      // horoscope_details_missing forever (P0-5).
      final place = _birthPlace.text.trim();
      await ref
          .read(apiClientProvider)
          .put(
            '/profile/me',
            body: {
              'horoscope_details': {
                'opt_in': true,
                'birth_date': _birthDate.text.trim(),
                'birth_time': _birthTime.text.trim(),
                if (place.isNotEmpty) 'birth_place': place,
              },
            },
          );
      final res = await ref
          .read(apiClientProvider)
          .get<Map<String, dynamic>>('/discovery/kundali/${widget.matchId}');
      setState(() => _narrative = res['narrative'] as String?);
    } on AppException catch (e) {
      setState(
        () => _error = e.code == 'horoscope_details_missing'
            ? 'Both of you need to add birth details for a kundali read.'
            : e.code == 'ai_unavailable_try_later'
            ? "Milan's AI is taking a breather."
            : e.message == null || e.message!.isEmpty
            ? e.code
            : '${e.code} — ${e.message}',
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(
        title: Text(AppLocalizations.of(context)!.discoverKundaliMode),
      ),
      body: ListView(
        padding: EdgeInsets.all(Spacing.xl),
        children: [
          Container(
            padding: EdgeInsets.all(Spacing.lg),
            decoration: BoxDecoration(
              color: milan.marigold100,
              borderRadius: BorderRadius.circular(Spacing.radiusMd),
            ),
            child: Row(
              children: [
                Icon(Icons.info_outline, size: 18, color: milan.marigold700),
                SizedBox(width: Spacing.sm),
                Expanded(
                  child: Text(
                    AppLocalizations.of(context)!.kundaliDisclaimer,
                    style: TextStyle(fontSize: 12, height: 1.4),
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: Spacing.xl),
          if (_narrative == null) ...[
            TextField(
              controller: _birthDate,
              readOnly: true,
              decoration: InputDecoration(
                labelText: 'Your birth date',
                suffixIcon: Icon(Icons.calendar_month),
                border: OutlineInputBorder(),
              ),
              onTap: () async {
                final picked = await showDatePicker(
                  context: context,
                  firstDate: DateTime(1940),
                  lastDate: DateTime.now(),
                );
                if (picked != null) {
                  _birthDate.text = picked.toIso8601String().split('T').first;
                }
              },
            ),
            SizedBox(height: Spacing.lg),
            TextField(
              controller: _birthTime,
              decoration: const InputDecoration(
                labelText: 'Birth time (approx ok)',
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: Spacing.lg),
            TextField(
              controller: _birthPlace,
              decoration: const InputDecoration(
                labelText: 'Birth place (e.g. Kathmandu)',
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: Spacing.xl),
            FilledButton.icon(
              icon: Icon(Icons.auto_stories),
              label: Text(
                _busy ? 'Reading the stars…' : 'Generate kundali narrative',
              ),
              onPressed: _busy ? null : _saveAndFetch,
            ),
            if (_error != null)
              Padding(
                padding: EdgeInsets.only(top: Spacing.md),
                child: Text(_error!, style: TextStyle(color: milan.error500)),
              ),
          ] else ...[
            Container(
              padding: EdgeInsets.all(Spacing.xl),
              decoration: BoxDecoration(
                color: milan.paper100,
                borderRadius: BorderRadius.circular(Spacing.radiusLg),
              ),
              child: Text(_narrative!, style: const TextStyle(height: 1.55)),
            ),
            Padding(
              padding: EdgeInsets.only(top: Spacing.sm),
              child: Text(
                'AI-generated cultural reading · for fun',
                style: TextStyle(fontSize: 10, color: milan.ink400),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// Screen 25 — who liked you (paywalled blurred grid).
class WhoLikedYouScreen extends ConsumerStatefulWidget {
  const WhoLikedYouScreen({super.key});

  @override
  ConsumerState<WhoLikedYouScreen> createState() => _WhoLikedYouScreenState();
}

class _WhoLikedYouScreenState extends ConsumerState<WhoLikedYouScreen> {
  Map<String, dynamic>? _data;
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
      final res = await ref
          .read(apiClientProvider)
          .get<Map<String, dynamic>>('/discovery/likes-received');
      if (!mounted) return;
      setState(() {
        _data = res;
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

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Who liked you')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _error!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 13),
                  ),
                  SizedBox(height: Spacing.md),
                  FilledButton(onPressed: _load, child: const Text('Retry')),
                ],
              ),
            )
          : (_data?['count'] as int? ?? 0) == 0
          ? Center(
              child: Text(
                'No likes yet — keep swiping!',
                style: TextStyle(color: milan.ink600),
              ),
            )
          // §A4.9 revised: the first five likers are free for
          // everyone; the rest render as locked teasers.
          : ListView(
              padding: EdgeInsets.all(Spacing.xl),
              children: [
                Text('${_data!['count']} people like you', style: context.h3),
                SizedBox(height: Spacing.sm),
                Text(
                  (_data!['premium'] as bool? ?? false) ||
                          (_data!['likes'] as List).length <=
                              (_data!['free_visible'] as int? ?? 5)
                      ? 'Like back any of them to match instantly.'
                      : 'First ${_data!['free_visible']} are free — get a pass to see the rest.',
                  style: TextStyle(fontSize: 13, color: milan.ink600),
                ),
                SizedBox(height: Spacing.md),
                for (final like in (_data!['likes'] as List))
                  _LikerRow(like: like as Map<String, dynamic>),
              ],
            ),
    );
  }
}

class _LikerRow extends StatelessWidget {
  const _LikerRow({required this.like});
  final Map<String, dynamic> like;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final locked = like['locked'] as bool? ?? false;
    final photo = like['photo_url'] as String?;
    final name = like['display_name'] as String?;
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: locked
          ? Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: milan.paper100,
                shape: BoxShape.circle,
              ),
              child: Icon(Icons.lock_rounded, size: 20, color: milan.ink400),
            )
          : CircleAvatar(
              radius: 26,
              backgroundImage: photo != null
                  ? CachedNetworkImageProvider(photo)
                  : null,
              child: photo == null ? const Icon(Icons.person) : null,
            ),
      title: locked
          ? Text('Someone liked you', style: TextStyle(color: milan.ink600))
          : Text(
              (name ?? 'Someone') + ((like['superlike'] ?? false) ? ' ⭐' : ''),
            ),
      subtitle: locked
          ? Text('Unlock with a pass', style: TextStyle(fontSize: 12))
          : ((like['note'] as String?)?.isNotEmpty ?? false
                ? Text(like['note'] as String)
                : null),
      trailing: locked
          ? const Icon(Icons.chevron_right)
          : Icon(Icons.favorite, size: 18, color: milan.dhaka500),
      onTap: () => locked
          ? context.push('/settings/subscription')
          : context.push('/profile/${like['id']}/public'),
    );
  }
}

class BoostScreen extends StatelessWidget {
  const BoostScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final packages = [
      ('30 min', 'NPR 120'),
      ('3 hrs', 'NPR 280'),
      ('12 hrs', 'NPR 650'),
    ];
    return Scaffold(
      appBar: AppBar(title: const Text('Boost')),
      body: ListView(
        padding: EdgeInsets.all(Spacing.xl),
        children: [
          Icon(
            Icons.rocket_launch_outlined,
            size: 56,
            color: milan.marigold500,
          ),
          SizedBox(height: Spacing.lg),
          Text(
            'Be one of the top profiles in your area for a burst of time.',
            textAlign: TextAlign.center,
            style: TextStyle(color: milan.ink600, height: 1.45),
          ),
          SizedBox(height: Spacing.xxl),
          for (final (dur, price) in packages)
            Card(
              margin: EdgeInsets.only(bottom: Spacing.lg),
              elevation: 0,
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(Spacing.radiusMd),
              ),
              child: ListTile(
                title: Text(dur),
                trailing: Text(
                  price,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(Spacing.radiusMd),
                ),
                onTap: () {},
              ),
            ),
          OutlinedButton.icon(
            icon: Icon(Icons.payment),
            label: const Text('Pay with eSewa / Khalti / Fonepay'),
            onPressed: () {},
          ),
        ],
      ),
    );
  }
}
