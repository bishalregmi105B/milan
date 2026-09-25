import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

class CandidateProfile {
  const CandidateProfile({
    required this.id,
    required this.name,
    required this.photoUrl,
    required this.age,
    this.distanceKm,
    this.verified = false,
    this.promptOverlay,
    this.compatibilityScore,
  });

  final String id;
  final String name;
  final String? photoUrl;
  final int age;
  final double? distanceKm;
  final bool verified;
  final String? promptOverlay;
  final num? compatibilityScore;

  factory CandidateProfile.fromJson(Map<String, dynamic> json) {
    return CandidateProfile(
      id: json['id'] as String,
      name: (json['display_name'] as String?) ?? 'Someone',
      photoUrl: json['photo_url'] as String?,
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

  Future<List<CandidateProfile>> _load() async {
    final res = await ref.read(apiClientProvider).get<Map<String, dynamic>>(
      '/discovery/candidates',
      query: {'mode': currentMode, 'limit': _pageSize, ...filterQuery()},
    );
    final items = (res['candidates'] as List)
        .map((e) => CandidateProfile.fromJson(e as Map<String, dynamic>))
        .toList();
    return items;
  }

  String currentMode = 'serious';
  // Server-applied filters (Indian-app parity): persisted in-memory and sent
  // with every candidates fetch. The SERVER filters — the UI never fakes it.
  int ageMin = 21;
  int ageMax = 40;
  String? city;
  bool verifiedOnly = false;
  String? intent;

  Map<String, dynamic> filterQuery() => {
        'age_min': ageMin,
        'age_max': ageMax,
        if (city != null && city!.isNotEmpty) 'city': city,
        'verified_only': verifiedOnly ? 'true' : 'false',
        if (intent != null && intent!.isNotEmpty && intent != 'any') 'intent': intent,
      };

  void applyFilters({int? min, int? max, String? cityValue, bool? verified, String? intentValue}) {
    if (min != null) ageMin = min;
    if (max != null) ageMax = max;
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
      final res = await _api.post<Map<String, dynamic>>('/discovery/swipe',
          body: {'target_id': targetId, 'direction': direction});
      state = AsyncData(
          (state.valueOrNull ?? []).where((c) => c.id != targetId).toList());
      if ((state.valueOrNull ?? []).length <= 3) {
        // pre-fetch before the stack runs dry (doc 3 §4)
        ref.invalidateSelf();
      }
      return res;
    } on AppException {
      rethrow;
    }
  }

  void undo(CandidateProfile candidate) {
    state = AsyncData([candidate, ...(state.valueOrNull ?? [])]);
  }
}

final discoveryProvider = AsyncNotifierProvider<DiscoveryController,
    List<CandidateProfile>>(DiscoveryController.new);
