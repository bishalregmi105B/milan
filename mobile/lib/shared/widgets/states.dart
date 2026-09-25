import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

import '../../app/theme/color_tokens.dart';
import '../../app/theme/spacing_tokens.dart';

/// Shared state widgets so every screen shows the SAME loading / empty / error
/// treatment (doc: consistency library). Use these instead of ad-hoc
/// `CircularProgressIndicator` / bare `Text('error')` blocks.

/// A single shimmering placeholder block.
class MilanSkeleton extends StatelessWidget {
  const MilanSkeleton({
    super.key,
    this.width,
    this.height = 16,
    this.radius = 8,
  });
  final double? width;
  final double height;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final base = milan.paper100;
    final highlight = Color.lerp(milan.paper100, milan.dhaka500, 0.08)!;
    return Shimmer.fromColors(
      baseColor: base,
      highlightColor: highlight,
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: base,
          borderRadius: BorderRadius.circular(radius),
        ),
      ),
    );
  }
}

/// Full-bleed card skeleton for the discovery deck / profile hero.
class MilanCardSkeleton extends StatelessWidget {
  const MilanCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.all(Spacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Expanded(child: MilanSkeleton(height: double.infinity, radius: 24)),
          SizedBox(height: Spacing.lg),
          const MilanSkeleton(width: 180, height: 22),
          SizedBox(height: Spacing.sm),
          const MilanSkeleton(width: 120, height: 14),
        ],
      ),
    );
  }
}

class MilanEmptyState extends StatelessWidget {
  const MilanEmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.subtitle,
    this.actionLabel,
    this.onAction,
  });
  final IconData icon;
  final String title;
  final String? subtitle;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Center(
      child: Padding(
        padding: EdgeInsets.all(Spacing.xxxl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: milan.dhaka500),
            SizedBox(height: Spacing.lg),
            Text(title,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
            if (subtitle != null) ...[
              SizedBox(height: Spacing.sm),
              Text(subtitle!,
                  textAlign: TextAlign.center,
                  style: TextStyle(color: milan.ink600)),
            ],
            if (actionLabel != null && onAction != null) ...[
              SizedBox(height: Spacing.lg),
              FilledButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}

class MilanErrorState extends StatelessWidget {
  const MilanErrorState({super.key, this.message, required this.onRetry});
  final String? message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Center(
      child: Padding(
        padding: EdgeInsets.all(Spacing.xxxl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.cloud_off_rounded, size: 44, color: milan.ink400),
            SizedBox(height: Spacing.lg),
            Text(message ?? "Something went wrong.",
                textAlign: TextAlign.center,
                style: TextStyle(color: milan.ink600)),
            SizedBox(height: Spacing.lg),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}
