import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/theme/chat_theme_tokens.dart';
import '../../app/theme/color_tokens.dart';
import '../../app/theme/spacing_tokens.dart';
import '../../app/theme/accent_theme.dart';

/// Messenger-style bubble (global chat redesign): white chat surface, accent
/// (blue-by-default, user-selectable) sent bubbles, soft grey received,
/// asymmetric radii opening toward the sender edge, compact in-bubble
/// timestamp. AI-labelled variant keeps a dashed disclosure border for the
/// companion surface only — the tag lives in the AppBar, per-message tagging
/// was removed (build brief §2).
class ChatBubble extends ConsumerWidget {
  const ChatBubble({
    super.key,
    required this.text,
    required this.isSent,
    this.isAi = false,
    this.bubbleColor,
    this.bubbleShape = BubbleShape.rounded,
    this.timestamp,
    this.read = false,
    this.onTap,
    this.accentColor,
  });

  final String text;
  final bool isSent;
  final bool isAi;
  final Color? bubbleColor;
  final BubbleShape bubbleShape;
  final DateTime? timestamp;
  final bool read;
  final VoidCallback? onTap;
  final Color? accentColor;

  /// Messenger-parity default accent — overridable by the user's theme pick.
  static const Color defaultAccent = Color(0xFF38BDF8);
  static const Color receivedFill = Color(0xFFFFFFFF);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final radiusValue =
        bubbleShape == BubbleShape.compact ? Spacing.radiusMd : Spacing.radiusLg;

    final userAccent = ref.watch(accentThemeProvider).accent;
    final accent = accentColor ?? userAccent;
    final Color fill = isAi
        ? milan.dhaka100
        : (bubbleColor ?? (isSent ? accent : receivedFill));
    // Contrast-gated (doc 8 §B): a light custom accent flips sent text to ink.
    final Color textColor =
        isSent ? AccentThemeState.readableOn(fill) : milan.ink900;

    // Messenger asymmetry: the corner nearest the sender stays square.
    final BorderRadius radii = isSent
        ? BorderRadius.only(
            topLeft: Radius.circular(radiusValue),
            topRight: Radius.circular(radiusValue),
            bottomLeft: Radius.circular(radiusValue),
            bottomRight: Radius.circular(4),
          )
        : BorderRadius.only(
            topLeft: Radius.circular(radiusValue),
            topRight: Radius.circular(radiusValue),
            bottomLeft: Radius.circular(4),
            bottomRight: Radius.circular(radiusValue),
          );

    return Align(
      alignment: isSent ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
        onLongPress: () => _showTimestampSheet(context),
        onTap: onTap,
        child: Container(
          margin: EdgeInsets.symmetric(vertical: 3, horizontal: Spacing.lg),
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 13),
          constraints:
              BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.76),
          decoration: BoxDecoration(
            color: fill,
            borderRadius: radii,
            border: isAi
                ? Border.all(color: milan.dhaka500, strokeAlign: BorderSide.strokeAlignInside)
                : null,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(text,
                  style: TextStyle(
                      color: textColor, fontSize: 15.5, height: 1.32)),
              const SizedBox(height: 3),
              Row(mainAxisSize: MainAxisSize.min, children: [
                if (timestamp != null)
                  Text(_format(timestamp!),
                      style: TextStyle(
                          fontSize: 10.5,
                          color: isSent
                              ? textColor.withValues(alpha: 0.7)
                              : milan.ink400)),
                if (isSent && read) ...[
                  const SizedBox(width: 4),
                  Icon(Icons.done_all,
                      size: 13, color: textColor.withValues(alpha: 0.7)),
                ],
              ]),
            ],
          ),
        ),
      ),
    );
  }

  void _showTimestampSheet(BuildContext context) {
    if (timestamp == null) return;
    showModalBottomSheet<void>(
      context: context,
      builder: (sheetContext) => Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Text(_format(timestamp!)),
      ),
    );
  }

  String _format(DateTime time) =>
      '${time.hour.toString().padLeft(2, '0')}:${time.minute.toString().padLeft(2, '0')}';
}

/// Doc 3 §6 — ephemeral-snap variant with a timer ring.
class SnapBubble extends StatelessWidget {
  const SnapBubble({super.key, required this.thumbnailUrl, this.expired = false});
  final String thumbnailUrl;
  final bool expired;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        width: 96,
        height: 96,
        margin: EdgeInsets.symmetric(vertical: Spacing.xs, horizontal: Spacing.lg),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(Spacing.radiusLg),
          image: expired
              ? null
              : DecorationImage(image: NetworkImage(thumbnailUrl), fit: BoxFit.cover),
          color: milan.paper100,
        ),
        child: expired
            ? Icon(Icons.hourglass_empty, color: milan.ink400)
            : Stack(children: [
                Positioned(
                  right: Spacing.sm,
                  top: Spacing.sm,
                  child: CircleAvatar(
                    radius: 11,
                    backgroundColor: Colors.black54,
                    child: Icon(Icons.timer, size: 13, color: Colors.white),
                  ),
                ),
              ]),
      ),
    );
  }
}

/// Messenger-style typing bubble — the 3-dot animation as a received bubble.
class TypingBubble extends StatelessWidget {
  const TypingBubble({super.key});
  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 3, horizontal: Spacing.lg),
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
        decoration: BoxDecoration(
          color: ChatBubble.receivedFill,
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(Spacing.radiusLg),
            topRight: Radius.circular(Spacing.radiusLg),
            bottomLeft: Radius.circular(4),
            bottomRight: Radius.circular(Spacing.radiusLg),
          ),
        ),
        child: const TypingDots(),
      ),
    );
  }
}

class TypingDots extends StatefulWidget {
  const TypingDots({super.key});
  @override
  State<TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<TypingDots> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 1100))..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) {
        return Row(mainAxisSize: MainAxisSize.min, children: [
          for (var i = 0; i < 3; i++)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2.5),
              child: Opacity(
                opacity: [0.35, 0.65, 1.0][(_c.value * 3).floor() % 3 == i ? 2 : 0],
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                      color: Color(0xFF8A919C), shape: BoxShape.circle),
                ),
              ),
            ),
        ]);
      },
    );
  }
}
