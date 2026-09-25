import 'dart:io';

import 'package:flutter_image_compress/flutter_image_compress.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_compress/video_compress.dart';

/// Client-side compression for low-bandwidth uploads (doc 3 §8).
/// More aggressive on data-saver; also used for custom chat-wallpaper
/// uploads before preview and send.
class CompressionService {
  Future<File> compressImage(String path, {bool dataSaver = false}) async {
    final source = File(path);
    if (!source.existsSync()) return source;
    if (source.lengthSync() < 200 * 1024 && !dataSaver) return source;

    final result = await FlutterImageCompress.compressWithFile(
      source.absolute.path,
      quality: dataSaver ? 40 : 72,
      minWidth: dataSaver ? 720 : 1280,
      format: CompressFormat.jpeg,
    );
    if (result == null) return source;

    final out = File('$path.milan.jpg');
    await out.writeAsBytes(result);
    return out;
  }

  Future<MediaInfo?> compressVideo(String path) {
    return VideoCompress.compressVideo(
      path,
      quality: VideoQuality.MediumQuality,
      deleteOrigin: false,
    );
  }
}

final compressionServiceProvider =
    Provider<CompressionService>((ref) => CompressionService());
