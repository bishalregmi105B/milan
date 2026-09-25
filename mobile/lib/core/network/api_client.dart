import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/secure_storage.dart';

class AppException implements Exception {
  AppException(this.code, {this.message, this.statusCode});
  final String code;
  final String? message;
  final int? statusCode;

  /// Best user-facing text: backend-provided message, or a readable fallback
  /// derived from the code ('invalid_or_expired_otp' -> 'Invalid or expired otp').
  String get displayMessage {
    final m = message;
    if (m != null && m.isNotEmpty) return m;
    final text = code.replaceAll('_', ' ').replaceAll('-', ' ').trim();
    if (text.isEmpty) return 'Something went wrong. Please try again.';
    return text[0].toUpperCase() + text.substring(1) + '.';
  }

  @override
  String toString() =>
      'AppException($code${message == null ? '' : ': $message'})';
}

class ApiClient {
  ApiClient({required SecureStorage storage}) : _storage = storage {
    _dio = Dio(
      BaseOptions(
        baseUrl: const String.fromEnvironment(
          'MILAN_API_BASE_URL',
          // Production API by default; override for local dev with:
          //   --dart-define=MILAN_API_BASE_URL=http://<host>:<port>/api/v1
          defaultValue: 'https://milanapi.pukarphulara.com.np/api/v1',
        ),
        connectTimeout: const Duration(seconds: 12),
        receiveTimeout: const Duration(seconds: 20),
      ),
    );
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          if (error.response?.statusCode == 401) {
            // Never refresh-loop on an already-retried request.
            final alreadyRetried =
                error.requestOptions.extra['milan_retried'] == true;
            if (!alreadyRetried) {
              final refreshed = await _tryRefresh();
              if (refreshed) {
                final retry = await _retry(error.requestOptions);
                return handler.resolve(retry);
              }
              // Refresh failed: drop the dead tokens and notify listeners so
              // the app stops retrying forever (P0-1).
              await _expireSession();
            }
          }
          handler.next(error);
        },
      ),
    );
  }

  final SecureStorage _storage;
  late final Dio _dio;
  Future<void>? _refreshing;

  /// Session lifecycle hooks (P0-1): wired by authProvider (signed-out state)
  /// and websocketClientProvider (socket token sync) without circular deps.
  final List<void Function(String)> _tokenRefreshedListeners = [];
  final List<void Function()> _sessionExpiredListeners = [];

  void onTokenRefreshed(void Function(String accessToken) listener) =>
      _tokenRefreshedListeners.add(listener);

  void onSessionExpired(void Function() listener) =>
      _sessionExpiredListeners.add(listener);

  Dio get dio => _dio;

  /// Single-flight refresh (P0-1): concurrent 401s share one request instead
  /// of racing (the old `_refreshing` bool made parallel callers return false
  /// and lose the retry).
  Future<bool> _tryRefresh() async {
    final inFlight = _refreshing;
    if (inFlight != null) {
      try {
        await inFlight;
        return true;
      } catch (_) {
        return false;
      }
    }
    final op = _doRefresh();
    _refreshing = op;
    try {
      await op;
      return true;
    } catch (_) {
      return false;
    } finally {
      _refreshing = null;
    }
  }

  Future<void> _doRefresh() async {
    final refresh = await _storage.refreshToken;
    if (refresh == null || refresh.isEmpty) {
      throw AppException('signed_out', statusCode: 401);
    }
    // Backend contract (auth_bp POST /refresh, @jwt_required(refresh=True)):
    // the refresh token travels as `Authorization: Bearer <refresh>`; the
    // body form 401s. Response only carries {"access_token": "..."}.
    final response = await Dio(BaseOptions(baseUrl: _dio.options.baseUrl)).post(
      '/auth/refresh',
      options: Options(headers: {'Authorization': 'Bearer $refresh'}),
    );
    final access = response.data['access_token'] as String;
    await _storage.saveTokens(access: access, refresh: refresh);
    for (final listener in _tokenRefreshedListeners) {
      listener(access);
    }
  }

  /// Clears the dead session so callers stop retrying forever (P0-1).
  Future<void> _expireSession() async {
    await _storage.clearTokens();
    for (final listener in _sessionExpiredListeners) {
      listener();
    }
  }

  Future<Response<dynamic>> _retry(RequestOptions requestOptions) async {
    final token = await _storage.accessToken;
    requestOptions.extra['milan_retried'] = true;
    requestOptions.headers['Authorization'] = 'Bearer $token';
    return _dio.fetch(requestOptions);
  }

  AppException mapError(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      String code = 'network_error';
      String? message;
      if (data is Map) {
        if (data['error'] is String) code = data['error'] as String;
        // Backend sends a controlled, human-readable message alongside the code.
        if (data['message'] is String &&
            (data['message'] as String).isNotEmpty) {
          message = data['message'] as String;
        }
      }
      return AppException(
        code,
        statusCode: error.response?.statusCode,
        message: message ?? error.message,
      );
    }
    return AppException('unknown_error', message: error.toString());
  }

  Future<T> get<T>(String path, {Map<String, dynamic>? query}) async {
    try {
      final res = await _dio.get<T>(path, queryParameters: query);
      return res.data as T;
    } catch (e) {
      throw mapError(e);
    }
  }

  Future<T> post<T>(String path, {Object? body}) async {
    try {
      final res = await _dio.post<T>(path, data: body);
      return res.data as T;
    } catch (e) {
      throw mapError(e);
    }
  }

  Future<T> put<T>(String path, {Object? body}) async {
    try {
      final res = await _dio.put<T>(path, data: body);
      return res.data as T;
    } catch (e) {
      throw mapError(e);
    }
  }

  Future<T> delete<T>(String path) async {
    try {
      final res = await _dio.delete<T>(path);
      return res.data as T;
    } catch (e) {
      throw mapError(e);
    }
  }

  /// Multipart upload (photos, video intros, liveness selfies, wallpapers).
  Future<Map<String, dynamic>> uploadMultipart(
    String path, {
    required String filePath,
    String field = 'file',
    Map<String, dynamic>? data,
  }) async {
    try {
      final form = FormData.fromMap({
        field: await MultipartFile.fromFile(filePath),
        ...?data,
      });
      final res = await _dio.post<Map<String, dynamic>>(path, data: form);
      return res.data ?? <String, dynamic>{};
    } catch (e) {
      throw mapError(e);
    }
  }

  /// Resolve relative media paths returned by the API before handing them to
  /// platform media players. Absolute URLs are preserved.
  String resolveMediaUrl(String value) {
    final parsed = Uri.tryParse(value);
    if (parsed != null && parsed.hasScheme) return value;
    return Uri.parse(_dio.options.baseUrl).resolve(value).toString();
  }

  /// Swap the transport for tests (canned-response adapter).
  @visibleForTesting
  set testAdapter(HttpClientAdapter adapter) =>
      _dio.httpClientAdapter = adapter;
}

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(storage: ref.watch(secureStorageProvider));
});
