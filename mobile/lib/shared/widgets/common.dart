import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme/chat_theme_presets.dart';
import '../../app/theme/chat_theme_tokens.dart';
import '../../app/theme/color_tokens.dart';
import '../../app/theme/spacing_tokens.dart';

/// Doc 2 §2.6 (new) — thumbnail tile showing a mini sample bubble pair over
/// the candidate wallpaper so pairing is judged together, never alone.
class WallpaperPreviewCard extends StatelessWidget {
  const WallpaperPreviewCard({
    super.key,
    required this.theme,
    required this.selected,
    this.onTap,
    this.size = 108,
  });

  final ChatWallpaperTheme theme;
  final bool selected;
  final VoidCallback? onTap;
  final double size;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: size,
        height: size * 1.25,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(Spacing.radiusMd),
          border: Border.all(
            color: selected ? milan.marigold500 : Colors.transparent,
            width: 2.5,
          ),
          boxShadow: Spacing.raised,
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(Spacing.radiusMd),
          child: Stack(
            children: [
              Positioned.fill(child:
                  DecoratedBox(decoration: resolveWallpaperDecoration(theme, Brightness.light))),
              Positioned(
                left: Spacing.sm, bottom: size * 0.42,
                child: _miniBubble(context, theme.bubbleColorReceived ?? milan.paper100),
              ),
              Positioned(
                right: Spacing.sm, bottom: Spacing.sm,
                child: _miniBubble(context, theme.bubbleColorSent ?? milan.marigold500),
              ),
              if (selected)
                const Positioned(
                  top: Spacing.sm, right: Spacing.sm,
                  child: Icon(Icons.check_circle, color: Color(0xFFC97D0C), size: 18),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _miniBubble(BuildContext context, Color fill) {
    return Container(
      width: 34,
      height: 16,
      decoration: BoxDecoration(
        color: fill,
        borderRadius: BorderRadius.circular(8),
      ),
    );
  }
}

/// Doc 2 §2.6 — gradient ring for unseen stories.
class StoryRing extends StatelessWidget {
  const StoryRing({super.key, this.seen = false, required this.child, this.size = 56});
  final bool seen;
  final Widget child;
  final double size;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    // Unseen rings use the Milan Sky gradient (deep sky → bright sky); seen
    // rings fade to a muted line tone.
    final Gradient gradient = seen
        ? LinearGradient(colors: [milan.line200, milan.line200])
        : LinearGradient(colors: [milan.dhaka500, milan.dhaka100]);
    return Container(
      width: size + 6,
      height: size + 6,
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(shape: BoxShape.circle, gradient: gradient),
      child: Container(
        padding: const EdgeInsets.all(2),
        color: Theme.of(context).scaffoldBackgroundColor,
        child: ClipOval(child: child),
      ),
    );
  }
}

/// Doc 2 §2.6 — pine-colored verification badge.
class VerifiedBadge extends StatelessWidget {
  const VerifiedBadge({super.key, this.onTap});
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Icon(Icons.verified, size: 20, color: Theme.of(context).extension<MilanColors>()!.pine500),
    );
  }
}

/// Doc 2 §2.6 — circular/arc meter reused on match detail + Kundali Mode.
class CompatibilityMeter extends StatelessWidget {
  const CompatibilityMeter({super.key, required this.score, this.label});
  final int score;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return CustomPaint(
      painter: _ArcPainter(score / 100,
          track: milan.dhaka500.withValues(alpha: 0.16),
          sweepStart: milan.dhaka100, sweepEnd: milan.dhaka500),
      child: SizedBox(
        width: 132,
        height: 132,
        child: Center(
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text('$score%',
                style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w700)),
            if (label != null)
              Text(label!, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
          ]),
        ),
      ),
    );
  }
}

class _ArcPainter extends CustomPainter {
  const _ArcPainter(this.progress,
      {required this.track, required this.sweepStart, required this.sweepEnd});
  final double progress;
  final Color track;
  final Color sweepStart;
  final Color sweepEnd;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.shortestSide / 2 - 8;
    final rect = Rect.fromCircle(center: center, radius: radius);
    final trackPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 9
      ..color = track;
    final sweepPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 9
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        startAngle: 0.75 * math.pi,
        endAngle: 2.25 * math.pi,
        colors: [sweepStart, sweepEnd],
        transform: GradientRotation(0.75 * math.pi),
      ).createShader(rect);
    final startAngle = 0.75 * math.pi;
    final totalSweep = 1.5 * math.pi;
    canvas.drawArc(rect, startAngle, totalSweep, false, trackPaint);
    canvas.drawArc(rect, startAngle, totalSweep * progress.clamp(0.0, 1.0), false, sweepPaint);
  }

  @override
  bool shouldRepaint(_ArcPainter oldDelegate) =>
      oldDelegate.progress != progress ||
      oldDelegate.sweepStart != sweepStart ||
      oldDelegate.sweepEnd != sweepEnd;
}

/// Doc 2 §2.6 — Saathi character gallery card (illustrated, never photoreal).
class AICharacterCard extends StatelessWidget {
  const AICharacterCard({
    super.key,
    required this.name,
    required this.description,
    required this.color,
    this.initial,
    this.onTap,
    this.locked = false,
  });
  final String name;
  final String description;
  final Color color;
  final String? initial;
  final VoidCallback? onTap;
  final bool locked;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Spacing.radiusLg),
        side: BorderSide(color: milan.line200),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(Spacing.radiusLg),
        // Locked cards navigate to the paywall instead of starting a chat.
        onTap: locked ? () => context.push('/settings/subscription') : onTap,
        child: Padding(
          padding: EdgeInsets.all(Spacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: color.withValues(alpha: 0.15),
                child: Text(initial ?? name.characters.first,
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700, color: color)),
              ),
              SizedBox(height: Spacing.md),
              Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
              SizedBox(height: Spacing.xs),
              Expanded(
                child: Text(description,
                    maxLines: 4, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 12.5, height: 1.35, color: Colors.grey.shade700)),
              ),
              Align(
                alignment: Alignment.bottomRight,
                child: locked
                    ? Chip(
                        avatar: Icon(Icons.lock_outline, size: 12, color: milan.dhaka500),
                        label: Text('Pass', style: TextStyle(fontSize: 10, color: milan.dhaka500)),
                        visualDensity: VisualDensity.compact,
                      )
                    : Chip(
                        label: const Text('AI', style: TextStyle(fontSize: 10)),
                        visualDensity: VisualDensity.compact,
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Profile-completion meter (growth pattern): shows how complete the profile is
/// and nudges the next missing item, tied to "be seen more". Tapping opens the
/// editor. Pass a fraction 0..1 and the ordered list of still-missing labels.
class ProfileCompletionMeter extends StatelessWidget {
  const ProfileCompletionMeter({
    super.key,
    required this.percent,
    this.missing = const [],
    this.onTap,
  });

  final double percent;
  final List<String> missing;
  final VoidCallback? onTap;

  /// Standard weighting used across the app so the number is consistent.
  static double computeFrom(Map<String, dynamic> me) {
    final profile = (me['profile'] as Map?) ?? const {};
    final photos = (profile['photos'] as List?) ?? const [];
    final prompts = (profile['prompts'] as List?) ?? const [];
    final checks = <bool>[
      ((profile['display_name'] as String?) ?? '').trim().isNotEmpty,
      ((profile['bio'] as String?) ?? '').trim().length >= 20,
      photos.isNotEmpty,
      photos.length >= 3,
      ((profile['city'] as String?) ?? '').trim().isNotEmpty,
      ((profile['interests'] as List?) ?? const []).isNotEmpty,
      prompts.isNotEmpty,
      (me['user']?['is_verified'] as bool?) ?? false,
    ];
    final done = checks.where((c) => c).length;
    return done / checks.length;
  }

  static List<String> missingFrom(Map<String, dynamic> me) {
    final profile = (me['profile'] as Map?) ?? const {};
    final photos = (profile['photos'] as List?) ?? const [];
    final prompts = (profile['prompts'] as List?) ?? const [];
    return [
      if (((profile['bio'] as String?) ?? '').trim().length < 20) 'Write a short bio',
      if (photos.length < 3) 'Add more photos',
      if (((profile['interests'] as List?) ?? const []).isEmpty) 'Pick your interests',
      if (prompts.isEmpty) 'Answer a prompt',
      if (((me['user']?['is_verified'] as bool?) ?? false) == false) 'Verify your profile',
    ];
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    if (percent >= 1.0) return const SizedBox.shrink();
    final pct = (percent * 100).round();
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(Spacing.radiusMd),
      child: Container(
        padding: EdgeInsets.all(Spacing.lg),
        decoration: BoxDecoration(
          color: milan.paper100,
          borderRadius: BorderRadius.circular(Spacing.radiusMd),
          border: Border.all(color: milan.line200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(Icons.pie_chart_outline, size: 18, color: milan.dhaka500),
              SizedBox(width: Spacing.sm),
              Text('Profile $pct% complete',
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              const Spacer(),
              if (onTap != null)
                Icon(Icons.chevron_right, color: milan.ink400),
            ]),
            SizedBox(height: Spacing.sm),
            ClipRRect(
              borderRadius: BorderRadius.circular(999),
              child: LinearProgressIndicator(
                value: percent,
                minHeight: 6,
                backgroundColor: milan.line200,
                valueColor: AlwaysStoppedAnimation(milan.dhaka500),
              ),
            ),
            if (missing.isNotEmpty) ...[
              SizedBox(height: Spacing.sm),
              Text('Next: ${missing.first} to be seen more',
                  style: TextStyle(fontSize: 12, color: milan.ink600)),
            ],
          ],
        ),
      ),
    );
  }
}
