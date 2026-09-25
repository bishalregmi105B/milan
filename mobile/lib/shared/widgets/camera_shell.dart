import 'dart:async';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../../app/theme/color_tokens.dart';
import '../../app/theme/spacing_tokens.dart';

/// Doc 2 §2.6 — shared camera UI used by profile video intro, story snaps,
/// chat snaps, reels and liveness capture: filter carousel, hold-to-record
/// video, tap-to-photo.
class CameraShell extends StatefulWidget {
  const CameraShell({
    super.key,
    this.onCaptured,
    this.filters = const ['None', 'Dashain', 'Tihar', 'Holi'],
    this.hint,
    this.countdownSeconds = 0,
    this.maxVideoSeconds = 0,
    this.onFilterChanged,
  });

  final void Function(XFile file, {required bool isVideo})? onCaptured;
  final List<String> filters;
  final String? hint;
  final int countdownSeconds;
  /// Jhalak product rule: clips are 15 seconds max — auto-stop with a live
  /// countdown instead of letting a 90s raw recording blow the upload limit.
  final int maxVideoSeconds;
  /// Selected festival filter, for hosts that store it with the post.
  final ValueChanged<String>? onFilterChanged;

  @override
  State<CameraShell> createState() => _CameraShellState();
}

class _CameraShellState extends State<CameraShell> {
  CameraController? _controller;
  int _filterIndex = 0;
  bool _recording = false;
  int _elapsed = 0;
  bool _front = true;
  bool _flash = false;
  Timer? _tick;
  Timer? _maxStop;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async => _openCamera(_front);

  Future<void> _openCamera(bool front) async {
    final cameras = await availableCameras();
    if (cameras.isEmpty || !mounted) return;
    final camera = front
        ? cameras.firstWhere(
            (c) => c.lensDirection == CameraLensDirection.front,
            orElse: () => cameras.first)
        : cameras.firstWhere(
            (c) => c.lensDirection == CameraLensDirection.back,
            orElse: () => cameras.first);
    await _controller?.dispose();
    final controller = CameraController(
        camera, ResolutionPreset.high,
        enableAudio: true, imageFormatGroup: ImageFormatGroup.jpeg);
    await controller.initialize();
    if (!mounted) return;
    setState(() => _controller = controller);
  }

  Future<void> _flip() async {
    if (_recording) return;
    setState(() {
      _front = !_front;
      _controller = null;
    });
    await _openCamera(_front);
  }

  Future<void> _snap() async {
    if (_controller == null || _recording) return;
    try {
      await _controller!.setFlashMode(_flash ? FlashMode.torch : FlashMode.off);
      final file = await _controller!.takePicture();
      widget.onCaptured?.call(file, isVideo: false);
    } on CameraException {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Camera error — try again.')));
    }
  }

  @override
  void dispose() {
    _recording = false;
    _tick?.cancel();
    _maxStop?.cancel();
    _controller?.dispose();
    super.dispose();
  }



  Future<void> _toggleRecord() async {
    if (_controller == null) return;
    if (_recording) {
      await _stopRecording();
    } else {
      await _controller!.startVideoRecording();
      setState(() {
        _recording = true;
        _elapsed = 0;
      });
      _tick = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) setState(() => _elapsed++);
      });
      if (widget.maxVideoSeconds > 0) {
        _maxStop = Timer(Duration(seconds: widget.maxVideoSeconds), _stopRecording);
      }
    }
  }

  Future<void> _stopRecording() async {
    if (!_recording) return;
    _tick?.cancel();
    _maxStop?.cancel();
    try {
      final file = await _controller!.stopVideoRecording();
      if (mounted) setState(() => _recording = false);
      widget.onCaptured?.call(file, isVideo: true);
    } on CameraException {
      if (mounted) setState(() => _recording = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(children: [
        Positioned.fill(
          child: _controller?.value.isInitialized ?? false
              ? ColorFiltered(
                  colorFilter: _activeFilter(),
                  child: CameraPreview(_controller!),
                )
              : const Center(child: CircularProgressIndicator(color: Colors.white)),
        ),
        SafeArea(
          child: Column(children: [
            Padding(
              padding: EdgeInsets.all(Spacing.lg),
              child: Row(
                children: [
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.white),
                    onPressed: () => Navigator.of(context).maybePop(),
                  ),
                  Spacer(),
                  if (widget.hint != null)
                    Flexible(
                      child: Container(
                        padding: EdgeInsets.symmetric(horizontal: Spacing.md, vertical: Spacing.sm),
                        decoration: BoxDecoration(
                          color: Colors.black45,
                          borderRadius: BorderRadius.circular(Spacing.pill),
                        ),
                        child: Text(widget.hint!,
                            style: const TextStyle(color: Colors.white, fontSize: 12)),
                      ),
                    ),
                ],
              ),
            ),
          ]),
        ),
        // Festival filter carousel — same art direction as theme packs (doc 2 §2.5).
        Positioned(
          bottom: 120, left: 0, right: 0,
          child: SizedBox(
            height: 40,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: EdgeInsets.symmetric(horizontal: Spacing.xl),
              itemCount: widget.filters.length,
              separatorBuilder: (_, __) => SizedBox(width: Spacing.md),
              itemBuilder: (context, i) => ChoiceChip(
                label: Text(widget.filters[i], style: TextStyle(fontSize: 12)),
                selected: _filterIndex == i,
                onSelected: (_) {
                  setState(() => _filterIndex = i);
                  widget.onFilterChanged?.call(widget.filters[i]);
                },
                labelStyle: TextStyle(color: _filterIndex == i ? milan.ink900 : Colors.white),
                selectedColor: milan.marigold500,
                backgroundColor: Colors.black45,
              ),
            ),
          ),
        ),
        Positioned(
          bottom: 32, left: 0, right: 0,
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            // flash toggle
            GestureDetector(
              onTap: () => setState(() => _flash = !_flash),
              child: CircleAvatar(
                radius: 24,
                backgroundColor: _flash ? milan.marigold500 : Colors.white24,
                child: Icon(_flash ? Icons.flash_on : Icons.flash_off,
                    color: Colors.white, size: 20),
              ),
            ),
            const Spacer(),
            GestureDetector(
              onTap: _recording ? _stopRecording : _snap,
              onLongPressStart: (_) {
                if (!_recording) _toggleRecord();
              },
              onLongPressEnd: (_) {
                if (_recording) _stopRecording();
              },
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                if (_recording && widget.maxVideoSeconds > 0)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Text(
                      '${widget.maxVideoSeconds - _elapsed}s',
                      style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w800),
                    ),
                  ),
                Container(
                  width: 78, height: 78,
                  decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                          color: _recording ? milan.error500 : Colors.white,
                          width: 4)),
                  child: Padding(
                    padding: const EdgeInsets.all(4),
                    child: CircleAvatar(
                      backgroundColor:
                          _recording ? milan.error500 : Colors.white,
                      child: Icon(
                        _recording ? Icons.stop : Icons.camera_alt,
                        color: _recording ? Colors.white : milan.ink900,
                      ),
                    ),
                  ),
                ),
              ]),
            ),
            const Spacer(),
            // flip camera
            GestureDetector(
              onTap: _flip,
              child: const CircleAvatar(
                radius: 24,
                backgroundColor: Colors.white24,
                child: Icon(Icons.cameraswitch, color: Colors.white, size: 20),
              ),
            ),
          ]),
        ),
      ]),
    );
  }

  ColorFilter _activeFilter() {
    switch (widget.filters[_filterIndex]) {
      case 'Dashain':
        return const ColorFilter.mode(Color(0x33B8791A), BlendMode.srcATop);
      case 'Tihar':
        return const ColorFilter.mode(Color(0x33C97D0C), BlendMode.overlay);
      case 'Holi':
        return const ColorFilter.matrix(<double>[
          1.1, 0, 0, 0, 0,
          0, 0.95, 0, 0, 0,
          0, 0, 1.15, 0, 0,
          0, 0, 0, 1, 0,
        ]);
      default:
        return const ColorFilter.mode(Colors.transparent, BlendMode.dst);
    }
  }
}
