import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class SecureStorage {
  static const _access = 'milan.access_token';
  static const _refresh = 'milan.refresh_token';
  static const _userId = 'milan.user_id';
  static const _biometric = 'milan.biometric_opt_in';

  final FlutterSecureStorage _inner = const FlutterSecureStorage();

  Future<String?> get accessToken => _inner.read(key: _access);
  Future<String?> get refreshToken => _inner.read(key: _refresh);

  /// Own user id persisted alongside the tokens at OTP verify (P1-6) so chat
  /// bubbles can attribute senders without an extra request.
  Future<String?> get userId => _inner.read(key: _userId);

  Future<void> saveUserId(String id) => _inner.write(key: _userId, value: id);

  Future<void> saveTokens({required String access, required String refresh}) async {
    await _inner.write(key: _access, value: access);
    await _inner.write(key: _refresh, value: refresh);
  }

  Future<void> clearTokens() async {
    await _inner.delete(key: _access);
    await _inner.delete(key: _refresh);
    await _inner.delete(key: _userId);
  }

  Future<bool> get biometricOptIn async =>
      await _inner.read(key: _biometric) == 'true';

  Future<void> setBiometricOptIn(bool value) =>
      _inner.write(key: _biometric, value: value ? 'true' : 'false');
}

final secureStorageProvider =
    Provider<SecureStorage>((ref) => SecureStorage());
