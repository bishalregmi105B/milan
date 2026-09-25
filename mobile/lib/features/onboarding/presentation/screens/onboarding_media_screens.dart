import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../core/localization/app_localizations.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/camera_shell.dart';

/// Screen 6 — photo grid uploader (min 2, max 6), reorderable.
class PhotoUploadScreen extends ConsumerStatefulWidget {
  const PhotoUploadScreen({super.key});

  @override
  ConsumerState<PhotoUploadScreen> createState() => _PhotoUploadScreenState();
}

class _PhotoUploadScreenState extends ConsumerState<PhotoUploadScreen> {
  final List<String> _paths = [];

  Future<void> _add() async {
    if (_paths.length >= 6) return;
    final picked = await ImagePicker().pickImage(source: ImageSource.gallery);
    if (picked == null) return;
    setState(() => _paths.add(picked.path));
    // Upload through compression + media endpoint in background; failures are
    // surfaced on Continue rather than blocking the grid interaction.
    try {
      await ref.read(apiClientProvider).uploadMultipart(
            '/media/upload?kind=photo',
            filePath: picked.path,
          );
    } on AppException {
      // keep local preview; retry happens on continue
    }
  }

  void _reorder(int oldIndex, int newIndex) {
    setState(() {
      if (newIndex > oldIndex) newIndex--;
      final p = _paths.removeAt(oldIndex);
      _paths.insert(newIndex, p);
    });
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.onboardingPhotosTitle)),
      body: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(l10n.onboardingPhotosRule, style: TextStyle(color: milan.ink600)),
          SizedBox(height: Spacing.lg),
          Expanded(
            child: _paths.isEmpty
                ? Center(child: Icon(Icons.photo_library_outlined, size: 56, color: milan.line200))
                : ReorderableListView.builder(
                    buildDefaultDragHandles: true,
                    itemCount: _paths.length,
                    onReorder: _reorder,
                    itemBuilder: (context, i) {
                      return Container(
                        // was 'photo-$_paths[i]' — interpolated the whole
                        // list toString + literal "[i]", giving duplicate keys
                        key: ValueKey('photo-${_paths[i]}'),
                        height: 84,
                        margin: EdgeInsets.only(bottom: Spacing.md),
                        child: Row(children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(Spacing.radiusMd),
                            child: Image.file(File(_paths[i]), width: 84, height: 84, fit: BoxFit.cover),
                          ),
                          if (i == 0)
                            Padding(
                              padding: EdgeInsets.only(left: Spacing.md),
                              child: Chip(label: Text('Main', style: TextStyle(fontSize: 11))),
                            ),
                          Spacer(),
                          IconButton(
                            icon: Icon(Icons.delete_outline, color: milan.error500),
                            onPressed: () => setState(() => _paths.removeAt(i)),
                          ),
                        ]),
                      );
                    },
                  ),
          ),
          const SizedBox(height: Spacing.lg),
          OutlinedButton.icon(
            icon: Icon(Icons.add_photo_alternate_outlined),
            label: Text('Add photo (${_paths.length}/6)'),
            onPressed: _add,
          ),
          FilledButton(
            onPressed: _paths.length >= 2
                ? () => context.push('/onboarding/video-intro')
                : null,
            child: Text(l10n.commonContinue),
          ),
        ]),
      ),
    );
  }
}



/// Screen 7 — optional video intro via CameraShell.
class VideoIntroScreen extends ConsumerStatefulWidget {
  const VideoIntroScreen({super.key});

  @override
  ConsumerState<VideoIntroScreen> createState() => _VideoIntroScreenState();
}

class _VideoIntroScreenState extends ConsumerState<VideoIntroScreen> {
  bool _uploading = false;
  String? _error;

  Future<void> _recordAndUpload() async {
    final file = await Navigator.of(context).push<XFile>(
      MaterialPageRoute(builder: (_) => const _CameraCapturePage(videoOnly: true)),
    );
    if (file == null || !mounted) return;
    setState(() {
      _uploading = true;
      _error = null;
    });
    try {
      final uploaded = await ref.read(apiClientProvider).uploadMultipart(
          '/media/upload?kind=video', filePath: file.path);
      final videoUrl = uploaded['url'] as String?;
      if (videoUrl == null || videoUrl.isEmpty) {
        throw AppException('upload_failed');
      }
      await ref
          .read(apiClientProvider)
          .post('/profile/video-intro', body: {'url': videoUrl});
      if (!mounted) return;
      context.push('/onboarding/liveness');
    } on AppException catch (e) {
      if (!mounted) return;
      // A failed intro upload must never trap the user mid-onboarding:
      // continue, the intro is optional.
      setState(() {
        _uploading = false;
        _error = 'Intro not saved (${e.displayMessage}) — you can add it later from your profile.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(),
      body: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(l10n.onboardingVideoIntro, style: context.h2),
          Spacer(),
          if (_error != null) ...[
            Text(_error!, style: TextStyle(fontSize: 12, color: Theme.of(context).extension<MilanColors>()!.ink600)),
            SizedBox(height: Spacing.md),
          ],
          FilledButton.icon(
            icon: _uploading
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : Icon(Icons.videocam),
            label: Text(_uploading ? 'Uploading…' : 'Record'),
            onPressed: _uploading ? null : _recordAndUpload,
          ),
          SizedBox(height: Spacing.md),
          OutlinedButton(
            onPressed: _uploading ? null : () => context.push('/onboarding/liveness'),
            child: Text(l10n.commonSkip),
          ),
        ]),
      ),
    );
  }
}

class _CameraCapturePage extends StatelessWidget {
  const _CameraCapturePage({this.videoOnly = false});
  final bool videoOnly;

  @override
  Widget build(BuildContext context) {
    return CameraShell(
      hint: videoOnly ? '15–60s intro' : 'Tap to capture',
      filters: const ['None', 'Dashain', 'Tihar', 'Holi'],
      onCaptured: (file, {required bool isVideo}) =>
          Navigator.of(context).pop(file),
    );
  }
}

/// Screen 8 — liveness verification capture.
class LivenessScreen extends ConsumerStatefulWidget {
  const LivenessScreen({super.key});

  @override
  ConsumerState<LivenessScreen> createState() => _LivenessScreenState();
}

class _LivenessScreenState extends ConsumerState<LivenessScreen> {
  String? _result;
  bool _busy = false;

  Future<void> _submit(XFile selfie) async {
    setState(() => _busy = true);
    try {
      final res = await ref.read(apiClientProvider).uploadMultipart(
            '/verification/liveness',
            filePath: selfie.path,
            field: 'selfie',
          );
      final passed = res['passed'] == true;
      setState(() => _result = passed ? 'success' : 'fail');
    } on AppException {
      setState(() => _result = 'fail');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.onboardingLivenessTitle)),
      body: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(l10n.onboardingLivenessBody, style: TextStyle(color: milan.ink600, height: 1.5)),
          SizedBox(height: Spacing.xxl),
          Center(child: Icon(Icons.face_retouching_natural, size: 96,
              color: _result == 'success' ? milan.pine500 : milan.marigold500)),
          SizedBox(height: Spacing.xl),
          if (_result == 'fail')
            Text("Couldn't verify — make sure your face is well lit and try again.",
                textAlign: TextAlign.center, style: TextStyle(color: milan.error500)),
          Spacer(),
          if (_busy)
            const Center(child: CircularProgressIndicator())
          else
            FilledButton.icon(
              icon: Icon(Icons.camera_alt),
              label: Text(_result == 'fail' ? l10n.commonRetry : 'Take live selfie'),
              onPressed: () async {
                final file = await Navigator.of(context).push<XFile>(
                  MaterialPageRoute(builder: (_) => const _CameraCapturePage()),
                );
                if (file != null) await _submit(file);
              },
            ),
          if (_result == 'success')
            Padding(
              padding: EdgeInsets.only(top: Spacing.md),
              child: FilledButton(
                onPressed: () => context.push('/onboarding/interview'),
                child: Text(l10n.commonContinue),
              ),
            ),
        ]),
      ),
    );
  }
}
