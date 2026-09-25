import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/common.dart' show VerifiedBadge;

/// "View my profile as others see it" — the full-profile card a match sees
/// when they swipe up, rendered from the SAME `/profile/me` data the user
/// filled during signup. Fully dynamic: photos, bio, interests, prompts,
/// languages, verification, city. Nothing static.
class MyProfileViewScreen extends ConsumerStatefulWidget {
  const MyProfileViewScreen({super.key});

  @override
  ConsumerState<MyProfileViewScreen> createState() => _MyProfileViewScreenState();
}

class _MyProfileViewScreenState extends ConsumerState<MyProfileViewScreen> {
  Map<String, dynamic>? _me;
  bool _loading = true;
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _failed = false;
    });
    try {
      final res =
          await ref.read(apiClientProvider).get<Map<String, dynamic>>('/profile/me');
      if (!mounted) return;
      setState(() {
        _me = res;
        _loading = false;
      });
    } on AppException {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _failed = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      backgroundColor: milan.paper0,
      appBar: AppBar(title: const Text('How others see you')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _failed || _me == null
              ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Text('Could not load your profile.',
                      style: TextStyle(color: milan.ink600)),
                  SizedBox(height: Spacing.md),
                  FilledButton(onPressed: _load, child: const Text('Retry')),
                ]))
              : _buildBody(_me!, milan),
    );
  }

  Widget _buildBody(Map<String, dynamic> me, MilanColors milan) {
    final user = (me['user'] ?? {}) as Map<String, dynamic>;
    final profile = (me['profile'] ?? {}) as Map<String, dynamic>;
    final name = (profile['display_name'] as String?) ?? 'Milan user';
    final isVerified = (user['is_verified'] as bool?) ?? false;
    final city = profile['city'] as String?;
    final bio = profile['bio'] as String?;
    final interests = ((profile['interests'] as List?) ?? const [])
        .map((e) => e.toString())
        .where((e) => e.isNotEmpty)
        .toList();
    final languages = ((profile['languages'] as List?) ?? const [])
        .map((e) => (e as Map<String, dynamic>)['label'] as String? ?? '')
        .where((l) => l.isNotEmpty)
        .toList();
    final prompts = ((profile['prompts'] as List?) ?? const [])
        .cast<Map<String, dynamic>>();
    final photos = ((profile['photos'] as List?) ?? const [])
        .map((p) => (p as Map<String, dynamic>)['url'] as String? ?? '')
        .where((u) => u.isNotEmpty)
        .toList();

    return ListView(padding: EdgeInsets.all(Spacing.xl), children: [
      // photo gallery — swipeable like a discovery card
      if (photos.isNotEmpty)
        SizedBox(
          height: 420,
          child: PageView.builder(
            itemCount: photos.length,
            itemBuilder: (context, i) => ClipRRect(
              borderRadius: BorderRadius.circular(Spacing.radiusLg),
              child: Image.network(photos[i], fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(color: milan.line200)),
            ),
          ),
        )
      else
        Container(height: 200, alignment: Alignment.center,
            decoration: BoxDecoration(color: milan.paper100,
                borderRadius: BorderRadius.circular(Spacing.radiusLg)),
            child: Text('No photos yet — add some from Edit.',
                style: TextStyle(color: milan.ink600))),
      SizedBox(height: Spacing.lg),
      Row(children: [
        Expanded(child: Text(name, style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800))),
        if (isVerified) VerifiedBadge(onTap: () => context.push('/profile/verification')),
      ]),
      if (city != null && city.isNotEmpty)
        Padding(padding: EdgeInsets.only(top: Spacing.xs),
            child: Text(city, style: TextStyle(color: milan.ink600))),
      if (languages.isNotEmpty) ...[
        SizedBox(height: Spacing.sm),
        Text('Speaks ${languages.join(" · ")}',
            style: TextStyle(fontSize: 13, color: milan.ink600)),
      ],
      if (bio != null && bio.trim().isNotEmpty) ...[
        SizedBox(height: Spacing.lg),
        Text(bio, style: TextStyle(height: 1.5)),
      ],
      if (interests.isNotEmpty) ...[
        SizedBox(height: Spacing.lg),
        Wrap(spacing: Spacing.sm, runSpacing: Spacing.sm, children: [
          for (final tag in interests) Chip(label: Text(tag, style: TextStyle(fontSize: 12))),
        ]),
      ],
      if (prompts.isNotEmpty) ...[
        SizedBox(height: Spacing.lg),
        for (final p in prompts)
          Container(margin: EdgeInsets.only(bottom: Spacing.md),
              padding: EdgeInsets.all(Spacing.lg),
              decoration: BoxDecoration(color: milan.paper100,
                  borderRadius: BorderRadius.circular(Spacing.radiusMd)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text((p['question'] ?? '') as String,
                    style: TextStyle(fontSize: 12, color: milan.ink600)),
                SizedBox(height: Spacing.xs),
                Text((p['answer'] ?? '') as String,
                    style: const TextStyle(fontWeight: FontWeight.w600)),
              ])),
      ],
      SizedBox(height: Spacing.xl),
      OutlinedButton.icon(
          icon: Icon(Icons.edit_outlined),
          label: Text('Edit everything'),
          onPressed: () => context.push('/profile/edit')),
      SizedBox(height: Spacing.xl),
    ]);
  }
}
