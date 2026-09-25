import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/camera_shell.dart';
import '../../../../shared/widgets/common.dart' show StoryRing;

/// Screen 38 — reel composer: prompt-of-the-day overlay + trim placeholder.
/// Screen 39 — duet recorder: split-screen with original pinned.
class DuetRecorderScreen extends ConsumerWidget {
  const DuetRecorderScreen({super.key, required this.reelId});
  final String reelId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Duet')),
      body: Column(children: [
        // Original clip pinned on top, audio plays while recording the new half.
        Container(height: 220, color: Colors.black87,
            child: Center(child: Icon(Icons.play_circle_fill, size: 56, color: Colors.white24))),
        Expanded(child: CameraShell(
          hint: 'Record your half',
          filters: const ['None', 'Dashain', 'Tihar', 'Holi'],
          onCaptured: (file, {required isVideo}) async {
              try {
                final uploaded = await ref.read(apiClientProvider).uploadMultipart(
                    '/media/upload?kind=video', filePath: file.path);
                final videoUrl = uploaded['url'] as String?;
                if (videoUrl == null || videoUrl.isEmpty) throw AppException('upload_failed');
                await ref.read(apiClientProvider).post('/jhalak/reels/$reelId/duet',
                    body: {'video_url': videoUrl});
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Duet posted to Jhalak.')));
              } on AppException {
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                    content: Text('Could not post the duet. Try again.')));
              }
              if (context.mounted) context.pop();
            },
        )),
      ]),
    );
  }
}

/// Screen 40 — stories bar (home top rail).
class StoriesBarScreen extends ConsumerWidget {
  const StoriesBarScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Stories')),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        SizedBox(height: 96, child: ListView(scrollDirection: Axis.horizontal, children: [
          for (final name in ['Your vibe', 'Sunita', 'Bikash', 'Anisha'])
            Padding(padding: EdgeInsets.only(right: Spacing.lg),
                child: Column(children: [
                  StoryRing(seen: name == 'Sunita',
                      child: CircleAvatar(radius: 26, child: Icon(Icons.person))),
                  SizedBox(height: Spacing.sm),
                  Text(name, style: TextStyle(fontSize: 11)),
                ])),
        ])),
      ]),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/jhalak/stories/camera'),
        child: const Icon(Icons.add_a_photo_outlined),
      ),
    );
  }
}

/// Screen 41 — full-screen story viewer.
class StoryViewerScreen extends StatefulWidget {
  const StoryViewerScreen({super.key, required this.userId});
  final String userId;

  @override
  State<StoryViewerScreen> createState() => _StoryViewerScreenState();
}

class _StoryViewerScreenState extends State<StoryViewerScreen> {
  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(fit: StackFit.expand, children: [
        ColoredBox(color: milan.ink900),
        // Tap zones advance; reply field at bottom (doc 2 §3.5).
        Row(children: [
          Expanded(child: GestureDetector(onTap: () {}, child: const SizedBox.expand())),
          Expanded(child: GestureDetector(onTap: () {}, child: const SizedBox.expand())),
        ]),
        SafeArea(child: Padding(
          padding: EdgeInsets.all(Spacing.lg),
          child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
            LinearProgressIndicator(value: .35, color: Colors.white, backgroundColor: Colors.white24),
            SizedBox(height: Spacing.lg),
            Row(children: [
              CircleAvatar(radius: 16, child: Icon(Icons.person, size: 14)),
              SizedBox(width: Spacing.sm),
              Text('aaja ko vibe · 2h', style: TextStyle(color: Colors.white70, fontSize: 12)),
            ]),
            SizedBox(height: Spacing.md),
            Row(children: [
              Expanded(child: TextField(style: TextStyle(color: Colors.white),
                  decoration: InputDecoration(hintText: 'Reply…',
                      hintStyle: TextStyle(color: Colors.white38),
                      filled: true, fillColor: Colors.white12))),
              IconButton(icon: Icon(Icons.favorite_border, color: Colors.white), onPressed: () {}),
            ]),
          ]),
        )),
      ]),
    );
  }
}

/// Screen 42 — story camera with daily prompt sticker.
class StoryCameraScreen extends StatelessWidget {
  const StoryCameraScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return CameraShell(
      hint: 'Aaja ko vibe?',
      filters: const ['None', 'Dashain', 'Tihar', 'Holi'],
      onCaptured: (file, {required isVideo}) => Navigator.pop(context),
    );
  }
}

/// Screens 43+44 — circles directory + detail.
class CirclesDirectoryScreen extends ConsumerWidget {
  const CirclesDirectoryScreen({super.key});

  static const _categories = ['All', 'Trekking', 'Football', 'Music', 'College', 'Hometown'];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Circles')),
      body: Column(children: [
        SizedBox(height: 48, child: ListView(scrollDirection: Axis.horizontal,
            padding: EdgeInsets.symmetric(horizontal: Spacing.xl),
            children: [for (final c in _categories) Padding(
                padding: EdgeInsets.only(right: Spacing.md),
                child: Chip(label: Text(c)))])),
        Expanded(child: GridView.count(crossAxisCount: 2,
            padding: EdgeInsets.all(Spacing.xl),
            mainAxisSpacing: Spacing.lg, crossAxisSpacing: Spacing.lg,
            childAspectRatio: 1.1,
            children: [
              for (final circle in [('Pokhara Trekkers', 'Trekking'), ('Futsal Fridays', 'Football'),
                    ('KTM Indie Music', 'Music'), ('TU Batch 19', 'College')])
                Card(elevation: 0, color: Theme.of(context).colorScheme.surfaceContainerHighest,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(Spacing.radiusLg)),
                    child: InkWell(borderRadius: BorderRadius.circular(Spacing.radiusLg),
                        onTap: () {},
                        child: Padding(padding: EdgeInsets.all(Spacing.lg),
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center, children: [
                                  Icon(Icons.diversity_3_outlined, size: 28,
                                      color: Theme.of(context).extension<MilanColors>()!.dhaka500),
                                  SizedBox(height: Spacing.md),
                                  Text(circle.$1, style: const TextStyle(fontWeight: FontWeight.w700)),
                                  Text(circle.$2, style: TextStyle(fontSize: 11,
                                      color: Theme.of(context).extension<MilanColors>()!.ink400)),
                                ])))),
            ])),
      ]),
    );
  }
}

/// Screen 45 — live audio room: speaker grid + raise-hand queue over sockets.
class LiveAudioRoomScreen extends ConsumerStatefulWidget {
  const LiveAudioRoomScreen({super.key, required this.circleId});
  final String circleId;

  @override
  ConsumerState<LiveAudioRoomScreen> createState() => _LiveAudioRoomScreenState();
}

class _LiveAudioRoomScreenState extends ConsumerState<LiveAudioRoomScreen> {
  bool _handRaised = false;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Live room')),
      body: Column(children: [
        Expanded(child: GridView.count(crossAxisCount: 3, padding: EdgeInsets.all(Spacing.xl),
            mainAxisSpacing: Spacing.lg, crossAxisSpacing: Spacing.lg,
            children: [
              for (final speaker in ['Host', 'You', '+'])
                Column(mainAxisSize: MainAxisSize.min, children: [
                  CircleAvatar(radius: 30, backgroundColor: milan.dhaka100,
                      child: Icon(Icons.mic, color: milan.dhaka500)),
                  SizedBox(height: Spacing.sm),
                  Text(speaker, style: TextStyle(fontSize: 11)),
                ]),
            ])),
        Padding(padding: EdgeInsets.all(Spacing.xl), child: Row(children: [
          Expanded(child: OutlinedButton.icon(
              icon: Icon(_handRaised ? Icons.front_hand : Icons.front_hand_outlined),
              label: Text(_handRaised ? 'Hand raised' : 'Raise hand'),
              onPressed: () => setState(() => _handRaised = !_handRaised))),
          SizedBox(width: Spacing.lg),
          FilledButton(onPressed: () => context.pop(), child: Text('Leave')),
        ])),
      ]),
    );
  }
}


/// Route host for circle detail (screen 44) — member grid, next room, join.
class CircleDetailRoute extends ConsumerWidget {
  const CircleDetailRoute({super.key, required this.circleId});
  final String circleId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Circle')),
      body: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Expanded(child: GridView.count(crossAxisCount: 4, padding: EdgeInsets.all(Spacing.xl),
            mainAxisSpacing: Spacing.md, crossAxisSpacing: Spacing.md,
            children: [for (var i = 0; i < 8; i++) CircleAvatar(radius: 24,
                backgroundColor: milan.paper100, child: Icon(Icons.person, size: 18))])),
        SafeArea(child: Padding(padding: EdgeInsets.all(Spacing.xl), child: Row(children: [
          Expanded(child: FilledButton.icon(icon: Icon(Icons.graphic_eq),
              label: const Text('Next live room'), onPressed:
                  () => context.push('/jhalak/circles/$circleId/room'))),
          SizedBox(width: Spacing.lg),
          OutlinedButton(onPressed: () async {
            try {
              await ref
                  .read(apiClientProvider)
                  .post('/jhalak/circles/$circleId/join');
              if (context.mounted) context.pop();
            } on AppException catch (e) {
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                  content: Text('Could not join circle (${e.code})'),
                ));
              }
            }
          }, child: const Text('Join')),
        ]))),
      ]),
    );
  }
}
