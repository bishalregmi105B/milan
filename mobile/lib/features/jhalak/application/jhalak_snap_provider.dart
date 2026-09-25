import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

/// One tile of the Jhalak grid (§Jhalak v2): who posted it, when, and
/// whether this viewer still has their one look. NO media URL until the
/// view is burned server-side — a tile can never leak the image.
class SnapTile {
  const SnapTile({
    required this.id,
    required this.authorId,
    required this.authorName,
    this.authorPhotoUrl,
    required this.mine,
    required this.viewed,
    this.caption,
    this.filterKey,
    this.postedAt,
    this.expiresAt,
    this.viewCount = 0,
  });

  final String id;
  final String authorId;
  final String authorName;
  final String? authorPhotoUrl;
  final bool mine;
  final bool viewed;
  final String? caption;
  final String? filterKey;
  final DateTime? postedAt;
  final DateTime? expiresAt;
  final int viewCount;

  factory SnapTile.fromJson(Map<String, dynamic> json) {
    final author = json['author'] as Map<String, dynamic>?;
    return SnapTile(
      id: json['id'] as String,
      authorId: author?['id'] as String? ?? '',
      authorName: (author?['display_name'] as String?) ?? 'Someone',
      authorPhotoUrl: author?['photo_url'] as String?,
      mine: json['mine'] as bool? ?? false,
      viewed: json['viewed'] as bool? ?? false,
      caption: json['caption'] as String?,
      filterKey: json['filter_key'] as String?,
      postedAt: json['posted_at'] == null
          ? null
          : DateTime.tryParse(json['posted_at'] as String),
      expiresAt: json['expires_at'] == null
          ? null
          : DateTime.tryParse(json['expires_at'] as String),
      viewCount: (json['view_count'] as num?)?.toInt() ?? 0,
    );
  }
}

/// The burned look: media revealed once, held only in memory.
class SnappedMedia {
  const SnappedMedia({required this.mediaUrl, this.caption, this.filterKey});
  final String mediaUrl;
  final String? caption;
  final String? filterKey;
}

class JhalakSnapController extends AsyncNotifier<List<SnapTile>> {
  @override
  Future<List<SnapTile>> build() async {
    // Propagate failures to AsyncError so the screen's error + Retry branch
    // runs instead of showing a fake "empty" state that can't recover.
    final res =
        await ref.read(apiClientProvider).get<Map<String, dynamic>>('/jhalak/snaps');
    return (res['snaps'] as List? ?? const [])
        .map((e) => SnapTile.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> refresh() async {
    ref.invalidateSelf();
    await future;
  }

  /// Post a snap from an uploaded image URL. Throws [AppException].
  Future<void> postSnap({required String imageUrl, String? caption, String? filterKey}) async {
    await ref.read(apiClientProvider).post('/jhalak/snaps', body: {
      'image_url': imageUrl,
      if (caption != null && caption.trim().isNotEmpty) 'caption': caption.trim(),
      if (filterKey != null && filterKey != 'None') 'filter_key': filterKey,
    });
    await refresh();
  }

  /// Burn the viewer's one look. The media URL comes back exactly once;
  /// a repeat call returns `already_viewed` with `mediaUrl == null`.
  Future<SnappedMedia> viewOnce(SnapTile tile) async {
    final res = await ref.read(apiClientProvider).post<Map<String, dynamic>>(
        '/jhalak/snaps/${tile.id}/view');
    await refresh();
    return SnappedMedia(
      mediaUrl: res['media_url'] as String? ?? '',
      caption: res['caption'] as String?,
      filterKey: res['filter_key'] as String?,
    );
  }

  /// Self-report a screenshot; the author gets a push.
  Future<void> reportScreenshot(String snapId) async {
    try {
      await ref.read(apiClientProvider).post('/jhalak/snaps/$snapId/screenshot');
    } on AppException {
      // best-effort
    }
  }

  Future<void> deleteMine(String snapId) async {
    await ref.read(apiClientProvider).delete('/jhalak/snaps/$snapId');
    await refresh();
  }
}

final jhalakSnapProvider =
    AsyncNotifierProvider<JhalakSnapController, List<SnapTile>>(
        JhalakSnapController.new);
