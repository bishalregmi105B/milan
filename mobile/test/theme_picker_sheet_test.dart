import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:milan/app/theme/chat_theme_tokens.dart';
import 'package:milan/core/network/api_client.dart';
import 'package:milan/core/storage/local_db.dart';
import 'package:milan/core/storage/secure_storage.dart';
import 'package:milan/app/theme/color_tokens.dart';
import 'package:milan/shared/widgets/theme_picker_sheet.dart';

class _EmptyDb extends LocalDb {
  final Map<String, Map<String, dynamic>> store = {};
  @override
  Future<Map<String, dynamic>?> loadResolvedTheme(String scopeKey) async => null;
  @override
  Future<void> saveResolvedTheme(String scopeKey, Map<String, dynamic> json,
      {bool synced = false}) async {
    store[scopeKey] = json;
  }
  @override
  Future<void> markThemesSynced() async {}
}

class _OfflineClient extends ApiClient {
  _OfflineClient() : super(storage: SecureStorage());
  Never _fail() => throw AppException('network_error', statusCode: 503);
  @override
  Future<T> get<T>(String path, {Map<String, dynamic>? query}) async => _fail();
  @override
  Future<T> post<T>(String path, {Object? body}) async => _fail();
  @override
  Future<T> put<T>(String path, {Object? body}) async => _fail();
  @override
  Future<T> delete<T>(String path) async => _fail();
}

void main() {
  testWidgets('ThemePickerSheet shows all four tabs, live preview and Apply',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          localDbProvider.overrideWithValue(_EmptyDb()),
          apiClientProvider.overrideWithValue(_OfflineClient()),
        ],
        child: MaterialApp(theme: milanLightTheme(),
          home: Scaffold(
            body: ThemePickerSheet(
              scope: const ChatThemeScopeKey.global(),
              embedded: true,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Presets'), findsOneWidget);
    expect(find.text('Solid & Gradient'), findsOneWidget);
    expect(find.text('Photo'), findsOneWidget);
    expect(find.text('Bubble Color'), findsOneWidget);
    // Scope indicator (doc 2 §2.7.4)
    expect(find.text('Applying to: all chats'), findsOneWidget);
    // Reset affordance at every level (doc 2 §2.7.1)
    expect(find.text('Reset to default'), findsOneWidget);
    // Contrast-gated Apply is enabled for the readable factory default.
    expect(tester.widget<FilledButton>(find.byType(FilledButton).first).onPressed,
        isNotNull);
  });

  testWidgets('scope indicator reflects a Saathi-scoped entry point',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          localDbProvider.overrideWithValue(_EmptyDb()),
          apiClientProvider.overrideWithValue(_OfflineClient()),
        ],
        child: MaterialApp(theme: milanLightTheme(),
          home: Scaffold(
            body: ThemePickerSheet(
              scope: const ChatThemeScopeKey.saathi('asha'),
              embedded: true,
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Applying to: this Saathi character'), findsOneWidget);
  });
}
