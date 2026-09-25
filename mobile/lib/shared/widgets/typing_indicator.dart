import 'package:flutter/material.dart';

import '../../app/theme/motion_tokens.dart';

/// Doc 2 §2.6 — three-dot pulse, shared by match chat and Saathi chat.
class TypingIndicator extends StatefulWidget {
  const TypingIndicator({
    super.key,
    this.color = const Color(0xFF7B1E3A),
    this.loop = Motion.saathiTypingPulse,
  });

  final Color color;
  final Duration loop;

  @override
  State<TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<TypingIndicator>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller =
      AnimationController(vsync: this, duration: widget.loop)..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            final phase = (_controller.value * 3 - i).clamp(0.0, 1.0);
            final lift = Motion.prefersReducedMotion(context)
                ? 0.0
                : (phase > 0 && phase < 1 ? 4.0 : 0.0);
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Transform.translate(
                offset: Offset(0, -lift),
                child: CircleAvatar(radius: 3, backgroundColor: widget.color),
              ),
            );
          }),
        );
      },
    );
  }
}
