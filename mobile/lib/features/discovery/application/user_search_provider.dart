import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/network/api_client.dart';

/// One row of `GET /discovery/search` — backend ranking v2 orders results,
/// so the list arrives relevance-sorted (doc 8 §C8).
class UserSearchHit {
  const UserSearchHit({
    required this.id,
    required this.name,
    this.photoUrl,
    this.isVerified = false,
    this.trustScore,
    this.city,
    this.age,
    this.distanceKm,
    this.compatibilityScore,
    this.isBoosted = false,
  });

  final String id;
  final String name;
  final String? photoUrl;
  final bool isVerified;
  final int? trustScore;
  final String? city;
  final int? age;
  final double? distanceKm;
  final double? compatibilityScore;
  final bool isBoosted;

  factory UserSearchHit.fromJson(Map<String, dynamic> json) => UserSearchHit(
        id: json['id'] as String,
        name: (json['display_name'] as String?) ?? 'Milan user',
        photoUrl: json['photo_url'] as String?,
        isVerified: json['is_verified'] as bool? ?? false,
        trustScore: (json['trust_score'] as num?)?.toInt(),
        city: json['city'] as String?,
        age: (json['age'] as num?)?.toInt(),
        distanceKm: (json['distance_km'] as num?)?.toDouble(),
        compatibilityScore: (json['compatibility_score'] as num?)?.toDouble(),
        isBoosted: json['is_boosted'] as bool? ?? false,
      );
}

class UserSearchState {
  const UserSearchState({
    this.query = '',
    this.results = const [],
    this.loading = false,
    this.error,
    this.recent = const [],
  });
  final String query;
  final List<UserSearchHit> results;
  final bool loading;
  final String? error;
  final List<String> recent;

  UserSearchState copyWith({
    String? query,
    List<UserSearchHit>? results,
    bool? loading,
    String? error,
    List<String>? recent,
    bool clearError = false,
  }) =>
      UserSearchState(
        query: query ?? this.query,
        results: results ?? this.results,
        loading: loading ?? this.loading,
        error: clearError ? null : (error ?? this.error),
        recent: recent ?? this.recent,
      );
}

/// Instagram-style dedicated people search (doc 8 §A4.9): debounced live
/// queries, recents persisted locally, ranking done server-side.
class UserSearchController extends StateNotifier<UserSearchState> {
  UserSearchController(this._ref) : super(const UserSearchState()) {
    _loadRecent();
  }

  final Ref _ref;

  static const _recentKey = 'discovery.recentSearches';
  static const _maxRecent = 8;

  Future<void> _loadRecent() async {
    final prefs = await SharedPreferences.getInstance();
    state = state.copyWith(recent: prefs.getStringList(_recentKey) ?? const []);
  }

  Future<void> _rememberRecent(String q) async {
    final next = [q, ...state.recent.where((r) => r != q)].take(_maxRecent).toList();
    state = state.copyWith(recent: next);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_recentKey, next);
  }

  Future<void> removeRecent(String q) async {
    final next = state.recent.where((r) => r != q).toList();
    state = state.copyWith(recent: next);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_recentKey, next);
  }

  Future<void> clearRecent() async {
    state = state.copyWith(recent: const []);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList(_recentKey, const []);
  }

  void updateQuery(String q) {
    state = state.copyWith(query: q, clearError: true);
  }

  /// Live search — caller debounces; safe to cancel by checking `query`.
  Future<void> search() async {
    final q = state.query.trim();
    if (q.isEmpty) {
      state = state.copyWith(results: const [], loading: false, clearError: true);
      return;
    }
    state = state.copyWith(loading: true, clearError: true);
    try {
      final res = await _ref
          .read(apiClientProvider)
          .get<Map<String, dynamic>>('/discovery/search', query: {'q': q});
      // A newer keystroke may have replaced this query while in flight.
      if (state.query.trim() != q) return;
      final hits = (res['results'] as List? ?? const [])
          .map((e) => UserSearchHit.fromJson(e as Map<String, dynamic>))
          .toList();
      state = state.copyWith(results: hits, loading: false);
      await _rememberRecent(q);
    } on AppException catch (e) {
      if (state.query.trim() != q) return;
      state = state.copyWith(loading: false, error: e.displayMessage);
    }
  }
}

final userSearchProvider =
    StateNotifierProvider<UserSearchController, UserSearchState>(
        (ref) => UserSearchController(ref));
