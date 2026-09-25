import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class CandidateProfile {
  const CandidateProfile({
    required this.id,
    required this.name,
    required this.photoUrl,
    required this.age,
    this.photos = const [],
    this.distanceKm,
    this.verified = false,
    this.promptOverlay,
    this.compatibilityScore,
  });

  final String id;
  final String name;
  final String? photoUrl;
  final List<String> photos;
  final int age;
  final double? distanceKm;
  final bool verified;
  final String? promptOverlay;
  final num? compatibilityScore;

  /// The gallery for the multi-photo swipe card — the `photos` array when the
  /// server sends one, otherwise the single `photo_url` so older payloads and
  /// blurred (preview-only) candidates still render a card.
  List<String> get gallery =>
      photos.isNotEmpty ? photos : [if (photoUrl != null) photoUrl!];

  factory CandidateProfile.fromJson(Map<String, dynamic> json) {
    return CandidateProfile(
      id: json['id'] as String,
      name: (json['display_name'] as String?) ?? 'Someone',
      photoUrl: json['photo_url'] as String?,
      photos: ((json['photos'] as List?) ?? const [])
          .whereType<String>()
          .toList(),
      age: (json['age'] as num?)?.toInt() ?? 0,
      distanceKm: (json['distance_km'] as num?)?.toDouble(),
      verified: json['is_verified'] as bool? ?? false,
      compatibilityScore: json['compatibility_score'] as num?,
    );
  }
}

/// Paginated candidate queue; pre-fetches next page when 3 cards remain
/// locally so swiping never blocks on network (doc 3 §4).
class DiscoveryController extends AsyncNotifier<List<CandidateProfile>> {
  static const _pageSize = 15;

  @override
  Future<List<CandidateProfile>> build() => _load();

  ApiClient get _api => ref.read(apiClientProvider);

  CandidateProfile? _lastSwiped;
  bool _appending = false;

  Future<List<CandidateProfile>> _load() async {
    final res = await ref.read(apiClientProvider).get<Map<String, dynamic>>(
      '/discovery/candidates',
      query: {'mode': currentMode, 'limit': _pageSize, ...filterQuery()},
    );
    final items = (res['candidates'] as List? ?? const [])
        .map((e) => CandidateProfile.fromJson(e as Map<String, dynamic>))
        .toList();
    return items;
  }

  String currentMode = 'serious';
  // Server-applied filters (Indian-app parity): persisted in-memory and sent
  // with every candidates fetch. The SERVER filters — the UI never fakes it.
  int ageMin = 21;
  int ageMax = 40;
  int? maxDistanceKm;
  String? city;
  bool verifiedOnly = false;
  String? intent;

  Map<String, dynamic> filterQuery() => {
        'age_min': ageMin,
        'age_max': ageMax,
        if (maxDistanceKm != null && maxDistanceKm! > 0)
          'max_distance_km': maxDistanceKm,
        if (city != null && city!.isNotEmpty) 'city': city,
        'verified_only': verifiedOnly ? 'true' : 'false',
        if (intent != null && intent!.isNotEmpty && intent != 'any') 'intent': intent,
      };

  void applyFilters(
      {int? min,
      int? max,
      int? distanceKm,
      String? cityValue,
      bool? verified,
      String? intentValue}) {
    if (min != null) ageMin = min;
    if (max != null) ageMax = max;
    if (distanceKm != null) maxDistanceKm = distanceKm;
    if (cityValue != null) city = cityValue;
    if (verified != null) verifiedOnly = verified;
    if (intentValue != null) intent = intentValue;
    ref.invalidateSelf();
  }

  Future<void> setMode(String mode) async {
    currentMode = mode;
    ref.invalidateSelf();
    await future;
  }

  Future<Map<String, dynamic>?> swipe(String targetId, String direction) async {
    try {
      final current = state.valueOrNull ?? [];
      CandidateProfile? swiped;
      for (final c in current) {
        if (c.id == targetId) {
          swiped = c;
          break;
        }
      }
      _lastSwiped = swiped;
      final res = await _api.post<Map<String, dynamic>>('/discovery/swipe',
          body: {'target_id': targetId, 'direction': direction});
      state = AsyncData(current.where((c) => c.id != targetId).toList());
      // Append the next page BEFORE the stack runs dry instead of replacing the
      // deck (which discarded the unseen cards, doc 8 §A4 / P2-1).
      if ((state.valueOrNull ?? []).length <= 3) {
        _appendMore();
      }
      return res;
    } on AppException {
      rethrow;
    }
  }

  /// Fetch the next page and MERGE it in, keeping the cards already on screen
  /// and dropping any duplicates the server re-returns.
  Future<void> _appendMore() async {
    if (_appending) return;
    _appending = true;
    try {
      final more = await _load();
      final current = state.valueOrNull ?? [];
      final seen = current.map((c) => c.id).toSet();
      final merged = [...current, ...more.where((c) => !seen.contains(c.id))];
      state = AsyncData(merged);
    } on AppException {
      // keep the current deck; the next swipe will retry the refill
    } finally {
      _appending = false;
    }
  }

  /// Server-backed rewind (tier-gated): un-records the last swipe so the
  /// candidate genuinely re-enters the deck, then puts it back on top locally.
  /// Returns the server result so the UI can surface a cap/upsell message.
  Future<Map<String, dynamic>> rewind() async {
    try {
      final res = await _api.post<Map<String, dynamic>>('/discovery/rewind');
      if (res['rewound'] == true && _lastSwiped != null) {
        final current = state.valueOrNull ?? [];
        if (!current.any((c) => c.id == _lastSwiped!.id)) {
          state = AsyncData([_lastSwiped!, ...current]);
        }
        _lastSwiped = null;
      }
      return res;
    } on AppException catch (e) {
      return {'rewound': false, 'reason': e.code};
    }
  }
}

final discoveryProvider = AsyncNotifierProvider<DiscoveryController,
    List<CandidateProfile>>(DiscoveryController.new);
