import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/rendering.dart';
import 'package:path_provider/path_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui';

import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/camera_shell.dart';
import '../../application/jhalak_snap_provider.dart';

/// Jhalak snap engine (§Snapchat-style, v2.2):
///   capture  — full-screen camera, live filter carousel (color-matrix LUTs),
///   edit     — draggable text sticker + caption over the filtered shot,
///   bake     — RepaintBoundary.toImage flattens filters + overlay into ONE
///              PNG (what you see is exactly what every viewer gets),
///   post     — upload the flattened image, 24h view-once as before.
class SnapComposerScreen extends ConsumerStatefulWidget {
  const SnapComposerScreen({super.key});

  @override
  ConsumerState<SnapComposerScreen> createState() => _SnapComposerScreenState();
}

class _SnapComposerScreenState extends ConsumerState<SnapComposerScreen> {
  String? _capturedPath;
  String _filter = 'None';
  final _caption = TextEditingController();
  bool _posting = false;

  @override
  void dispose() {
    _caption.dispose();
    super.dispose();
  }

  Future<void> _post() async {
    if (_capturedPath == null || _posting) return;
    setState(() => _posting = true);
    try {
      final uploaded = await ref.read(apiClientProvider).uploadMultipart(
          '/media/upload?kind=photo', filePath: _capturedPath!);
      final url = uploaded['url'] as String?;
      if (url == null || url.isEmpty) {
        throw AppException('upload_failed',
            message: 'The upload did not return a URL — try again.');
      }
      await ref.read(jhalakSnapProvider.notifier).postSnap(
          imageUrl: url, caption: _caption.text, filterKey: _filter);
      if (!mounted) return;
      context.pop(); // review
      context.pop(); // back to the grid, now showing the snap
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() => _posting = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Could not post: ${e.displayMessage}')));
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_capturedPath == null) {
      return CameraShell(
        hint: 'Your 24h Jhalak — view once, then gone',
        filters: const ['None', 'Dashain', 'Tihar', 'Holi', 'Mono', 'Punk'],
        onFilterChanged: (f) => _filter = f,
        onCaptured: (file, {required isVideo}) {
          if (isVideo) return; // snaps are photos only
          setState(() => _capturedPath = file.path);
        },
      );
    }
    return SnapEditScreen(
      imagePath: _capturedPath!,
      posting: _posting,
      onRetake: () => setState(() => _capturedPath = null),
      onPost: (flattenedPath, caption, filter) async {
        setState(() {
          _capturedPath = flattenedPath;
          _caption.text = caption;
          _filter = filter;
          _posting = true;
        });
        await _post();
      },
    );
  }
}

/// Shared festival LUTs — capture preview and the edit bake use THE SAME
/// matrices, so the swatch you pick is the image you get.
class SnapFilters {
  static const names = ['None', 'Dashain', 'Tihar', 'Holi', 'Mono', 'Punk'];
  static const matrices = <String, List<double>>{
    'None': [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0],
    'Dashain': [
      1.12, 0.06, 0, 0, 0.02, 0, 1.04, 0, 0, 0.02, 0, 0, 0.94, 0, 0, 0, 0, 0, 1, 0
    ],
    'Tihar': [
      1.05, 0, 0.08, 0, 0.03, 0, 0.98, 0.05, 0, 0, 0, 0, 1.1, 0, 0.02, 0, 0, 0, 1, 0
    ],
    'Holi': [
      1.15, 0.1, -0.05, 0, 0, -0.02, 1.08, 0.08, 0, 0, 0.05, 0, 1.18, 0, 0.03, 0, 0, 0, 1, 0
    ],
    'Mono': [
      0.33, 0.59, 0.11, 0, 0, 0.33, 0.59, 0.11, 0, 0, 0.33, 0.59, 0.11, 0, 0, 0, 0, 0, 1, 0
    ],
    'Punk': [
      1.3, 0, -0.2, 0, 0.05, 0, 0.6, 0.2, 0, 0, -0.1, 0, 1.25, 0, 0.04, 0, 0, 0, 1, 0
    ],
  };

  static ColorFilter filterFor(String name) {
    final m = matrices[name] ?? matrices['None']!;
    return ColorFilter.matrix(Float64List.fromList(m));
  }

  /// Swatch colour for the carousel chip.
  static Color swatchFor(String name) {
    switch (name) {
      case 'Dashain':
        return const Color(0xFFB8791A);
      case 'Tihar':
        return const Color(0xFFC97D0C);
      case 'Holi':
        return const Color(0xFFE85D9E);
      case 'Mono':
        return const Color(0xFF444444);
      case 'Punk':
        return const Color(0xFF7B1E3A);
      default:
        return const Color(0xFFDDDDDD);
    }
  }
}

/// Post-capture edit stage: filtered image full-screen, draggable text
/// sticker (Snapchat caption-in-space), caption strip, flatten-on-post.
class SnapEditScreen extends StatefulWidget {
  const SnapEditScreen({
    super.key,
    required this.imagePath,
    required this.posting,
    required this.onRetake,
    required this.onPost,
  });

  final String imagePath;
  final bool posting;
  final VoidCallback onRetake;
  /// Called with the path of the FLATTENED image (filters + text baked in).
  final Future<void> Function(String path, String caption, String filter) onPost;

  @override
  State<SnapEditScreen> createState() => _SnapEditScreenState();
}

class _SnapEditScreenState extends State<SnapEditScreen> {
  final _boundaryKey = GlobalKey();
  final _caption = TextEditingController();
  final _textController = TextEditingController();
  Alignment _textOffset = const Alignment(0, -0.3); // alignment-space position
  bool _editingText = false;
  String _filter = 'None';
  bool _baking = false;

  bool get _hasText => _textController.text.trim().isNotEmpty;

  Future<void> _bakeAndPost() async {
    if (_baking) return;
    setState(() => _baking = true);
    try {
      // flatten: image + filter + text overlay → single PNG (WYSIWYG)
      final boundary = _boundaryKey.currentContext!.findRenderObject()
          as RenderRepaintBoundary;
      final image = await boundary.toImage(pixelRatio: 2.0);
      final bytes = await image.toByteData(format: ImageByteFormat.png);
      final temp = await getTemporaryDirectory();
      final file = File(
          '${temp.path}/jhalak_${DateTime.now().millisecondsSinceEpoch}.png');
      await file.writeAsBytes(bytes!.buffer.asUint8List());
      await widget.onPost(file.path, _caption.text, _filter);
    } catch (_) {
      if (!mounted) return;
      setState(() => _baking = false);
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Could not process the snap — try again.')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(children: [
        // the bake source — everything inside this boundary is flattened
        RepaintBoundary(
          key: _boundaryKey,
          child: Stack(fit: StackFit.expand, children: [
            ColorFiltered(
              colorFilter: SnapFilters.filterFor(_filter),
              child: Image.file(File(widget.imagePath),
                  fit: BoxFit.cover),
            ),
            // draggable text sticker
            if (_hasText)
              Align(
                alignment: _textOffset,
                child: GestureDetector(
                  onPanUpdate: (d) => setState(() {
                    _textOffset = Alignment(
                        (_textOffset.x + d.delta.dx / 180).clamp(-1.0, 1.0),
                        (_textOffset.y + d.delta.dy / 320).clamp(-1.0, 1.0));
                  }),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 8),
                    constraints: const BoxConstraints(maxWidth: 280),
                    decoration: BoxDecoration(
                        color: Colors.black45,
                        borderRadius: BorderRadius.circular(10)),
                    child: Text(_textController.text.trim(),
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 22,
                            fontWeight: FontWeight.w800)),
                  ),
                ),
              ),
          ]),
        ),
        SafeArea(
          child: Column(children: [
            Padding(
              padding: EdgeInsets.all(Spacing.lg),
              child: Row(children: [
                IconButton(
                    icon: const Icon(Icons.close, color: Colors.white),
                    onPressed: widget.onRetake),
                const Spacer(),
                if (!_hasText)
                  IconButton(
                      tooltip: 'Add text',
                      icon: const Icon(Icons.text_fields, color: Colors.white),
                      onPressed: () =>
                          setState(() => _editingText = !_editingText)),
              ]),
            ),
            const Spacer(),
            // filter carousel — circular swatches, Snapchat-style
            SizedBox(
              height: 56,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                shrinkWrap: true,
                padding: const EdgeInsets.symmetric(horizontal: 24),
                itemCount: SnapFilters.names.length,
                separatorBuilder: (_, __) => const SizedBox(width: 12),
                itemBuilder: (context, i) {
                  final name = SnapFilters.names[i];
                  final selected = _filter == name;
                  return GestureDetector(
                    onTap: () => setState(() => _filter = name),
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      Container(
                        width: 42,
                        height: 42,
                        decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: SnapFilters.swatchFor(name),
                            border: Border.all(
                                color: selected ? Colors.white : Colors.white30,
                                width: selected ? 3 : 1.5)),
                      ),
                      const SizedBox(height: 3),
                      Text(name,
                          style: TextStyle(
                              fontSize: 10,
                              color: selected ? Colors.white : Colors.white60)),
                    ]),
                  );
                },
              ),
            ),
            // caption + text editor
            Padding(
              padding: EdgeInsets.all(Spacing.lg),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                if (_editingText)
                  Row(children: [
                    Expanded(
                      child: TextField(
                        controller: _textController,
                        autofocus: true,
                        maxLength: 60,
                        style: const TextStyle(color: Colors.white),
                        onChanged: (_) => setState(() {}),
                        decoration: InputDecoration(
                          hintText: 'Text on snap…',
                          hintStyle: const TextStyle(color: Colors.white38),
                          counterStyle: const TextStyle(color: Colors.white24),
                          filled: true,
                          fillColor: Colors.white12,
                          border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(24),
                              borderSide: BorderSide.none),
                        ),
                      ),
                    ),
                    IconButton(
                        icon: const Icon(Icons.check, color: Colors.white),
                        onPressed: () => setState(() => _editingText = false)),
                  ])
                else
                  TextField(
                    controller: _caption,
                    maxLength: 280,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      hintText: 'Caption…',
                      hintStyle: const TextStyle(color: Colors.white38),
                      counterStyle: const TextStyle(color: Colors.white24),
                      filled: true,
                      fillColor: Colors.white12,
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(24),
                          borderSide: BorderSide.none),
                    ),
                  ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: (_baking || widget.posting) ? null : _bakeAndPost,
                    icon: (_baking || widget.posting)
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : const Icon(Icons.flash_on_rounded),
                    label: Text((_baking || widget.posting)
                        ? 'Posting…'
                        : 'Send · 24h · view once'),
                  ),
                ),
              ]),
            ),
          ]),
        ),
      ]),
    );
  }
}

/// Author control screen: my live snaps, who viewed, who screenshotted.
class MySnapsScreen extends ConsumerStatefulWidget {
  const MySnapsScreen({super.key});

  @override
  ConsumerState<MySnapsScreen> createState() => _MySnapsScreenState();
}

class _MySnapsScreenState extends ConsumerState<MySnapsScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() =>
      ref.read(apiClientProvider).get<Map<String, dynamic>>('/jhalak/snaps/mine');

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    return Scaffold(
      appBar: AppBar(title: const Text('My Jhalaks')),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('Could not load your snaps.',
                style: TextStyle(color: milan.ink600)));
          }
          final snaps = (snapshot.data?['snaps'] as List? ?? const []);
          if (snaps.isEmpty) {
            return Center(child: Text('No live snaps — post one!',
                style: TextStyle(color: milan.ink600)));
          }
          return ListView.builder(
            padding: EdgeInsets.all(Spacing.lg),
            itemCount: snaps.length,
            itemBuilder: (context, i) {
              final snap = snaps[i] as Map<String, dynamic>;
              final viewers = (snap['viewers'] as List? ?? const []);
              final shots = viewers.where((v) => (v as Map<String, dynamic>)['screenshot'] == true).length;
              return Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: EdgeInsets.all(Spacing.lg),
                decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(Spacing.radiusLg),
                    border: Border.all(color: milan.line200)),
                child: Row(children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(Spacing.radiusMd),
                    child: CachedNetworkImage(
                        imageUrl: snap['media_url'] as String? ?? '',
                        width: 64, height: 64, fit: BoxFit.cover,
                        errorWidget: (_, __, ___) => Container(
                            width: 64, height: 64, color: milan.paper100)),
                  ),
                  SizedBox(width: Spacing.md),
                  Expanded(
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                      Text('${snap['view_count'] ?? 0} views',
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 2),
                      Text(
                        viewers.isEmpty
                            ? 'Not viewed yet'
                            : 'Seen by ${(viewers.cast<Map<String, dynamic>>()).map((v) => v['name']).take(3).join(', ')}'
                            '${viewers.length > 3 ? ' +${viewers.length - 3}' : ''}',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12.5, color: milan.ink400),
                      ),
                      if (shots > 0)
                        Text('$shots screenshot${shots == 1 ? '' : 's'} 📸',
                            style: TextStyle(fontSize: 12, color: milan.error500)),
                    ]),
                  ),
                  IconButton(
                      tooltip: 'Delete snap',
                      icon: Icon(Icons.delete_outline, color: milan.ink400),
                      onPressed: () async {
                        try {
                          await ref
                              .read(apiClientProvider)
                              .delete<Map<String, dynamic>>(
                                  '/jhalak/snaps/${snap['id']}');
                        } on AppException {
                          // removal is best-effort; the list refresh decides
                        }
                        await ref
                            .read(jhalakSnapProvider.notifier)
                            .refresh();
                        if (mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('Snap deleted')));
                          setState(() => _future = _load());
                        }
                      }),
                ]),
              );
            },
          );
        },
      ),
    );
  }
}
