import 'package:permission_handler/permission_handler.dart';

class PermissionService {
  Future<bool> camera() => Permission.camera.request().isGranted;

  Future<bool> microphone() => Permission.microphone.request().isGranted;

  Future<bool> location() => Permission.locationWhenInUse.request().isGranted;

  Future<bool> notifications() => Permission.notification.request().isGranted;

  Future<bool> gallery() async {
    final status = await Permission.photos.request();
    return status.isGranted || status.isLimited;
  }
}
