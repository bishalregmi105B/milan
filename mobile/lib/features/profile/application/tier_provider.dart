import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';

/// The signed-in user's pass tier, from /profile/me. Simple StateNotifier:
/// refreshed on demand (after payment approval, subscription changes) and
/// consumed by premium gates (multi-photo chat themes, companion limits...).
class TierState {
  const TierState({this.tier = 'free', this.loaded = false});
  final String tier;
  final bool loaded;

  bool get isPlusOrHigher => tier == 'plus' || tier == 'premium';
  bool get isPremium => tier == 'premium';
}

class TierController extends StateNotifier<TierState> {
  TierController(this._ref) : super(const TierState());
  final Ref _ref;

  Future<void> load() async {
    try {
      final res =
          await _ref.read(apiClientProvider).get<Map<String, dynamic>>('/profile/me');
      state = TierState(
        tier: (res['tier'] as String?) ?? 'free',
        loaded: true,
      );
    } on AppException {
      state = TierState(tier: state.tier, loaded: true);
    }
  }

  /// Re-check after a payment approval / subscription change.
  void refresh() => load();
}

final tierProvider = StateNotifierProvider<TierController, TierState>(
    (ref) => TierController(ref));
