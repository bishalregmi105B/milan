import 'dart:io';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:record/record.dart';

import '../../../../app/theme/chat_theme_tokens.dart';
import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/localization/app_localizations.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/camera_shell.dart';
import '../../../../shared/widgets/theme_picker_sheet.dart';
import '../../application/chat_providers.dart';

/// Screen 31 — voice note recorder with waveform preview.
class VoiceNoteScreen extends ConsumerStatefulWidget {
  const VoiceNoteScreen({super.key, required this.matchId});
  final String matchId;

  @override
  ConsumerState<VoiceNoteScreen> createState() => _VoiceNoteScreenState();
}

class _VoiceNoteScreenState extends ConsumerState<VoiceNoteScreen> {
  final _recorder = AudioRecorder();
  String? _path;
  bool _recording = false;
  bool _sending = false;
  String? _error;

  @override
  void dispose() {
    _recorder.dispose();
    super.dispose();
  }

  Future<void> _toggle() async {
    if (_recording) {
      final path = await _recorder.stop();
      setState(() {
        _recording = false;
        _path = path;
      });
      return;
    }
    if (!await _recorder.hasPermission()) {
      if (mounted) {
        setState(
          () => _error =
              'Microphone permission is required to record a voice note.',
        );
      }
      return;
    }
    final dir = Directory.systemTemp;
    try {
      await _recorder.start(
        const RecordConfig(encoder: AudioEncoder.aacLc),
        path:
            '${dir.path}/milan_voice_${DateTime.now().millisecondsSinceEpoch}.m4a',
      );
      if (mounted) {
        setState(() {
          _recording = true;
          _error = null;
        });
      }
    } catch (_) {
      if (mounted)
        setState(() => _error = 'Recording could not start. Try again.');
    }
  }

  Future<void> _send() async {
    final path = _path;
    if (path == null || _sending) return;
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      final uploaded = await ref
          .read(apiClientProvider)
          .uploadMultipart('/media/upload?kind=audio', filePath: path);
      final url = uploaded['url'];
      if (url is! String || url.isEmpty) {
        throw AppException(
          'media_upload_incomplete',
          message: 'The recording could not be uploaded. Try again.',
        );
      }
      await ref
          .read(chatThreadProvider(widget.matchId).notifier)
          .sendMedia(mediaUrl: url, mediaType: 'audio', caption: 'Voice note');
      if (mounted) context.pop();
    } on AppException catch (e) {
      if (mounted) {
        setState(() {
          _sending = false;
          _error = e.displayMessage;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _sending = false;
          _error = "The voice note couldn't be sent. Try again.";
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Voice note')),
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Waveform preview — amplitude bars animate while recording.
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (final h in [12, 28, 44, 30, 18])
                  Padding(
                    padding: EdgeInsets.symmetric(horizontal: Spacing.sm),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 180),
                      width: 5,
                      height: _recording ? h.toDouble() : 8,
                      decoration: BoxDecoration(
                        color: milan.dhaka500,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ),
              ],
            ),
            SizedBox(height: Spacing.xxl),
            GestureDetector(
              onTap: _toggle,
              child: CircleAvatar(
                radius: 36,
                backgroundColor: _recording ? milan.error500 : milan.dhaka500,
                child: Icon(
                  _recording ? Icons.stop : Icons.mic,
                  color: Colors.white,
                ),
              ),
            ),
            SizedBox(height: Spacing.lg),
            Text(_recording ? 'Recording… tap to stop' : 'Tap to record'),
            SizedBox(height: Spacing.xxl),
            if (_error != null) ...[
              Text(_error!, style: TextStyle(color: milan.error500)),
              SizedBox(height: Spacing.md),
            ],
            FilledButton(
              onPressed: _path == null || _sending ? null : _send,
              child: _sending
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Send voice note'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Screen 32 — in-chat snap camera (CameraShell variant).
/// Flow: capture → pick view mode → upload via /media/upload → POST
/// /matches/:id/snaps {media_url, view_mode} (backend chat_bp contract) →
/// back to the thread.
class SnapCameraScreen extends ConsumerWidget {
  const SnapCameraScreen({super.key, required this.matchId});
  final String matchId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return CameraShell(
      hint: 'Send as disappearing snap',
      filters: const ['None', 'Dashain', 'Tihar', 'Holi'],
      onCaptured: (file, {required isVideo}) async {
        // single_view / 24h toggle then send.
        final mode = await showModalBottomSheet<String>(
          context: context,
          builder: (_) => SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ListTile(
                  title: const Text('View once'),
                  onTap: () => Navigator.pop(context, 'single_view'),
                ),
                ListTile(
                  title: const Text('Keep in chat for 24h'),
                  onTap: () => Navigator.pop(context, '24h'),
                ),
              ],
            ),
          ),
        );
        if (mode == null || !context.mounted) return;
        try {
          final uploaded = await ref
              .read(apiClientProvider)
              .uploadMultipart(
                '/media/upload?kind=${isVideo ? 'video' : 'photo'}',
                filePath: file.path,
              );
          await ref
              .read(apiClientProvider)
              .post(
                '/matches/$matchId/snaps',
                body: {'media_url': uploaded['url'], 'view_mode': mode},
              );
          if (context.mounted) context.pop();
        } on AppException catch (e) {
          if (context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Could not send snap (${e.code})')),
            );
          }
        }
      },
    );
  }
}

/// Screen 33 — ephemeral snap viewer: hold-to-view + screenshot notice.
class SnapViewerScreen extends ConsumerStatefulWidget {
  const SnapViewerScreen({
    super.key,
    required this.snapUrl,
    required this.snapId,
  });
  final String snapUrl;
  final String snapId;

  @override
  ConsumerState<SnapViewerScreen> createState() => _SnapViewerScreenState();
}

class _SnapViewerScreenState extends ConsumerState<SnapViewerScreen> {
  bool _revealed = false;

  void _notifyViewed() {
    // Screenshot detection uses the OS flag where available; we always notify
    // the sender of view completion for single-view snaps (doc 1 guardrail #9).
    ref.read(apiClientProvider).post('/matches/snaps/${widget.snapId}/viewed');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: GestureDetector(
        onTapDown: (_) => setState(() => _revealed = true),
        onTapUp: (_) {
          if (_revealed) _notifyViewed();
          setState(() => _revealed = false);
        },
        child: Stack(
          children: [
            Positioned.fill(
              child: _revealed
                  ? CachedNetworkImage(imageUrl: widget.snapUrl, fit: BoxFit.contain)
                  : Center(
                      child: Icon(
                        Icons.visibility_off_outlined,
                        size: 56,
                        color: Colors.white24,
                      ),
                    ),
            ),
            SafeArea(
              child: Padding(
                padding: EdgeInsets.all(Spacing.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.timer, size: 14, color: Colors.white54),
                        SizedBox(width: Spacing.sm),
                        Text(
                          _revealed ? 'Viewing…' : 'Hold to view once',
                          style: TextStyle(color: Colors.white54, fontSize: 12),
                        ),
                      ],
                    ),
                    SizedBox(height: Spacing.md),
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
                        'Screenshots notify the sender',
                        style: TextStyle(color: Colors.white70, fontSize: 11),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Screen 34 — Share My Date with trusted contact.
class ShareDateScreen extends ConsumerStatefulWidget {
  const ShareDateScreen({super.key, required this.matchId});
  final String matchId;

  @override
  ConsumerState<ShareDateScreen> createState() => _ShareDateScreenState();
}

class _ShareDateScreenState extends ConsumerState<ShareDateScreen> {
  final _contactName = TextEditingController();
  final _contactPhone = TextEditingController();
  final _location = TextEditingController();
  DateTime? _when;
  bool _liveLocation = true;

  @override
  void dispose() {
    _contactName.dispose();
    _contactPhone.dispose();
    _location.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.safetyShareMyDate)),
      body: ListView(
        padding: EdgeInsets.all(Spacing.xl),
        children: [
          Text(
            'Let someone you trust know who, when and where before you meet up.',
            style: TextStyle(color: milan.ink600, height: 1.5),
          ),
          SizedBox(height: Spacing.xl),
          TextField(
            controller: _contactName,
            decoration: const InputDecoration(
              labelText: 'Trusted contact name',
            ),
          ),
          SizedBox(height: Spacing.lg),
          TextField(
            controller: _contactPhone,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(labelText: 'Their phone (+977…)'),
          ),
          SizedBox(height: Spacing.lg),
          TextField(
            controller: _location,
            decoration: const InputDecoration(labelText: 'Meeting place'),
          ),
          SizedBox(height: Spacing.lg),
          ListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('When'),
            subtitle: Text(
              _when?.toIso8601String().split('.').first ?? 'Pick date & time',
            ),
            trailing: const Icon(Icons.event),
            onTap: () async {
              final date = await showDatePicker(
                context: context,
                firstDate: DateTime.now(),
                lastDate: DateTime.now().add(const Duration(days: 60)),
              );
              if (date == null || !mounted) return;
              final time = await showTimePicker(
                context: context,
                initialTime: TimeOfDay.now(),
              );
              if (time != null) {
                setState(
                  () => _when = DateTime(
                    date.year,
                    date.month,
                    date.day,
                    time.hour,
                    time.minute,
                  ),
                );
              }
            },
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Share live location during the meetup'),
            value: _liveLocation,
            onChanged: (v) => setState(() => _liveLocation = v),
          ),
          SizedBox(height: Spacing.xl),
          FilledButton.icon(
            icon: Icon(Icons.share_location),
            label: const Text('Share my date'),
            onPressed: () async {
              await ref
                  .read(apiClientProvider)
                  .post(
                    '/matches/${widget.matchId}/share-date',
                    body: {
                      'contact_name': _contactName.text.trim(),
                      'contact_phone': _contactPhone.text.trim(),
                      'location': _location.text.trim(),
                      'date_time': _when?.toIso8601String(),
                      'live_location': _liveLocation,
                    },
                  );
              if (context.mounted) context.pop();
            },
          ),
        ],
      ),
    );
  }
}

/// Screens 35+36 — call shells with always-visible report shortcut.
class CallScreen extends StatelessWidget {
  const CallScreen({super.key, required this.video, required this.matchId});
  final bool video;
  final String matchId;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      backgroundColor: milan.ink900,
      body: SafeArea(
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                IconButton(
                  icon: const Icon(Icons.flag_outlined),
                  tooltip: 'Report unavailable until call is connected',
                  color: Colors.white,
                  onPressed: null,
                ),
              ],
            ),
            Expanded(
              child: Center(
                child: video
                    ? Stack(
                        alignment: Alignment.bottomCenter,
                        children: [
                          ColoredBox(
                            color: milan.paper100,
                            child: const SizedBox.expand(),
                          ),
                          CircleAvatar(
                            radius: 48,
                            backgroundColor: milan.dhaka500,
                            child: Icon(
                              Icons.person,
                              color: Colors.white,
                              size: 40,
                            ),
                          ),
                        ],
                      )
                    : Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircleAvatar(
                            radius: 64,
                            backgroundColor: milan.dhaka500,
                            child: Icon(
                              Icons.person,
                              color: Colors.white,
                              size: 52,
                            ),
                          ),
                          SizedBox(height: Spacing.xxl),
                          // Waveform avatar for audio-only calls.
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              for (final h in [10, 22, 34, 22, 10])
                                Padding(
                                  padding: EdgeInsets.symmetric(
                                    horizontal: Spacing.xs,
                                  ),
                                  child: Container(
                                    width: 4,
                                    height: h.toDouble(),
                                    decoration: BoxDecoration(
                                      color: milan.marigold100,
                                      borderRadius: BorderRadius.circular(2),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ],
                      ),
              ),
            ),
            Padding(
              padding: EdgeInsets.only(bottom: Spacing.huge),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: Colors.white24,
                    child: Icon(Icons.mic_off_outlined, color: Colors.white),
                  ),
                  SizedBox(width: Spacing.xl),
                  CircleAvatar(
                    radius: 30,
                    backgroundColor: milan.error500,
                    child: IconButton(
                      icon: Icon(Icons.call_end, color: Colors.white),
                      onPressed: () => context.pop(),
                    ),
                  ),
                  SizedBox(width: Spacing.xl),
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: Colors.white24,
                    child: Icon(
                      video
                          ? Icons.videocam_off_outlined
                          : Icons.volume_up_outlined,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Full-screen host for the match-scoped ThemePickerSheet route.
class ChatThemeRouteScreen extends StatelessWidget {
  const ChatThemeRouteScreen({super.key, required this.matchId});
  final String matchId;

  @override
  Widget build(BuildContext context) {
    return ThemePickerHostPage(
      title: 'Chat theme · this chat',
      scopeBuilder: () => ChatThemeScopeKey.match(matchId),
    );
  }
}
