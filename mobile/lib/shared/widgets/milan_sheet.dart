import 'package:flutter/material.dart';

import '../../app/theme/color_tokens.dart';
import '../../app/theme/spacing_tokens.dart';

/// Standardized bottom sheet (NNGroup bottom-sheet guidance): a grab handle for
/// affordance PLUS a visible close button (the handle alone is inaccessible to
/// screen readers and imprecise swipers), rounded top, safe-area padding, and
/// ordinary back-gesture dismissal. Use [showMilanSheet] instead of calling
/// showModalBottomSheet with an ad-hoc layout so every sheet looks the same.
Future<T?> showMilanSheet<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  String? title,
  bool isScrollControlled = true,
}) {
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: isScrollControlled,
    backgroundColor: Colors.transparent,
    builder: (context) => MilanSheet(title: title, child: builder(context)),
  );
}

class MilanSheet extends StatelessWidget {
  const MilanSheet({super.key, required this.child, this.title});
  final Widget child;
  final String? title;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Container(
      decoration: BoxDecoration(
        color: milan.paper0,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 10),
            // Grab handle — affordance only, never the sole dismiss control.
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: milan.line200,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Padding(
              padding: EdgeInsets.fromLTRB(Spacing.lg, Spacing.sm, Spacing.sm, 0),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      title ?? '',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                        color: milan.ink900,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    tooltip: 'Close',
                    onPressed: () => Navigator.of(context).maybePop(),
                  ),
                ],
              ),
            ),
            Flexible(
              child: Padding(
                padding: EdgeInsets.fromLTRB(
                    Spacing.lg, 0, Spacing.lg, Spacing.lg),
                child: child,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
