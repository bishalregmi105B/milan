import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';

import '../../app/theme/color_tokens.dart';
import '../../app/theme/spacing_tokens.dart';
import '../../core/network/api_client.dart';
import 'chat_bubble.dart';

/// In-thread voice-note player (doc 8 §A2.9: recording existed, playback did
/// not). Streams over HTTP via just_audio; no local-file hop needed.
class VoiceNoteBubble extends ConsumerStatefulWidget {
  const VoiceNoteBubble({
    super.key,
    required this.url,
    required this.isSent,
    this.accent,
  });
  final String url;
  final bool isSent;
  final Color? accent;

  @override
  ConsumerState<VoiceNoteBubble> createState() => _VoiceNoteBubbleState();
}

class _VoiceNoteBubbleState extends ConsumerState<VoiceNoteBubble> {
  final AudioPlayer _player = AudioPlayer();
  bool _failed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final url = ref.read(apiClientProvider).resolveMediaUrl(widget.url);
      await _player.setUrl(url);
    } catch (_) {
      if (mounted) setState(() => _failed = true);
    }
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  String _fmt(Duration d) =>
      '${d.inMinutes.remainder(60).toString().padLeft(2, '0')}:${d.inSeconds.remainder(60).toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final milan = context.milan;
    final accent = widget.accent ?? ChatBubble.defaultAccent;
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 10),
      decoration: BoxDecoration(
        color: widget.isSent ? accent : ChatBubble.receivedFill,
        borderRadius: BorderRadius.circular(Spacing.radiusLg),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: _failed
                ? Icon(
                    Icons.error_outline,
                    color: widget.isSent ? Colors.white : milan.ink600,
                  )
                : StreamBuilder<PlayerState>(
                    stream: _player.playerStateStream,
                    builder: (context, snap) {
                      final playing = snap.data?.playing ?? false;
                      return Icon(
                        playing
                            ? Icons.pause_circle_filled
                            : Icons.play_circle_filled,
                        color: widget.isSent ? Colors.white : accent,
                        size: 28,
                      );
                    },
                  ),
            onPressed: _failed
                ? null
                : () {
                    final playing = _player.playing;
                    if (playing) {
                      _player.pause();
                    } else {
                      _player.play();
                    }
                  },
          ),
          StreamBuilder<Duration>(
            stream: _player.positionStream,
            builder: (context, snap) => Text(
              _fmt(snap.data ?? Duration.zero),
              style: TextStyle(
                fontSize: 12,
                color: widget.isSent ? Colors.white : milan.ink600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
