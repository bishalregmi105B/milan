import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/localization/app_localizations.dart';
import '../../../../core/network/api_client.dart';

/// Screen 53 — "What Saathi Remembers": real per-item-deletable data view,
/// not a static privacy page (doc 3 §6).
class SaathiMemoryScreen extends ConsumerStatefulWidget {
  const SaathiMemoryScreen({super.key, required this.sessionId});
  final String sessionId;

  @override
  ConsumerState<SaathiMemoryScreen> createState() => _SaathiMemoryScreenState();
}

class _SaathiMemoryScreenState extends ConsumerState<SaathiMemoryScreen> {
  List<Map<String, dynamic>>? _items;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await ref.read(apiClientProvider).get<Map<String, dynamic>>(
          '/saathi/sessions/${widget.sessionId}/memory');
      if (!mounted) return;
      setState(() => _items = (res['items'] as List).cast<Map<String, dynamic>>());
    } on AppException {
      if (!mounted) return;
      setState(() => _items = []);
    }
  }

  Future<void> _delete(String itemId) async {
    await ref.read(apiClientProvider).delete(
        '/saathi/sessions/${widget.sessionId}/memory/$itemId');
    // Deleting actually removes it from what feeds future prompts (doc 5 §2.4).
    _load();
  }

  Future<void> _clearAll() async {
    await ref.read(apiClientProvider).delete(
        '/saathi/sessions/${widget.sessionId}/memory');
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: Text(AppLocalizations.of(context)!.saathiMemoryTitle)),
      body: !_items.isNullOrEmpty
          ? ListView.separated(
              padding: EdgeInsets.all(Spacing.xl),
              itemCount: _items!.length + 1,
              separatorBuilder: (_, __) => SizedBox(height: Spacing.md),
              itemBuilder: (context, i) {
                if (i == _items!.length) {
                  return TextButton.icon(
                    icon: Icon(Icons.delete_sweep_outlined, color: milan.error500),
                    label: Text(AppLocalizations.of(context)!.saathiMemoryClearAll,
                        style: TextStyle(color: milan.error500)),
                    onPressed: _clearAll,
                  );
                }
                final item = _items![i];
                return Container(
                  padding: EdgeInsets.all(Spacing.lg),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(Spacing.radiusMd),
                  ),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(item['summary_text'] ?? '',
                              style: const TextStyle(height: 1.4)),
                          if (item['category'] != null)
                            Padding(padding: EdgeInsets.only(top: Spacing.sm),
                                child: Text(item['category'].toString(),
                                    style: TextStyle(fontSize: 10, color: milan.ink400))),
                        ])),
                    IconButton(icon: Icon(Icons.close, size: 18, color: milan.ink400),
                        onPressed: () => _delete(item['id'] as String)),
                  ]),
                );
              },
            )
          : Center(child: Text('Nothing stored yet.',
              style: TextStyle(color: milan.ink600))),
    );
  }
}

extension _ListX on List<Map<String, dynamic>>? {
  bool get isNullOrEmpty => this == null || this!.isEmpty;
}
