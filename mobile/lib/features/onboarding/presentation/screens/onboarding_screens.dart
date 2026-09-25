import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../app/app.dart' show pendingDeepLinkProvider;
import '../../../../app/theme/color_tokens.dart';
import '../../../../app/theme/spacing_tokens.dart';
import '../../../../app/theme/type_tokens.dart';
import '../../../../core/localization/app_localizations.dart';
import '../../../../core/network/api_client.dart';
import '../../../../shared/widgets/milan_logo.dart';
import '../../../auth/application/auth_provider.dart';

/// Screen 1 — Splash with Junction Mark load animation.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1400),
  );

  @override
  void initState() {
    super.initState();
    _controller.forward();
    // Let the logo animation play (900ms), then WAIT for session restore to
    // actually finish instead of racing it: the fixed 1.2s delay used to
    // route returning users into signup while /profile/me was still loading.
    Future.delayed(const Duration(milliseconds: 950), () async {
      Session? session;
      try {
        session = await ref
            .read(authProvider.future)
            .timeout(const Duration(seconds: 6));
      } catch (_) {
        // restore failed (offline without a session) — treat as signed out
      }
      if (!mounted) return;
      if (session != null) {
        // A notification tapped on a cold start parked its destination while we
        // were restoring; honour it instead of dropping the user on discovery.
        final deepLink = ref.read(pendingDeepLinkProvider);
        if (deepLink != null && session.hasProfile) {
          ref.read(pendingDeepLinkProvider.notifier).state = null;
          context.go(deepLink);
          return;
        }
        context.go(session.hasProfile ? '/discover' : '/onboarding/basic-info');
      } else {
        // Fresh (or signed-out) installs get the animated brand intro first.
        context.go('/onboarding/welcome');
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      backgroundColor: milan.paper0,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // The junction mark draws itself: rings grow in, the blue bridge
            // arcs across, the marigold tika drops into place.
            MilanLogoMark(size: 108, animation: _controller),
            SizedBox(height: Spacing.lg),
            Text(
              'Milan',
              style: TextStyle(
                fontFamily: 'Sora',
                fontSize: 30,
                fontWeight: FontWeight.w700,
                color: milan.ink900,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Screen 2 — Language select.
class LanguageSelectScreen extends StatelessWidget {
  const LanguageSelectScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: EdgeInsets.all(Spacing.xl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(height: Spacing.huge),
              Text(
                AppLocalizations.of(context)!.onboardingLanguageTitle,
                style: context.h1,
              ),
              SizedBox(height: Spacing.xxl),
              _LanguageCard(
                label: 'नेपाली',
                sub: 'Nepali',
                color: milan.marigold500,
                onTap: () => context.push('/onboarding/phone'),
              ),
              SizedBox(height: Spacing.lg),
              _LanguageCard(
                label: 'English',
                sub: 'अंग्रेजी',
                color: milan.dhaka500,
                onTap: () => context.push('/onboarding/phone'),
              ),
              Spacer(),
              OutlinedButton(
                onPressed: () => context.push('/onboarding/phone'),
                child: Text(AppLocalizations.of(context)!.commonContinue),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LanguageCard extends StatelessWidget {
  const _LanguageCard({
    required this.label,
    required this.sub,
    required this.color,
    this.onTap,
  });
  final String label;
  final String sub;
  final Color color;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Spacing.radiusLg),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(Spacing.radiusLg),
        onTap: onTap,
        child: Padding(
          padding: EdgeInsets.all(Spacing.xl),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: color.withValues(alpha: .2),
                child: Icon(Icons.language, color: color),
              ),
              SizedBox(width: Spacing.lg),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    sub,
                    style: TextStyle(
                      color: Theme.of(context).extension<MilanColors>()!.ink600,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Screen 3 — Phone entry (+977 locked with override).
class PhoneEntryScreen extends ConsumerStatefulWidget {
  const PhoneEntryScreen({super.key});

  @override
  ConsumerState<PhoneEntryScreen> createState() => _PhoneEntryScreenState();
}

class _PhoneEntryScreenState extends ConsumerState<PhoneEntryScreen> {
  final _controller = TextEditingController();
  final _countryCode = TextEditingController(text: '97');
  bool _overrideCountry = false;
  bool _sending = false;
  bool _useEmail =
      true; // email-first login (phone optional, can be added later)

  @override
  void dispose() {
    _controller.dispose();
    _countryCode.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _sending = true);
    try {
      if (_useEmail) {
        final email = _controller.text.trim().toLowerCase();
        await ref.read(authProvider.notifier).requestOtp(email: email);
        if (!mounted) return;
        context.push('/onboarding/otp?email=$email');
      } else {
        final phone =
            '${_overrideCountry ? "+${_controller.text.trim()}" : "+977${_controller.text.trim()}"}';
        await ref.read(authProvider.notifier).requestOtp(phone: phone);
        if (!mounted) return;
        context.push('/onboarding/otp?phone=$phone');
      }
    } on AppException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.displayMessage)));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  Future<void> _signInWithGoogle() async {
    final picked = await showDatePicker(
      context: context,
      firstDate: DateTime(1920),
      lastDate: DateTime.now(),
      helpText: 'Confirm your date of birth',
    );
    if (picked == null || !mounted) return;
    final today = DateTime.now();
    final hasNotHadBirthday =
        today.month < picked.month ||
        (today.month == picked.month && today.day < picked.day);
    final age = today.year - picked.year - (hasNotHadBirthday ? 1 : 0);
    if (age < 18) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('You must be 18 or older to use Milan.')),
      );
      return;
    }
    setState(() => _sending = true);
    try {
      final session = await ref
          .read(authProvider.notifier)
          .signInWithGoogle(
            dateOfBirth: picked.toIso8601String().split('T').first,
          );
      if (!mounted) return;
      context.go(
        session.hasProfile ? '/discover' : '/onboarding/basic-info?google=1',
      );
    } on AppException catch (e) {
      if (mounted && e.code != 'google_cancelled') {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.displayMessage)));
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(),
      body: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              AppLocalizations.of(context)!.onboardingPhoneTitle,
              style: context.h1,
            ),
            SizedBox(height: Spacing.lg),
            // Sign-up method — phone or email, same OTP flow for both.
            SegmentedButton<bool>(
              segments: const [
                ButtonSegment(
                  value: true,
                  icon: Icon(Icons.alternate_email),
                  label: Text('Email'),
                ),
                ButtonSegment(
                  value: false,
                  icon: Icon(Icons.phone_android),
                  label: Text('Phone'),
                ),
              ],
              selected: {_useEmail},
              onSelectionChanged: (selection) =>
                  setState(() => _useEmail = selection.first),
            ),
            SizedBox(height: Spacing.lg),
            // Google Sign-In — one tap, same session as OTP (§auth)
            OutlinedButton.icon(
              icon: const Icon(Icons.g_mobiledata, size: 28),
              label: const Text('Continue with Google'),
              onPressed: _sending ? null : _signInWithGoogle,
            ),
            SizedBox(height: Spacing.lg),
            Row(
              children: [
                Expanded(child: Divider(color: milan.line200)),
                Padding(
                  padding: EdgeInsets.symmetric(horizontal: Spacing.md),
                  child: Text(
                    'or use OTP',
                    style: TextStyle(fontSize: 12, color: milan.ink400),
                  ),
                ),
                Expanded(child: Divider(color: milan.line200)),
              ],
            ),
            SizedBox(height: Spacing.xl),
            Row(
              children: [
                if (!_useEmail && _overrideCountry)
                  SizedBox(
                    width: 76,
                    child: TextField(
                      controller: _countryCode,
                      keyboardType: TextInputType.phone,
                      decoration: const InputDecoration(prefixText: '+'),
                    ),
                  ),
                Expanded(
                  child: TextField(
                    controller: _controller,
                    keyboardType: _useEmail
                        ? TextInputType.emailAddress
                        : TextInputType.phone,
                    autofillHints: _useEmail
                        ? [AutofillHints.email]
                        : [AutofillHints.telephoneNumber],
                    // rebuild on every keystroke so the Next button's enabled
                    // state re-evaluates (was frozen at "empty -> disabled")
                    onChanged: (_) => setState(() {}),
                    decoration: InputDecoration(
                      prefixText: !_useEmail && !_overrideCountry
                          ? '+977 '
                          : '',
                      hintText: _useEmail
                          ? 'you@example.com'
                          : AppLocalizations.of(context)!.onboardingPhoneHint,
                    ),
                  ),
                ),
              ],
            ),
            if (!_useEmail) ...[
              TextButton(
                onPressed: () =>
                    setState(() => _overrideCountry = !_overrideCountry),
                child: Text(
                  _overrideCountry
                      ? 'Use +977'
                      : 'Diaspora? Change country code',
                ),
              ),
              Text(
                'Phone is optional — you can add it later from your profile.',
                style: TextStyle(fontSize: 12),
              ),
            ],
            Spacer(),
            FilledButton(
              onPressed: _sending || _controller.text.trim().isEmpty
                  ? null
                  : _submit,
              child: Text(
                _sending
                    ? AppLocalizations.of(context)!.commonLoading
                    : AppLocalizations.of(context)!.commonNext,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Screen 4 — OTP verify. Returning users (account exists) verify here and
/// go straight into the app — they never see the sign-up form again, and
/// their saved profile is never overwritten (doc 8 §A4). New accounts carry
/// the code to basic-info for DOB/name collection.
/// Works for both phone and email sign-up.
class OtpVerifyScreen extends ConsumerStatefulWidget {
  const OtpVerifyScreen({super.key, this.phone, this.email});
  final String? phone;
  final String? email;

  String get identifier => phone ?? email ?? '';

  @override
  ConsumerState<OtpVerifyScreen> createState() => _OtpVerifyScreenState();
}

class _OtpVerifyScreenState extends ConsumerState<OtpVerifyScreen> {
  final _code = TextEditingController();
  int _resendIn = 45;
  bool _resending = false;
  bool _verifying = false;
  String? _error;
  StreamSubscription<int>? _timer;

  @override
  void initState() {
    super.initState();
    _timer = Stream.periodic(const Duration(seconds: 1), (t) => t)
        .take(45)
        .listen((_) {
          if (mounted) setState(() => _resendIn--);
        });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _code.dispose();
    super.dispose();
  }

  Future<void> _resend() async {
    setState(() => _resending = true);
    try {
      await ref
          .read(authProvider.notifier)
          .requestOtp(phone: widget.phone, email: widget.email);
      if (!mounted) return;
      setState(() {
        _resendIn = 45;
        _resending = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('A new code is on its way.')),
      );
    } on AppException catch (e) {
      if (!mounted) return;
      setState(() => _resending = false);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.displayMessage)));
    }
  }

  /// Verify first without asking for a date of birth. The server only
  /// reveals whether onboarding is needed after the code has been accepted;
  /// the code is kept in the current screen state until that decision.
  Future<void> _verifyReturningUser() async {
    setState(() {
      _verifying = true;
      _error = null;
    });
    try {
      await ref
          .read(authProvider.notifier)
          .verifyOtp(
            phone: widget.phone,
            email: widget.email,
            code: _code.text,
          );
      if (!mounted) return;
      final session = ref.read(authProvider).valueOrNull;
      context.go(
        session?.hasProfile == true ? '/discover' : '/onboarding/basic-info',
      );
    } on AppException catch (e) {
      if (!mounted) return;
      if (e.code == 'onboarding_required') {
        final params = [
          if (widget.phone != null) 'phone=${widget.phone}',
          if (widget.email != null) 'email=${widget.email}',
          'code=${_code.text}',
        ].join('&');
        context.push('/onboarding/basic-info?$params');
        return;
      }
      setState(() {
        _verifying = false;
        _error = e.displayMessage;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _verifying = false;
        _error =
            "Couldn't reach Milan's servers. Check your connection and try again.";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    return Scaffold(
      appBar: AppBar(),
      body: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              AppLocalizations.of(context)!.onboardingOtpTitle,
              style: context.h1,
            ),
            SizedBox(height: Spacing.sm),
            Text(widget.identifier, style: TextStyle(color: milan.ink600)),
            SizedBox(height: Spacing.xxl),
            TextField(
              controller: _code,
              keyboardType: TextInputType.number,
              maxLength: 6,
              textAlign: TextAlign.center,
              autofocus: true,
              style: const TextStyle(fontSize: 26, letterSpacing: 12),
              decoration: const InputDecoration(counterText: ''),
              onChanged: (_) => setState(() {}),
            ),
            SizedBox(height: Spacing.md),
            if (_error != null)
              Padding(
                padding: EdgeInsets.only(bottom: Spacing.md),
                child: Text(
                  _error!,
                  style: TextStyle(color: milan.error500),
                  textAlign: TextAlign.center,
                ),
              ),
            Center(
              child: TextButton(
                onPressed: (_resendIn > 0 || _resending) ? null : _resend,
                child: Text(
                  _resendIn > 0
                      ? '$_resendIn s'
                      : AppLocalizations.of(context)!.onboardingOtpResend,
                ),
              ),
            ),
            Spacer(),
            FilledButton(
              onPressed: _code.text.length == 6 && !_verifying
                  ? _verifyReturningUser
                  : null,
              child: Text(
                _verifying
                    ? 'Signing you in…'
                    : AppLocalizations.of(context)!.commonContinue,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Screen 5 — Basic info with hard 18+ age gate.
class BasicInfoScreen extends ConsumerStatefulWidget {
  const BasicInfoScreen({
    super.key,
    this.phone,
    this.email,
    this.code = '',
    this.googleUser = false,
  });
  final String? phone;
  final String? email;
  final String code;
  final bool googleUser;

  @override
  ConsumerState<BasicInfoScreen> createState() => _BasicInfoScreenState();
}

class _BasicInfoScreenState extends ConsumerState<BasicInfoScreen> {
  final _name = TextEditingController();
  DateTime? _dob;
  String? _gender;
  String? _error;
  bool _submitting = false;

  ApiClient get _api => ref.read(apiClientProvider);

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final requiresDob = !widget.googleUser;
    final under18 =
        requiresDob &&
        _dob != null &&
        DateTime.now().difference(_dob!).inDays < 18 * 365;
    return Scaffold(
      appBar: AppBar(),
      body: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: ListView(
          children: [
            Text(
              AppLocalizations.of(context)!.onboardingBasicInfoTitle,
              style: context.h1,
            ),
            SizedBox(height: Spacing.xl),
            TextField(
              controller: _name,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                labelText: AppLocalizations.of(context)!.onboardingName,
              ),
            ),
            SizedBox(height: Spacing.lg),
            if (!widget.googleUser) ...[
              ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(AppLocalizations.of(context)!.onboardingBirthDate),
                subtitle: Text(
                  _dob?.toIso8601String().split('T').first ?? 'YYYY-MM-DD',
                ),
                trailing: const Icon(Icons.calendar_month),
                onTap: () async {
                  final picked = await showDatePicker(
                    context: context,
                    firstDate: DateTime(1940),
                    lastDate: DateTime.now(),
                  );
                  if (picked != null) setState(() => _dob = picked);
                },
              ),
            ],
            if (under18)
              Text(
                'You must be 18+ to use Milan.',
                style: TextStyle(color: milan.error500),
              ),
            SizedBox(height: Spacing.lg),
            Wrap(
              spacing: Spacing.md,
              children: [
                for (final g in ['female', 'male', 'nonbinary', 'other'])
                  ChoiceChip(
                    label: Text(g),
                    selected: _gender == g,
                    onSelected: (_) => setState(() => _gender = g),
                  ),
              ],
            ),
            SizedBox(height: Spacing.xxl),
            if (_error != null)
              Padding(
                padding: EdgeInsets.only(bottom: Spacing.md),
                child: Text(_error!, style: TextStyle(color: milan.error500)),
              ),
            FilledButton(
              onPressed:
                  (requiresDob && _dob == null ||
                      under18 ||
                      _gender == null ||
                      _name.text.isEmpty ||
                      _submitting)
                  ? null
                  : () async {
                      setState(() => _submitting = true);
                      try {
                        if (requiresDob) {
                          await ref
                              .read(authProvider.notifier)
                              .verifyOtp(
                                phone: widget.phone,
                                email: widget.email,
                                code: widget.code,
                                dateOfBirth: _dob!
                                    .toIso8601String()
                                    .split('T')
                                    .first,
                              );
                        }
                        // Profile is upserted server-side: persist the name the
                        // user just typed instead of dropping it.
                        await _api.put(
                          '/profile/me',
                          body: {
                            'display_name': _name.text.trim(),
                            'gender': _gender,
                          },
                        );
                        if (!mounted) return;
                        context.go('/onboarding/photos');
                      } on AppException catch (e) {
                        if (!mounted) return;
                        if (requiresDob && e.code == 'invalid_or_expired_otp') {
                          final params = [
                            if (widget.phone != null) 'phone=${widget.phone}',
                            if (widget.email != null) 'email=${widget.email}',
                          ].join('&');
                          context.go('/onboarding/otp?$params&expired=1');
                        } else {
                          setState(() {
                            _submitting = false;
                            _error = e.code == 'age_gate_18_plus'
                                ? 'You must be 18+ to use Milan.'
                                : e.displayMessage;
                          });
                        }
                      } catch (_) {
                        if (!mounted) return;
                        setState(() {
                          _submitting = false;
                          _error =
                              "Couldn't reach Milan's servers. Check your connection and try again.";
                        });
                      }
                    },
              child: Text(
                _submitting
                    ? AppLocalizations.of(context)!.commonLoading
                    : AppLocalizations.of(context)!.commonContinue,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Screens 10 & 11 — permission primers.
class PermissionPrimerScreen extends StatelessWidget {
  const PermissionPrimerScreen({super.key, required this.isNotifications});
  final bool isNotifications;

  @override
  Widget build(BuildContext context) {
    final milan = Theme.of(context).extension<MilanColors>()!;
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(
        actions: [
          TextButton(
            onPressed: () => context.go('/discover'),
            child: Text(l10n.commonSkip),
          ),
        ],
      ),
      body: Padding(
        padding: EdgeInsets.all(Spacing.xl),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Icon(
              isNotifications
                  ? Icons.notifications_active_outlined
                  : Icons.location_on_outlined,
              size: 64,
              color: milan.marigold500,
            ),
            SizedBox(height: Spacing.xl),
            Text(
              isNotifications
                  ? l10n.onboardingNotificationPrimer
                  : l10n.onboardingLocationPrimer,
              style: context.h2,
            ),
            SizedBox(height: Spacing.md),
            Text(
              isNotifications
                  ? 'New match alerts, message notifications and optional Saathi check-ins. Every category is controllable and capped.'
                  : 'Your location is used only to rank nearby candidates and never shown exactly to other users.',
              style: TextStyle(color: milan.ink600, height: 1.5),
            ),
            if (isNotifications) ...[
              SizedBox(height: Spacing.xl),
              for (final sample in [
                'Match found 🎉',
                'Sunita sent a message',
                'Saathi practice nudge',
              ])
                Padding(
                  padding: EdgeInsets.only(bottom: Spacing.md),
                  child: Container(
                    padding: EdgeInsets.all(Spacing.lg),
                    decoration: BoxDecoration(
                      color: milan.paper100,
                      borderRadius: BorderRadius.circular(Spacing.radiusMd),
                    ),
                    child: Text(sample),
                  ),
                ),
            ],
            Spacer(),
            FilledButton(
              onPressed: () => context.go('/discover'),
              child: Text(l10n.commonContinue),
            ),
          ],
        ),
      ),
    );
  }
}
