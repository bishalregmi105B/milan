import 'dart:math' as math;

import 'package:flutter/material.dart';

/// The Milan junction mark, drawn natively (doc 8 §B brand): two people
/// (rings) meeting — the overlap *is* the milan — bridged by a blue arc and
/// crowned by the marigold tika dot. Same geometry as
/// `assets/brand/milan_logo.svg` so the app icon, web and splash match.
class MilanLogoMark extends StatelessWidget {
  const MilanLogoMark({super.key, this.size = 84, this.animation});
  final double size;
  /// 0..1 progress for the intro draw (rings grow in, arc draws, dot drops).
  /// Null renders the static mark (app icon parity).
  final Animation<double>? animation;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      size: Size.square(size),
      painter: _MilanLogoPainter(animation),
    );
  }
}

class _MilanLogoPainter extends CustomPainter {
  _MilanLogoPainter(this.animation);
  final Animation<double>? animation;

  static const crimson = Color(0xFF7B1E3A);
  static const marigold = Color(0xFFF5A623);
  static const actionBlue = Color(0xFF0B84FE);

  @override
  void paint(Canvas canvas, Size size) {
    final t = animation?.value ?? 1.0;
    final scale = size.width / 512;
    final center = Offset(256 * scale, 304 * scale);
    final radius = 108 * scale;
    final strokeWidth = 38 * scale;

    // Rings grow from the centre with a gentle overshoot curve.
    final ringT = math.min(1.0, t / 0.55);
    final eased = Curves.easeOutBack.transform(ringT);
    final ringPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.butt;
    canvas.saveLayer(null, Paint());
    ringPaint.color = crimson;
    canvas.drawCircle(center.translate(-52 * scale, 0), radius * eased, ringPaint);
    ringPaint.color = marigold;
    canvas.drawCircle(center.translate(52 * scale, 0), radius * eased, ringPaint);
    canvas.restore();

    // Bridge arc draws left-to-right after the rings land.
    final arcT = ((t - 0.45) / 0.35).clamp(0.0, 1.0);
    if (arcT > 0) {
      final arcRect = Rect.fromCircle(
          center: center, radius: 144 * scale);
      final sweep = 1.05 + 1.05 * Curves.easeOut.transform(arcT);
      final arcPaint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 24 * scale
        ..strokeCap = StrokeCap.round
        ..color = actionBlue;
      canvas.drawArc(arcRect, math.pi + (1.05 * (1 - arcT)), sweep - 1.05 * (1 - arcT),
          false, arcPaint);
    }

    // Tika dot drops from above with easeOutBack once the arc completes.
    final dotT = ((t - 0.72) / 0.28).clamp(0.0, 1.0);
    if (dotT > 0) {
      final drop = Curves.easeOutBack.transform(dotT);
      final dotY = 112 * scale + (1 - drop) * -40 * scale;
      final dotPaint = Paint()..color = marigold;
      canvas.drawCircle(
          Offset(256 * scale, dotY), 28 * scale * math.min(1.0, dotT * 1.4), dotPaint);
    }
  }

  @override
  bool shouldRepaint(_MilanLogoPainter oldDelegate) =>
      oldDelegate.animation?.value != animation?.value;
}
