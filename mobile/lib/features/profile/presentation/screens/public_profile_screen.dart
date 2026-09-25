import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:share_plus/share_plus.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../core/feedback/sfx.dart';
import '../../../../core/network/api_client.dart';

/// Public view of another user's profile (doc 8 Part D.7). Backed by
/// `GET /profile/<id>/public`, which honours `hidden_fields`, blurs discreet
/// users, and records the view for "Who viewed me" (§C9).
class PublicProfileScreen extends ConsumerStatefulWidget {
  const PublicProfileScreen({super.key, required this.userId});
  final String userId;

  @override
  ConsumerState<PublicProfileScreen> createState() =>
      _PublicProfileScreenState();
}

class _PublicProfileScreenState extends ConsumerState<PublicProfileScreen> {
  Map<String, dynamic>? _profile;
  String? _error;
  bool _loading = true;
  bool _liked = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final res = await ref
          .read(apiClientProvider)
          .get<Map<String, dynamic>>('/profile/${widget.userId}/public');
      if (!mounted) return;
      setState(() => _profile = res);
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.displayMessage);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    return Scaffold(
      backgroundColor: milan.paper0,
      appBar: AppBar(title: const Text('Profile')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                  Text(_error!, style: TextStyle(color: milan.ink600)),
                  SizedBox(height: Spacing.md),
                  FilledButton(onPressed: _load, child: const Text('Retry')),
                ]))
              : _buildProfile(context, _profile!),
    );
  }

  Widget _buildProfile(BuildContext context, Map<String, dynamic> p) {
    final milan = context.milan;
    final photos = (p['photos'] as List?)?.cast<String>() ?? const <String>[];
    final interests = (p['interests'] as List?)?.cast<String>() ?? const <String>[];
    final prompts = (p['prompts'] as List?) ?? const [];
    final name = (p['display_name'] as String?) ?? 'Milan user';
    final trust = p['trust_score'] as int?;

    return ListView(padding: const EdgeInsets.only(bottom: 48), children: [
      Stack(children: [
        if (photos.isNotEmpty)
          SizedBox(
            height: 280,
            width: double.infinity,
            child: p['is_blurred'] == true
                ? Stack(fit: StackFit.expand, children: [
                    CachedNetworkImage(imageUrl: photos.first, fit: BoxFit.cover),
                    Container(
                        color: Colors.white.withValues(alpha: 0.72),
                        child: Center(
                          child: Column(mainAxisSize: MainAxisSize.min, children: [
                            Icon(Icons.lock_rounded, color: milan.ink600),
                            SizedBox(height: Spacing.xs),
                            Text('Photos visible after you match',
                                style: TextStyle(fontSize: 13, color: milan.ink600)),
                          ]),
                        )),
                  ])
                : CachedNetworkImage(imageUrl: photos.first, fit: BoxFit.cover),
          )
        else
          Container(height: 180, color: milan.paper100),
        if (photos.length > 1)
          Positioned(
            bottom: 10,
            left: 0,
            right: 0,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (var i = 0; i < photos.length && i < 5; i++)
                  Container(
                    width: 6,
                    height: 6,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: i == 0 ? 1 : 0.5),
                        shape: BoxShape.circle),
                  ),
              ],
            ),
          ),
      ]),
      Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Text(name, style: context.h2),
            ),
            if (p['is_verified'] == true)
              Icon(Icons.verified, size: 22, color: const Color(0xFF0B84FE)),
            SizedBox(width: Spacing.sm),
            if (trust != null)
              _TrustBadge(score: trust),
          ]),
          SizedBox(height: Spacing.xs),
          Text(_subtitle(p), style: TextStyle(fontSize: 14, color: milan.ink600)),
          if (p['bio'] != null && (p['bio'] as String).isNotEmpty) ...[
            SizedBox(height: Spacing.lg),
            Text(p['bio'] as String,
                style: TextStyle(fontSize: 15, height: 1.5, color: milan.ink900)),
          ],
          if (interests.isNotEmpty) ...[
            SizedBox(height: Spacing.lg),
            Wrap(
              spacing: Spacing.sm,
              runSpacing: Spacing.sm,
              children: [
                for (final interest in interests)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                        color: milan.paper100,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: milan.line200)),
                    child: Text(interest,
                        style: TextStyle(fontSize: 12.5, color: milan.ink900)),
                  ),
              ],
            ),
          ],
          if (prompts.isNotEmpty) ...[
            SizedBox(height: Spacing.xl),
            Text('Prompts', style: context.h4),
            SizedBox(height: Spacing.sm),
            for (final prompt in prompts.take(3))
              Container(
                margin: const EdgeInsets.only(bottom: 10),
                padding: EdgeInsets.all(Spacing.lg),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(Spacing.radiusMd),
                    border: Border.all(color: milan.line200)),
                child: Text(_promptText(prompt),
                    style: TextStyle(fontSize: 14, height: 1.45, color: milan.ink900)),
              ),
          ],
          SizedBox(height: Spacing.xl),
          // Like / Superlike / Share — the request to THIS person sent from
          // their profile (doc 8 §A4: match requests must be visible).
          Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: (_busy || _liked) ? null : () => _sendSwipe('like'),
                icon: Icon(_liked ? Icons.favorite : Icons.favorite_border,
                    size: 18,
                    color: _liked ? null : milan.dhaka500),
                label: Text(_liked ? 'Like sent' : 'Like'),
              ),
            ),
            const SizedBox(width: 10),
            IconButton(
              onPressed: (_busy || _liked) ? null : () => _sendSwipe('superlike'),
              tooltip: 'Superlike with a note',
              style: IconButton.styleFrom(
                  backgroundColor: milan.dhaka100, shape: const CircleBorder()),
              icon: Icon(Icons.diamond_outlined, size: 20, color: milan.dhaka500),
            ),
            const SizedBox(width: 10),
            IconButton(
              onPressed: () => SharePlus.instance.share(ShareParams(
                  text: 'Check out this profile on Milan — the Nepali dating '
                      'app: https://milan.pukarphulara.com.np')),
              tooltip: 'Share',
              style: IconButton.styleFrom(
                  backgroundColor: milan.paper100, shape: const CircleBorder()),
              icon: Icon(Icons.ios_share, size: 18, color: milan.ink600),
            ),
          ]),
          SizedBox(height: Spacing.lg),
          ..._detailsSection(context, p),
          SizedBox(height: Spacing.lg),
          if (photos.length > 1 && p['is_blurred'] != true)
            SizedBox(
              height: 260,
              child: GridView.builder(
                physics: const NeverScrollableScrollPhysics(),
                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 3, crossAxisSpacing: 4, mainAxisSpacing: 4),
                itemCount: photos.length - 1,
                itemBuilder: (context, i) => ClipRRect(
                  borderRadius: BorderRadius.circular(6),
                  child: CachedNetworkImage(
                      imageUrl: photos[i + 1], fit: BoxFit.cover),
                ),
              ),
            ),
        ]),
      ),
    ]);
  }

  Future<void> _sendSwipe(String direction) async {
    setState(() => _busy = true);
    try {
      await ref.read(apiClientProvider).post('/discovery/swipe',
          body: {'target_id': widget.userId, 'direction': direction});
      if (!mounted) return;
      ref.read(sfxProvider.notifier).play(Sfx.swipeLike);
      setState(() {
        _liked = true;
        _busy = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(direction == 'superlike'
              ? 'Superlike sent — you stand out now ⭐'
              : 'Like sent — if they like you back, it\'s a match!')));
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.displayMessage)));
    }
  }

  /// Every non-empty detail we hold, as label/value rows (§C8 — interview
  /// answers finally get a read surface).
  List<Widget> _detailsSection(BuildContext context, Map<String, dynamic> p) {
    final milan = context.milan;
    const fields = <(String, String)>[
      ('height_cm', 'Height'),
      ('education', 'Education'),
      ('profession', 'Work'),
      ('hometown', 'From'),
      ('languages', 'Languages'),
      ('mother_tongue', 'Mother tongue'),
      ('diet', 'Diet'),
      ('drinking', 'Drinking'),
      ('smoking', 'Smoking'),
      ('lifestyle_tags', 'Lifestyle'),
      ('values_tags', 'Values'),
      ('conversation_style', 'Chats in'),
    ];
    final rows = <(String, String)>[];
    for (final (key, label) in fields) {
      final value = p[key];
      if (value == null) continue;
      final text = value is List
          ? value.map((e) => e.toString().replaceAll('_', ' ')).join(', ')
          : value.toString().replaceAll('_', ' ');
      if (text.trim().isEmpty || text == '[]') continue;
      rows.add((label, text));
    }
    if (rows.isEmpty) return [];
    return [
      Text('About', style: context.h4),
      SizedBox(height: Spacing.sm),
      Container(
        padding: EdgeInsets.all(Spacing.lg),
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(Spacing.radiusMd),
            border: Border.all(color: milan.line200)),
        child: Column(children: [
          for (var i = 0; i < rows.length; i++) ...[
            if (i > 0) Divider(height: 18, color: milan.line200),
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              SizedBox(
                  width: 108,
                  child: Text(rows[i].$1,
                      style: TextStyle(fontSize: 13, color: milan.ink400))),
              Expanded(
                  child: Text(rows[i].$2,
                      style: TextStyle(
                          fontSize: 13.5, fontWeight: FontWeight.w600,
                          color: milan.ink900))),
            ]),
          ],
        ]),
      ),
    ];
  }

  String _subtitle(Map<String, dynamic> p) {
    final parts = <String>[
      if (p['city'] != null && (p['city'] as String).isNotEmpty) p['city'] as String,
      if (p['profession'] != null && (p['profession'] as String).isNotEmpty)
        p['profession'] as String,
      if (p['relationship_intent'] != null)
        (p['relationship_intent'] as String).replaceAll('_', ' '),
    ];
    return parts.isEmpty ? 'On Milan' : parts.join(' · ');
  }

  String _promptText(dynamic prompt) {
    if (prompt is Map) {
      final question = prompt['question'] ?? prompt['questionText'] ?? '';
      final answer = prompt['answer'] ?? prompt['answerText'] ?? '';
      return answer.isNotEmpty ? '$question\n$answer' : '$answer$question';
    }
    return prompt.toString();
  }
}

class _TrustBadge extends StatelessWidget {
  const _TrustBadge({required this.score});
  final int score;

  @override
  Widget build(BuildContext context) {
    final color = score >= 70
        ? const Color(0xFF1F8F62)
        : (score >= 45 ? const Color(0xFFF5A623) : const Color(0xFF8A919C));
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(10)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(Icons.shield_outlined, size: 12, color: color),
        const SizedBox(width: 3),
        Text('$score',
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: color)),
      ]),
    );
  }
}
