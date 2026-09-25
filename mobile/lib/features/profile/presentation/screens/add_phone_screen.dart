import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../core/network/api_client.dart';

/// Email-first accounts can attach a phone number later — OTP-verified, same
/// proof as signup. Phone stays OPTIONAL; nothing blocks signup without it.
class AddPhoneScreen extends ConsumerStatefulWidget {
  const AddPhoneScreen({super.key});

  @override
  ConsumerState<AddPhoneScreen> createState() => _AddPhoneScreenState();
}

class _AddPhoneScreenState extends ConsumerState<AddPhoneScreen> {
  final _phone = TextEditingController();
  final _code = TextEditingController();
  bool _codeSent = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _phone.dispose();
    _code.dispose();
    super.dispose();
  }

  Future<void> _sendCode() async {
    final phone = _phone.text.trim();
    if (phone.isEmpty || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(apiClientProvider)
          .post('/profile/phone/request-otp', body: {'phone': phone});
      if (!mounted) return;
      setState(() {
        _codeSent = true;
        _busy = false;
      });
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = e.displayMessage;
      });
    }
  }

  Future<void> _verifyAndLink() async {
    final phone = _phone.text.trim();
    final code = _code.text.trim();
    if (phone.isEmpty || code.isEmpty || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(apiClientProvider).post('/profile/phone',
          body: {'phone': phone, 'code': code});
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Phone number linked to your account.')));
      context.pop();
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = e.displayMessage;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(title: const Text('Add a phone number')),
      body: ListView(padding: EdgeInsets.all(Spacing.xl), children: [
        Text('Optional — your email is all you need to sign in. Adding a phone lets people find you by number and lets us send important alerts by SMS.',
            style: TextStyle(fontSize: 13, color: milan.ink600, height: 1.5)),
        SizedBox(height: Spacing.xl),
        TextField(
          controller: _phone,
          keyboardType: TextInputType.phone,
          enabled: !_codeSent,
          decoration: const InputDecoration(
              prefixText: '+977 ', hintText: '98XXXXXXXX'),
        ),
        if (_codeSent) ...[
          SizedBox(height: Spacing.lg),
          TextField(
            controller: _code,
            keyboardType: TextInputType.number,
            maxLength: 6,
            onChanged: (_) => setState(() {}),
            decoration: const InputDecoration(labelText: '6-digit code sent by SMS'),
          ),
        ],
        if (_error != null)
          Padding(padding: EdgeInsets.only(top: Spacing.md),
              child: Text(_error!, style: TextStyle(fontSize: 12, color: milan.error500))),
        SizedBox(height: Spacing.xl),
        FilledButton(
          onPressed: _busy
              ? null
              : (!_codeSent
                  ? _sendCode
                  : (_code.text.trim().length == 6 ? _verifyAndLink : null)),
          child: Text(_busy
              ? 'Please wait…'
              : (!_codeSent ? 'Send code' : 'Verify & link')),
        ),
      ]),
    );
  }
}
