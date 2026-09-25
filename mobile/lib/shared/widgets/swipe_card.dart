import 'dart:async';
import 'dart:math' as math;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../app/theme/color_tokens.dart';
import '../../app/theme/motion_tokens.dart';
import '../../app/theme/spacing_tokens.dart';

/// Command channel so the action buttons trigger the SAME animated commit a
/// drag does (Tinder-parity): the card flies out, then the parent removes it.
class SwipeCardController extends ChangeNotifier {
  _SwipeIntent? _pending;
  VoidCallback? _onCommand;

  void like() => _fire(_SwipeIntent.like);
  void pass() => _fire(_SwipeIntent.pass);
  void superlike() => _fire(_SwipeIntent.superlike);

  _SwipeIntent? _takePending() {
    final pending = _pending;
    _pending = null;
    return pending;
  }

  void _fire(_SwipeIntent intent) {
    _pending = intent;
    _onCommand?.call();
    notifyListeners();
  }
}

enum _SwipeIntent { none, like, pass, superlike }

/// Doc 2 §2.6 — photo/video carousel card with verification badge, distance/
/// age chip, drag physics, spring settle-back and animated fly-out commit
/// (the deck previously snapped instantly with no decision feedback).
class SwipeCard extends StatefulWidget {
  const SwipeCard({
    super.key,
    required this.mediaUrls,
    required this.name,
    required this.age,
    this.distanceKm,
    this.verified = false,
    this.promptOverlay,
    this.onLike,
    this.onPass,
    this.onSuperlike,
    this.onTapProfile,
    this.controller,
  });

  final List<String> mediaUrls;
  final String name;
  final int age;
  final double? distanceKm;
  final bool verified;
  final String? promptOverlay;
  final Future<bool> Function()? onLike;
  final Future<bool> Function()? onPass;
  final Future<bool> Function()? onSuperlike;
  final VoidCallback? onTapProfile;
  final SwipeCardController? controller;

  @override
  State<SwipeCard> createState() => _SwipeCardState();
}

class _SwipeCardState extends State<SwipeCard>
    with SingleTickerProviderStateMixin {
  double _dragDx = 0;
  double _dragDy = 0;
  int _page = 0;
  late final AnimationController _motion = AnimationController(
    vsync: this,
    duration: Motion.swipeSpring,
  );
  Animation<Offset>? _flyOut;
  bool _committing = false;

  static const double _commitThreshold = 140;

  @override
  void initState() {
    super.initState();
    widget.controller?._onCommand = _commandSwipe;
  }

  @override
  void didUpdateWidget(SwipeCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller != widget.controller) {
      oldWidget.controller?._onCommand = null;
      widget.controller?._onCommand = _commandSwipe;
    }
  }

  @override
  void dispose() {
    widget.controller?._onCommand = null;
    _motion.dispose();
    super.dispose();
  }

  /// Buttons route through the same animation as a drag: fly out toward the
  /// decision, fire the callback on landing, and restore the card when the
  /// server rejects the action.
  void _commandSwipe() {
    if (_committing) {
      widget.controller?._takePending();
      return;
    }
    final intent = widget.controller?._takePending() ?? _SwipeIntent.none;
    switch (intent) {
      case _SwipeIntent.like:
        _flyTo(const Offset(1.6, -0.12), intent);
      case _SwipeIntent.pass:
        _flyTo(const Offset(-1.6, -0.12), intent);
      case _SwipeIntent.superlike:
        _flyTo(const Offset(0.06, -2.2), intent);
      case _SwipeIntent.none:
        break;
    }
  }

  void _flyTo(Offset direction, _SwipeIntent intent) {
    if (_committing) return;
    _committing = true;
    final size = MediaQuery.sizeOf(context);
    final target = Offset(
      direction.dx * size.width,
      direction.dy * size.width * 0.4 + direction.dy * 300,
    );
    final anim = Tween<Offset>(
      begin: Offset(_dragDx, _dragDy),
      end: target,
    ).animate(CurvedAnimation(parent: _motion, curve: Curves.easeOutCubic));
    setState(() => _flyOut = anim);
    unawaited(_finishFlyOut(intent));
  }

  Future<void> _finishFlyOut(_SwipeIntent intent) async {
    try {
      await _motion.forward(from: 0).orCancel;
    } on TickerCanceled {
      return;
    }
    if (!mounted) return;

    var accepted = true;
    try {
      switch (intent) {
        case _SwipeIntent.like:
          accepted = await (widget.onLike?.call() ?? Future.value(true));
        case _SwipeIntent.pass:
          accepted = await (widget.onPass?.call() ?? Future.value(true));
        case _SwipeIntent.superlike:
          accepted = await (widget.onSuperlike?.call() ?? Future.value(true));
        case _SwipeIntent.none:
          break;
      }
    } catch (_) {
      accepted = false;
    }
    if (!accepted && mounted) _restoreAfterFailure();
  }

  void _restoreAfterFailure() {
    _motion.stop();
    setState(() {
      _flyOut = null;
      _dragDx = 0;
      _dragDy = 0;
      _committing = false;
    });
  }

  void _settle() {
    // Spring settle: overshoot curve from wherever the finger left, back to
    // centre (Motion.swipeSpring duration).
    final from = Offset(_dragDx, _dragDy);
    final anim = Tween<Offset>(begin: from, end: Offset.zero).animate(
      CurvedAnimation(parent: _motion, curve: const Cubic(0.22, 1.4, 0.4, 1)),
    ); // slight overshoot
    setState(() => _flyOut = anim);
    _motion.forward(from: 0).whenComplete(() {
      setState(() {
        _flyOut = null;
        _dragDx = 0;
        _dragDy = 0;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final reduced = Motion.prefersReducedMotion(context);
    final dragDx = _flyOut?.value.dx ?? _dragDx;
    final dragDy = _flyOut?.value.dy ?? _dragDy;
    final rotation =
        (reduced ? 0 : 1) *
        Motion.dragToRotation(dragDx, MediaQuery.sizeOf(context).width) *
        math.pi /
        180;

    return GestureDetector(
      onHorizontalDragUpdate: reduced
          ? null
          : (details) => setState(() {
              _dragDx += details.delta.dx;
            }),
      onHorizontalDragEnd: reduced
          ? null
          : (details) {
              if (_dragDx.abs() >= _commitThreshold) {
                _flyTo(
                  Offset(_dragDx > 0 ? 1.6 : -1.6, _dragDy / 400 - 0.12),
                  _dragDx > 0 ? _SwipeIntent.like : _SwipeIntent.pass,
                );
              } else {
                _settle();
              }
            },
      onVerticalDragUpdate: reduced
          ? null
          : (details) => setState(() {
              if (details.delta.dy < 0) _dragDy += details.delta.dy;
            }),
      onVerticalDragEnd: reduced
          ? null
          : (details) {
              if (_dragDy <= -_commitThreshold) {
                _flyTo(const Offset(0.06, -2.2), _SwipeIntent.superlike);
              } else {
                _settle();
              }
            },
      child: Transform.translate(
        offset: Offset(dragDx, dragDy),
        child: Transform.rotate(
          angle: rotation,
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(Spacing.radiusLg),
              boxShadow: Spacing.raised,
            ),
            clipBehavior: Clip.antiAlias,
            child: Stack(
              fit: StackFit.expand,
              children: [
                ColoredBox(
                  color: milan.paper100,
                  child: widget.mediaUrls.isEmpty
                      ? Center(
                          child: Icon(
                            Icons.person,
                            size: 64,
                            color: milan.ink400,
                          ),
                        )
                      : GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTapUp: (details) {
                            final half = MediaQuery.sizeOf(context).width / 2;
                            setState(() {
                              if (details.globalPosition.dx > half &&
                                  _page < widget.mediaUrls.length - 1) {
                                _page++;
                              } else if (details.globalPosition.dx <= half &&
                                  _page > 0) {
                                _page--;
                              }
                            });
                          },
                          child: CachedNetworkImage(
                            imageUrl:
                                widget.mediaUrls[_page.clamp(
                                  0,
                                  widget.mediaUrls.length - 1,
                                )],
                            fit: BoxFit.cover,
                            placeholder: (_, __) =>
                                Container(color: Colors.grey.shade200),
                            errorWidget: (_, __, ___) =>
                                Container(color: Colors.grey.shade300),
                          ),
                        ),
                ),
                // Decision stamps — the interest feedback the deck never had.
                _DecisionStamp(
                  label: 'LIKE',
                  color: const Color(0xFF1F8F62),
                  icon: Icons.favorite_rounded,
                  opacity: _stampOpacity(dragDx, positive: true),
                  rotation: -0.35,
                ),
                _DecisionStamp(
                  label: 'NOPE',
                  color: const Color(0xFFE0384C),
                  icon: Icons.close_rounded,
                  opacity: _stampOpacity(dragDx, positive: false),
                  rotation: 0.35,
                ),
                _DecisionStamp(
                  label: 'SUPER',
                  color: const Color(0xFF0B84FE),
                  icon: Icons.diamond_rounded,
                  opacity: (_dragDy / -120).clamp(0.0, 1.0),
                  rotation: 0,
                ),
                if (widget.promptOverlay != null)
                  Positioned(
                    left: Spacing.lg,
                    right: Spacing.lg,
                    bottom: 96,
                    child: Container(
                      padding: EdgeInsets.all(Spacing.lg),
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(Spacing.radiusMd),
                      ),
                      child: Text(
                        widget.promptOverlay!,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          height: 1.3,
                        ),
                      ),
                    ),
                  ),
                Positioned(
                  left: Spacing.lg,
                  right: Spacing.lg,
                  bottom: Spacing.xl,
                  child: Row(
                    children: [
                      Flexible(
                        child: Text(
                          widget.age > 0
                              ? '${widget.name}, ${widget.age}'
                              : widget.name,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 24,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      SizedBox(width: Spacing.md),
                      if (widget.verified)
                        Icon(Icons.verified, size: 20, color: Colors.white),
                      SizedBox(width: Spacing.md),
                      // Full public profile (doc 8 Part D.7) — the deck
                      // previously had no way to see more than the card.
                      if (widget.onTapProfile != null)
                        GestureDetector(
                          behavior: HitTestBehavior.opaque,
                          onTap: widget.onTapProfile,
                          child: Container(
                            padding: const EdgeInsets.all(5),
                            decoration: const BoxDecoration(
                              color: Colors.black45,
                              shape: BoxShape.circle,
                            ),
                            child: const Icon(
                              Icons.info_outline,
                              size: 17,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      const Spacer(),
                      if (widget.distanceKm != null)
                        Container(
                          padding: EdgeInsets.symmetric(
                            horizontal: Spacing.md,
                            vertical: Spacing.sm,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.black45,
                            borderRadius: BorderRadius.circular(Spacing.pill),
                          ),
                          child: Text(
                            '${widget.distanceKm!.toStringAsFixed(0)} km',
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 12,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                if (widget.mediaUrls.length > 1)
                  Positioned(
                    top: Spacing.md,
                    left: Spacing.lg,
                    right: Spacing.lg,
                    child: Row(
                      children: List.generate(widget.mediaUrls.length, (i) {
                        return Expanded(
                          child: Padding(
                            padding: EdgeInsets.symmetric(
                              horizontal: Spacing.sm,
                            ),
                            child: LinearProgressIndicator(
                              value: i == _page ? 1 : (i < _page ? 1 : 0),
                              minHeight: 3,
                              backgroundColor: Colors.white30,
                              valueColor: AlwaysStoppedAnimation(Colors.white),
                            ),
                          ),
                        );
                      }),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  double _stampOpacity(double dx, {required bool positive}) {
    if (positive) {
      return dx > 0 ? (dx / 120).clamp(0.0, 1.0) : 0;
    }
    return dx < 0 ? (-dx / 120).clamp(0.0, 1.0) : 0;
  }
}

class _DecisionStamp extends StatelessWidget {
  const _DecisionStamp({
    required this.label,
    required this.color,
    required this.icon,
    required this.opacity,
    required this.rotation,
  });

  final String label;
  final Color color;
  final IconData icon;
  final double opacity;
  final double rotation;

  @override
  Widget build(BuildContext context) {
    if (opacity <= 0.02) return const SizedBox.shrink();
    return IgnorePointer(
      child: Center(
        child: Transform.rotate(
          angle: rotation,
          child: Opacity(
            opacity: opacity,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 9),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.9),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.white, width: 3),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(icon, color: Colors.white, size: 20),
                  const SizedBox(width: 6),
                  Text(
                    label,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.5,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
