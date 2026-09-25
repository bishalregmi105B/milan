import 'package:flutter/material.dart';

import '../../app/theme/color_tokens.dart';
import '../../app/theme/spacing_tokens.dart';

/// One dialog factory so success/error/confirm/info alerts look identical
/// everywhere (colored circle icon + title + message + actions), instead of
/// each call site hand-rolling an AlertDialog.
enum MilanDialogKind { success, error, confirm, info }

class MilanDialog {
  static Future<bool> show(
    BuildContext context, {
    required MilanDialogKind kind,
    required String title,
    String? message,
    String confirmLabel = 'OK',
    String? cancelLabel,
  }) async {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final (icon, color) = switch (kind) {
      MilanDialogKind.success => (Icons.check_circle_rounded, milan.pine500),
      MilanDialogKind.error => (Icons.error_rounded, milan.error500),
      MilanDialogKind.confirm => (Icons.help_rounded, milan.dhaka500),
      MilanDialogKind.info => (Icons.info_rounded, milan.dhaka500),
    };
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(Spacing.radiusLg)),
        title: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: color.withValues(alpha: 0.14),
              child: Icon(icon, color: color),
            ),
            SizedBox(height: Spacing.md),
            Text(title,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
          ],
        ),
        content: message == null
            ? null
            : Text(message, textAlign: TextAlign.center),
        actionsAlignment: MainAxisAlignment.center,
        actions: [
          if (cancelLabel != null)
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: Text(cancelLabel),
            ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(confirmLabel),
          ),
        ],
      ),
    );
    return result ?? false;
  }
}
