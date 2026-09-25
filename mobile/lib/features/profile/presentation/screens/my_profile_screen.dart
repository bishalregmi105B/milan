import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/network/api_client.dart';
import '../../../auth/application/auth_provider.dart';
import '../../../../shared/widgets/common.dart';
import '../../../../shared/widgets/states.dart';

/// Screen 12 — self-view profile. Everything is loaded from `/profile/me`:
/// the account you set up at signup is shown here as-is (name, photo,
/// verification, city, interests, prompts) — never a static placeholder.
class MyProfileScreen extends ConsumerStatefulWidget {
  const MyProfileScreen({super.key});

  @override
  ConsumerState<MyProfileScreen> createState() => _MyProfileScreenState();
}

class _MyProfileScreenState extends ConsumerState<MyProfileScreen> {
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
      appBar: AppBar(
        title: Text('Profile', style: context.h2),
        actions: [
          IconButton(
            tooltip: 'Safety Center',
            icon: Icon(Icons.shield_outlined),
            onPressed: () => context.push('/safety'),
          ),
        ],
      ),
      body: _loading
          ? _ProfileSkeleton()
          : _failed || _me == null
              ? MilanErrorState(onRetry: _load)
              : _buildBody(_me!, milan),
    );
  }

  Widget _buildBody(Map<String, dynamic> me, MilanColors milan) {
    final user = (me['user'] ?? {}) as Map<String, dynamic>;
    final profile = (me['profile'] ?? {}) as Map<String, dynamic>;
    final name = (profile['display_name'] as String?) ?? '';
    final isVerified = (user['is_verified'] as bool?) ?? false;
    final photos = ((profile['photos'] as List?) ?? const [])
        .map((p) => (p as Map<String, dynamic>)['url'] as String? ?? '')
        .where((u) => u.isNotEmpty)
        .toList();
    final city = profile['city'] as String?;
    final bio = profile['bio'] as String?;
    final interests = ((profile['interests'] as List?) ?? const [])
        .map((e) => e.toString())
        .toList();
    final phone = user['phone'] as String?;

    return ListView(
      padding: EdgeInsets.all(Spacing.xl),
      children: [
        ProfileCompletionMeter(
          percent: ProfileCompletionMeter.computeFrom(me),
          missing: ProfileCompletionMeter.missingFrom(me),
          onTap: () => context.push('/profile/edit'),
        ),
        SizedBox(height: Spacing.lg),
        Row(children: [
          StoryRing(
            seen: true,
            child: CircleAvatar(
              radius: 30,
              backgroundImage:
                  photos.isNotEmpty ? CachedNetworkImageProvider(photos.first) : null,
              child: photos.isEmpty ? const Icon(Icons.person) : null,
            ),
          ),
          SizedBox(width: Spacing.lg),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(name.isNotEmpty ? name : 'Complete your profile',
                  maxLines: 2, overflow: TextOverflow.ellipsis, style: context.h3),
              SizedBox(height: Spacing.xs),
              Row(children: [
                if (isVerified) ...[
                  VerifiedBadge(onTap: () => context.push('/profile/verification')),
                  SizedBox(width: Spacing.sm),
                  Text('Verified', style: TextStyle(fontSize: 12, color: milan.pine500)),
                ] else
                  GestureDetector(
                    onTap: () => context.push('/onboarding/liveness'),
                    child: Text('Verify your photo →',
                        style: TextStyle(fontSize: 12, color: milan.dhaka500)),
                  ),
                if (city != null && city.isNotEmpty) ...[
                  SizedBox(width: Spacing.sm),
                  Text('· $city', style: TextStyle(fontSize: 12, color: milan.ink600)),
                ],
              ]),
            ]),
          ),
          OutlinedButton(onPressed: () => context.push('/profile/edit'), child: Text('Edit')),
        ]),
        SizedBox(height: Spacing.lg),
        // See yourself exactly the way a match sees you when they swipe up.
        OutlinedButton.icon(
          icon: Icon(Icons.visibility_outlined),
          label: Text('View my profile as others see it'),
          onPressed: () => context.push('/profile/me/view'),
        ),
        SizedBox(height: Spacing.xl),
        if (bio != null && bio.trim().isNotEmpty) ...[
          Text(bio, style: TextStyle(color: milan.ink600, height: 1.45)),
          SizedBox(height: Spacing.lg),
        ],
        if (interests.isNotEmpty) ...[
          Wrap(spacing: Spacing.sm, runSpacing: Spacing.sm, children: [
            for (final tag in interests)
              Chip(label: Text(tag, style: TextStyle(fontSize: 12))),
          ]),
          SizedBox(height: Spacing.lg),
        ],
        if (phone == null || phone.isEmpty)
          _SettingsTile(
              icon: Icons.phone_android_outlined,
              label: 'Add a phone number (optional)',
              onTap: () async {
                await context.push('/profile/add-phone');
                _load();
              })
        else
          _SettingsTile(
              icon: Icons.phone_android_outlined,
              label: 'Phone: $phone',
              onTap: null),
        _SettingsTile(icon: Icons.notifications_outlined, label: 'Notifications',
            onTap: () => context.push('/settings/notifications')),
        _SettingsTile(icon: Icons.palette_outlined, label: 'Appearance',
            onTap: () => context.push('/settings/appearance')),
        _SettingsTile(icon: Icons.translate, label: 'Language & Accessibility',
            onTap: () => context.push('/settings/language')),
        _SettingsTile(icon: Icons.account_balance_wallet_outlined, label: 'Payment Methods',
            onTap: () => context.push('/settings/payment-methods')),
        _SettingsTile(icon: Icons.workspace_premium_outlined, label: 'Subscription Plans',
            onTap: () => context.push('/settings/subscription')),
        _SettingsTile(icon: Icons.help_outline, label: 'Help & Support',
            onTap: () => context.push('/settings/help')),
        _SettingsTile(icon: Icons.shield_moon_outlined, label: 'Privacy & Discreet Mode',
            onTap: () => context.push('/profile/privacy')),
        _SettingsTile(icon: Icons.logout_outlined, label: 'Sign out',
            onTap: () => _confirmSignOut(context, ref)),
      ],
    );
  }

  void _confirmSignOut(BuildContext context, WidgetRef ref) {
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text('Your profile, matches and messages stay safe — you can sign back in with your email.'),
        actions: [
          TextButton(onPressed: () => dialogContext.pop(), child: const Text('Cancel')),
          FilledButton(
            onPressed: () async {
              dialogContext.pop();
              await ref.read(authProvider.notifier).signOut();
              if (!context.mounted) return;
              context.go('/onboarding/phone');
            },
            child: const Text('Sign out'),
          ),
        ],
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({required this.icon, required this.label, this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.only(bottom: Spacing.md),
      elevation: 0,
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Spacing.radiusMd)),
      child: ListTile(
        leading: Icon(icon, size: 22),
        title: Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
        trailing: Icon(Icons.chevron_right, color: Theme.of(context).extension<MilanColors>()!.ink400),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Spacing.radiusMd)),
        onTap: onTap,
      ),
    );
  }
}

/// Loading placeholder for the self-profile (consistency library skeletons).
class _ProfileSkeleton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: EdgeInsets.all(Spacing.xl),
      children: [
        const MilanSkeleton(height: 64, radius: 16),
        SizedBox(height: Spacing.lg),
        Row(children: [
          const MilanSkeleton(width: 60, height: 60, radius: 30),
          SizedBox(width: Spacing.lg),
          const Expanded(child: MilanSkeleton(height: 22)),
        ]),
        SizedBox(height: Spacing.xl),
        const MilanSkeleton(height: 120, radius: 16),
        SizedBox(height: Spacing.lg),
        const MilanSkeleton(height: 120, radius: 16),
      ],
    );
  }
}
