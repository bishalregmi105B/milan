import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../shared/widgets/milan_logo.dart';

/// Brand intro (doc 8 Part D.6): three animated value-prop pages shown to
/// fresh installs before language select. Skippable — "Sign in" always jumps
/// straight to the entry screen. Pages build the Milan promise in order:
/// meet for real, feel seen, stay safe.
class OnboardingIntroScreen extends ConsumerStatefulWidget {
  const OnboardingIntroScreen({super.key});

  @override
  ConsumerState<OnboardingIntroScreen> createState() =>
      _OnboardingIntroScreenState();
}

class _OnboardingIntroScreenState extends ConsumerState<OnboardingIntroScreen> {
  final _controller = PageController();
  int _page = 0;

  static const _pages = <_IntroPage>[
    _IntroPage(
      icon: Icons.favorite_rounded,
      title: 'भेट हुने ठाउँ, मिलन',
      subtitle: 'Where two paths meet',
      body: 'Match with real, verified Nepali people who actually share your '
          'world — from chiya tastes to Dashain plans.',
    ),
    _IntroPage(
      icon: Icons.auto_awesome,
      title: 'Companions with real lives',
      subtitle: 'AI companions that feel present',
      body: 'They have their own day, their own stories, and they text first '
          'when it matters — adapting to how you write.',
    ),
    _IntroPage(
      icon: Icons.verified_user_outlined,
      title: 'Safe by design',
      subtitle: 'Liveness-verified, 18+ only',
      body: 'Every profile is selfie-verified. Report, block and privacy '
          'controls are one tap away. Always.',
    ),
  ];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _next() {
    if (_page < _pages.length - 1) {
      _controller.nextPage(
          duration: const Duration(milliseconds: 420), curve: Curves.easeOutCubic);
    } else {
      context.go('/onboarding/language');
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    return Scaffold(
      backgroundColor: milan.paper0,
      body: SafeArea(
        child: Column(children: [
          Align(
            alignment: Alignment.topRight,
            child: TextButton(
                onPressed: () => context.go('/onboarding/language'),
                child: const Text('Skip')),
          ),
          Expanded(
            child: PageView.builder(
              controller: _controller,
              itemCount: _pages.length,
              onPageChanged: (i) => setState(() => _page = i),
              itemBuilder: (context, i) =>
                  _IntroPageView(page: _pages[i], index: i),
            ),
          ),
          Padding(
            padding: EdgeInsets.fromLTRB(Spacing.xl, 0, Spacing.xl, Spacing.xl),
            child: Column(children: [
              Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                for (var i = 0; i < _pages.length; i++)
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 220),
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    width: i == _page ? 22 : 7,
                    height: 7,
                    decoration: BoxDecoration(
                      color: i == _page ? milan.dhaka500 : milan.line200,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
              ]),
              SizedBox(height: Spacing.xl),
              Row(children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => context.push('/onboarding/phone'),
                    child: const Text('Sign in'),
                  ),
                ),
                SizedBox(width: Spacing.md),
                Expanded(
                  child: FilledButton(
                    onPressed: _next,
                    child: Text(
                        _page == _pages.length - 1 ? 'Get started' : 'Next'),
                  ),
                ),
              ]),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _IntroPage {
  const _IntroPage(
      {required this.icon,
      required this.title,
      required this.subtitle,
      required this.body});
  final IconData icon;
  final String title;
  final String subtitle;
  final String body;
}

class _IntroPageView extends StatefulWidget {
  const _IntroPageView({required this.page, required this.index});
  final _IntroPage page;
  final int index;

  @override
  State<_IntroPageView> createState() => _IntroPageViewState();
}

class _IntroPageViewState extends State<_IntroPageView>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 900));
  late final Animation<double> _rise =
      CurvedAnimation(parent: _c, curve: Curves.easeOutCubic);

  @override
  void initState() {
    super.initState();
    _c.forward();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    final page = widget.page;
    final accent =
        widget.index == 0 ? milan.dhaka500 : (widget.index == 1 ? milan.marigold500 : milan.pine500);
    return Padding(
      padding: EdgeInsets.all(Spacing.xxl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Gentle 3D tilt + float on the hero emblem (pure Flutter, honors
          // the reduced-motion setting through the rise curve only).
          FadeTransition(
            opacity: _rise,
            child: SlideTransition(
              position: Tween(begin: const Offset(0, .18), end: Offset.zero)
                  .animate(_rise),
              child: TweenAnimationBuilder<double>(
                tween: Tween(begin: 0.9, end: 1.0),
                duration: const Duration(milliseconds: 900),
                curve: Curves.easeOutBack,
                builder: (context, scale, child) =>
                    Transform.scale(scale: scale, child: child),
                child: Container(
                  width: 180,
                  height: 180,
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    border: Border.all(color: milan.line200),
                    boxShadow: [
                      BoxShadow(
                          color: accent.withValues(alpha: 0.18),
                          blurRadius: 32,
                          spreadRadius: 6),
                    ],
                  ),
                  child: Center(
                    child: widget.index == 0
                        ? const MilanLogoMark(size: 112)
                        : Icon(page.icon,
                            size: 64,
                            color: widget.index == 1
                                ? milan.marigold500
                                : milan.pine500),
                  ),
                ),
              ),
            ),
          ),
          SizedBox(height: Spacing.xxl),
          Text(page.title,
              textAlign: TextAlign.center,
              style: context.h1.copyWith(fontFamily: 'Sora')),
          SizedBox(height: Spacing.xs),
          Text(page.subtitle,
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: accent)),
          SizedBox(height: Spacing.lg),
          Text(page.body,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 15, height: 1.5, color: milan.ink600)),
        ],
      ),
    );
  }
}
