import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/notifications/push_service.dart';
import 'package:google_sign_in/google_sign_in.dart';

import '../../../core/network/api_client.dart';
import '../../../core/network/websocket_client.dart';
import '../../../core/storage/secure_storage.dart';

class Session {
  const Session({
    required this.userId,
    this.hasProfile = false,
    this.email,
    this.authProvider = 'phone',
  });
  final String userId;
  final bool hasProfile;
  final String? email;
  final String authProvider;
}

/// Synchronous holder for the signed-in user's id (mirrors secure storage,
/// which is written at OTP verify). Chat reads it to attribute message
/// senders without awaiting disk (P1-6).
final currentUserIdProvider = StateProvider<String?>((ref) => null);

class AuthController extends AsyncNotifier<Session?> {
  @override
  Future<Session?> build() async {
    // P0-1: when a token refresh fails for good, drop the session so the app
    // stops retrying forever (secure storage is already cleared by ApiClient).
    ref.read(apiClientProvider).onSessionExpired(() {
      state = const AsyncData(null);
    });
    // Session restore: returning users go straight to the app — signing up
    // twice with the same email must never be needed.
    final storage = ref.read(secureStorageProvider);
    final access = await storage.accessToken;
    if (access == null || access.isEmpty) return null;
    try {
      final me = await _api.get<Map<String, dynamic>>('/profile/me');
      final user = me['user'] as Map<String, dynamic>?;
      final userId = user?['id']?.toString() ?? await storage.userId ?? '';
      if (userId.isEmpty) return null;
      ref.read(currentUserIdProvider.notifier).state = userId;
      final ws = ref.read(websocketClientProvider);
      ws.authToken = access;
      ws.connect();
      unawaited(ref.read(pushServiceProvider).onSignedIn(userId));
      final profile = me['profile'] as Map<String, dynamic>?;
      final hasProfile = ((profile?['display_name'] ?? '') as String)
          .trim()
          .isNotEmpty;
      return Session(
        userId: userId,
        hasProfile: hasProfile,
        email: user?['email']?.toString(),
        authProvider: user?['auth_provider']?.toString() ?? 'phone',
      );
    } on AppException catch (e) {
      if (e.statusCode == 401) {
        await storage.clearTokens();
        return null;
      }
      // Offline / network error: a stored token + user id means the user is
      // still signed in — restore so they aren't forced through signup again.
      final savedId = await storage.userId;
      if (savedId != null && savedId.isNotEmpty) {
        final ws = ref.read(websocketClientProvider);
        ws.authToken = access;
        ws.connect();
        ref.read(currentUserIdProvider.notifier).state = savedId;
        unawaited(ref.read(pushServiceProvider).onSignedIn(savedId));
        return Session(userId: savedId, hasProfile: true);
      }
      return null;
    }
  }

  ApiClient get _api => ref.read(apiClientProvider);

  /// Request an OTP without revealing whether the identifier already belongs
  /// to an account. The post-verification response is the only place account
  /// state is exposed.
  /// Throws [AppException] with the backend's controlled message on failure.
  Future<void> requestOtp({String? phone, String? email}) async {
    state = const AsyncLoading();
    try {
      await _api.post<Map<String, dynamic>>(
        '/auth/otp/request',
        body: {
          if (phone != null) 'phone': phone,
          if (email != null) 'email': email,
        },
      );
      state = AsyncData(null);
    } on AppException catch (e) {
      state = AsyncError(e, StackTrace.current);
      rethrow;
    }
  }

  /// Throws [AppException] on failure so screens can show the real reason
  /// (expired code vs network failure vs age gate) instead of silently looping.
  Future<Session> verifyOtp({
    String? phone,
    String? email,
    required String code,
    String? dateOfBirth,
  }) async {
    final res = await _api.post<Map<String, dynamic>>(
      '/auth/otp/verify',
      body: {
        if (phone != null) 'phone': phone,
        if (email != null) 'email': email,
        'code': code,
        if (dateOfBirth != null) 'date_of_birth': dateOfBirth,
      },
    );
    final access = res['access_token'] as String?;
    final refresh = res['refresh_token'] as String?;
    final user = res['user'];
    if (access == null || refresh == null || user is! Map) {
      // Never hard-cast: a malformed backend payload must surface as a
      // controlled AppException, not crash the login flow.
      throw AppException(
        'malformed_auth_response',
        message: 'Login response was incomplete — please try again.',
      );
    }
    await ref
        .read(secureStorageProvider)
        .saveTokens(access: access, refresh: refresh);
    final userId = user['id']?.toString() ?? '';
    if (userId.isEmpty) {
      throw AppException(
        'malformed_auth_response',
        message: 'Login response was incomplete — please try again.',
      );
    }
    await ref.read(secureStorageProvider).saveUserId(userId);
    ref.read(currentUserIdProvider.notifier).state = userId;
    // P0-2: bring the realtime layer online with the fresh token.
    final ws = ref.read(websocketClientProvider);
    ws.authToken = access;
    ws.connect();
    final session = Session(
      userId: userId,
      hasProfile: user['has_profile'] as bool? ?? false,
      email: user['email']?.toString(),
      authProvider: user['auth_provider']?.toString() ?? 'phone',
    );
    state = AsyncData(session);
    // OneSignal: external-id login + subscription registration (§push v2).
    unawaited(ref.read(pushServiceProvider).onSignedIn(userId));
    return session;
  }

  /// Google Sign-In (§auth): one-tap, then the ID token is verified
  /// server-side — same JWT pair, same session flow as OTP.
  Future<Session> signInWithGoogle({String? dateOfBirth}) async {
    state = const AsyncLoading();
    try {
      final google = GoogleSignIn(scopes: ['email']);
      final account = await google.signIn();
      if (account == null) {
        state = AsyncData(null);
        throw AppException(
          'google_cancelled',
          message: 'Google sign-in cancelled.',
        );
      }
      final auth = await account.authentication;
      final idToken = auth.idToken;
      if (idToken == null) {
        throw AppException(
          'google_no_token',
          message: "Google didn't return a token — try again.",
        );
      }
      final res = await _api.post<Map<String, dynamic>>(
        '/auth/google',
        body: {
          'id_token': idToken,
          if (dateOfBirth != null) 'date_of_birth': dateOfBirth,
        },
      );
      final access = res['access_token'] as String?;
      final refresh = res['refresh_token'] as String?;
      final user = res['user'];
      if (access == null || refresh == null || user is! Map) {
        throw AppException(
          'malformed_auth_response',
          message: 'Login response was incomplete — please try again.',
        );
      }
      await ref
          .read(secureStorageProvider)
          .saveTokens(access: access, refresh: refresh);
      final userId = user['id']?.toString() ?? '';
      await ref.read(secureStorageProvider).saveUserId(userId);
      ref.read(currentUserIdProvider.notifier).state = userId;
      final ws = ref.read(websocketClientProvider);
      ws.authToken = access;
      ws.connect();
      final session = Session(
        userId: userId,
        hasProfile: user['has_profile'] as bool? ?? false,
        email: user['email']?.toString(),
        authProvider: 'google',
      );
      state = AsyncData(session);
      await ref.read(pushServiceProvider).onSignedIn(userId);
      return session;
    } on AppException catch (e) {
      state = AsyncError(e, StackTrace.current);
      rethrow;
    }
  }

  Future<void> signOut() async {
    final ws = ref.read(websocketClientProvider);
    ws.disconnect();
    ws.clearSession();
    ref.read(currentUserIdProvider.notifier).state = null;
    await ref.read(secureStorageProvider).clearTokens();
    state = const AsyncData(null);
  }
}

final authProvider = AsyncNotifierProvider<AuthController, Session?>(
  AuthController.new,
);
