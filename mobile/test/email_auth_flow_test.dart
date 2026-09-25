import 'dart:convert';
import 'dart:typed_data';
import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:milan/core/network/api_client.dart';
import 'package:milan/core/storage/secure_storage.dart';
import 'package:milan/features/auth/application/auth_provider.dart';

/// Records requests and returns canned JSON responses keyed by path suffix.
class _CannedAdapter implements HttpClientAdapter {
  final Map<String, Map<String, dynamic>> responses;
  final List<({String path, Map<String, dynamic> body})> posts = [];

  _CannedAdapter(this.responses);

  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? stream, Future<void>? cancelFuture) async {
    final path = options.uri.path;
    final method = options.method.toUpperCase();
    Map<String, dynamic>? body;
    if (method == 'POST' || method == 'PUT') {
      // options.data is already JSON-encoded string by the transformer.
      body = options.data is String
          ? Map<String, dynamic>.from(jsonDecode(options.data as String))
          : Map<String, dynamic>.from(options.data as Map);
      posts.add((path: path, body: body ?? {}));
    }
    for (final suffix in responses.keys) {
      if (path.endsWith(suffix)) {
        return ResponseBody.fromString(
          jsonEncode(responses[suffix]),
          200,
          headers: {Headers.contentTypeHeader: ['application/json']},
        );
      }
    }
    return ResponseBody.fromString(jsonEncode({'error': 'not_found', 'message': 'no canned response'}), 404,
        headers: {Headers.contentTypeHeader: ['application/json']});
  }

  @override
  void close({bool force = false}) {}
}

class _FakeStorage extends SecureStorage {
  String? access;
  String? refresh;
  String? storedUserId;

  @override
  Future<void> saveTokens({required String access, required String refresh}) async {
    this.access = access;
    this.refresh = refresh;
  }

  @override
  Future<void> saveUserId(String id) async {
    storedUserId = id;
  }

  @override
  Future<void> clearTokens() async {
    access = null;
    refresh = null;
    storedUserId = null;
  }

  @override
  Future<String?> get accessToken async => access;

  @override
  Future<String?> get refreshToken async => refresh;

  @override
  Future<String?> get userId async => storedUserId;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('AppException.displayMessage prefers the backend-controlled message', () {
    final backendError = AppException('invalid_or_expired_otp',
        message: 'That code is invalid or has expired. Request a new one and try again.');
    expect(backendError.displayMessage, contains('expired'));

    final noMessage = AppException('account_suspended');
    expect(noMessage.displayMessage, 'Account suspended.');
  });

  test('verifyOtp sends the email-based payload and stores the session', () async {
    final storage = _FakeStorage();
    final adapter = _CannedAdapter({
      '/auth/otp/verify': {
        'access_token': 'access-xyz',
        'refresh_token': 'refresh-xyz',
        'user': {
          'id': 'u-1',
          'email': 'aasha@example.com',
          'phone': null,
          'auth_provider': 'email',
          'is_verified': false,
          'has_profile': false,
        },
      },
      '/profile/me': {'updated': true},
    });

    final container = ProviderContainer(overrides: [
      secureStorageProvider.overrideWithValue(storage),
    ]);
    addTearDown(container.dispose);

    final api = container.read(apiClientProvider);
    api.testAdapter = adapter;

    final session = await container.read(authProvider.notifier).verifyOtp(
          email: 'aasha@example.com',
          code: '654321',
          dateOfBirth: '1998-04-12',
        );

    final verify = adapter.posts.firstWhere((p) => p.path.endsWith('/auth/otp/verify'));
    expect(verify.body['email'], 'aasha@example.com');
    expect(verify.body.containsKey('phone'), isFalse);
    expect(verify.body['code'], '654321');
    expect(verify.body['date_of_birth'], '1998-04-12');

    // Profile creation happens later in onboarding (has_profile=false here);
    // verifyOtp only stores the session.
    expect(storage.access, 'access-xyz');
    expect(storage.storedUserId, 'u-1');
    expect(session.userId, 'u-1');
    expect(session.hasProfile, isFalse);
  });

  test('requestOtp rethrows backend errors with the controlled message', () async {
    final storage = _FakeStorage();
    final container = ProviderContainer(overrides: [
      secureStorageProvider.overrideWithValue(storage),
    ]);
    addTearDown(container.dispose);

    final api = container.read(apiClientProvider);
    api.testAdapter = _ErrorAdapter();

    await expectLater(
      container.read(authProvider.notifier).requestOtp(email: 'bad-email'),
      throwsA(isA<AppException>().having((e) => e.displayMessage, 'message',
          contains("doesn't look right"))),
    );
  });
}

class _ErrorAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(RequestOptions options, Stream<Uint8List>? stream, Future<void>? cancelFuture) async {
    return ResponseBody.fromString(
      jsonEncode({
        'error': 'invalid_email',
        'message': "That email address doesn't look right. Check it and try again.",
      }),
      422,
      headers: {Headers.contentTypeHeader: ['application/json']},
    );
  }

  @override
  void close({bool force = false}) {}
}
