import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'core/notifications/push_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // OneSignal push (§push v2): boot init — a graceful no-op when the
  // ONESIGNAL_APP_ID dart-define is absent (keys arrive later).
  PushService.initOnce();
  runApp(const ProviderScope(child: MilanApp()));
}
