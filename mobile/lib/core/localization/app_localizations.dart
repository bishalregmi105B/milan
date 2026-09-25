import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ne.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'localization/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ne'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Milan'**
  String get appTitle;

  /// No description provided for @navDiscover.
  ///
  /// In en, this message translates to:
  /// **'Discover'**
  String get navDiscover;

  /// No description provided for @navJhalak.
  ///
  /// In en, this message translates to:
  /// **'Jhalak'**
  String get navJhalak;

  /// No description provided for @navChat.
  ///
  /// In en, this message translates to:
  /// **'Chat'**
  String get navChat;

  /// No description provided for @navProfile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get navProfile;

  /// No description provided for @saathi.
  ///
  /// In en, this message translates to:
  /// **'Saathi AI'**
  String get saathi;

  /// No description provided for @onboardingLanguageTitle.
  ///
  /// In en, this message translates to:
  /// **'Choose your language'**
  String get onboardingLanguageTitle;

  /// No description provided for @onboardingLanguageNepali.
  ///
  /// In en, this message translates to:
  /// **'नेपाली'**
  String get onboardingLanguageNepali;

  /// No description provided for @onboardingLanguageEnglish.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get onboardingLanguageEnglish;

  /// No description provided for @onboardingPhoneTitle.
  ///
  /// In en, this message translates to:
  /// **'Enter your phone number'**
  String get onboardingPhoneTitle;

  /// No description provided for @onboardingPhoneHint.
  ///
  /// In en, this message translates to:
  /// **'98XXXXXXXX'**
  String get onboardingPhoneHint;

  /// No description provided for @onboardingOtpTitle.
  ///
  /// In en, this message translates to:
  /// **'Verify your number'**
  String get onboardingOtpTitle;

  /// No description provided for @onboardingOtpResend.
  ///
  /// In en, this message translates to:
  /// **'Resend code'**
  String get onboardingOtpResend;

  /// No description provided for @onboardingBasicInfoTitle.
  ///
  /// In en, this message translates to:
  /// **'A little about you'**
  String get onboardingBasicInfoTitle;

  /// No description provided for @onboardingName.
  ///
  /// In en, this message translates to:
  /// **'Name'**
  String get onboardingName;

  /// No description provided for @onboardingBirthDate.
  ///
  /// In en, this message translates to:
  /// **'Birth date'**
  String get onboardingBirthDate;

  /// No description provided for @onboardingGender.
  ///
  /// In en, this message translates to:
  /// **'Gender'**
  String get onboardingGender;

  /// No description provided for @onboardingPhotosTitle.
  ///
  /// In en, this message translates to:
  /// **'Add your photos'**
  String get onboardingPhotosTitle;

  /// No description provided for @onboardingPhotosRule.
  ///
  /// In en, this message translates to:
  /// **'Minimum 2, maximum 6 photos'**
  String get onboardingPhotosRule;

  /// No description provided for @onboardingVideoIntro.
  ///
  /// In en, this message translates to:
  /// **'Record a short intro video (optional)'**
  String get onboardingVideoIntro;

  /// No description provided for @onboardingLivenessTitle.
  ///
  /// In en, this message translates to:
  /// **'Let\'s verify it\'s really you'**
  String get onboardingLivenessTitle;

  /// No description provided for @onboardingLivenessBody.
  ///
  /// In en, this message translates to:
  /// **'We take a quick live selfie to verify your profile and keep Milan safe.'**
  String get onboardingLivenessBody;

  /// No description provided for @onboardingInterviewTitle.
  ///
  /// In en, this message translates to:
  /// **'Tell us what you\'re looking for'**
  String get onboardingInterviewTitle;

  /// No description provided for @onboardingLocationPrimer.
  ///
  /// In en, this message translates to:
  /// **'Why we need your location'**
  String get onboardingLocationPrimer;

  /// No description provided for @onboardingNotificationPrimer.
  ///
  /// In en, this message translates to:
  /// **'Stay in the loop'**
  String get onboardingNotificationPrimer;

  /// No description provided for @commonNext.
  ///
  /// In en, this message translates to:
  /// **'Next'**
  String get commonNext;

  /// No description provided for @commonSkip.
  ///
  /// In en, this message translates to:
  /// **'Skip'**
  String get commonSkip;

  /// No description provided for @commonLoading.
  ///
  /// In en, this message translates to:
  /// **'Please wait…'**
  String get commonLoading;

  /// No description provided for @commonContinue.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get commonContinue;

  /// No description provided for @commonRetry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get commonRetry;

  /// No description provided for @commonCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get commonCancel;

  /// No description provided for @commonApply.
  ///
  /// In en, this message translates to:
  /// **'Apply'**
  String get commonApply;

  /// No description provided for @commonResetToDefault.
  ///
  /// In en, this message translates to:
  /// **'Reset to default'**
  String get commonResetToDefault;

  /// No description provided for @commonReport.
  ///
  /// In en, this message translates to:
  /// **'Report'**
  String get commonReport;

  /// No description provided for @commonBlock.
  ///
  /// In en, this message translates to:
  /// **'Block'**
  String get commonBlock;

  /// No description provided for @commonSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get commonSave;

  /// No description provided for @discoverEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'That\'s everyone for today'**
  String get discoverEmptyTitle;

  /// No description provided for @discoverEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'Quality over quantity — check back tomorrow for fresh matches.'**
  String get discoverEmptyBody;

  /// No description provided for @discoverSeriousMode.
  ///
  /// In en, this message translates to:
  /// **'Serious'**
  String get discoverSeriousMode;

  /// No description provided for @discoverCasualMode.
  ///
  /// In en, this message translates to:
  /// **'Casual'**
  String get discoverCasualMode;

  /// No description provided for @discoverWhoLikedYou.
  ///
  /// In en, this message translates to:
  /// **'Who liked you'**
  String get discoverWhoLikedYou;

  /// No description provided for @discoverKundaliMode.
  ///
  /// In en, this message translates to:
  /// **'Kundali Mode'**
  String get discoverKundaliMode;

  /// No description provided for @kundaliDisclaimer.
  ///
  /// In en, this message translates to:
  /// **'A fun cultural tradition and conversation piece — not a scientific measure of compatibility.'**
  String get kundaliDisclaimer;

  /// No description provided for @chatThemeEntry.
  ///
  /// In en, this message translates to:
  /// **'Chat theme'**
  String get chatThemeEntry;

  /// No description provided for @chatStudioTitle.
  ///
  /// In en, this message translates to:
  /// **'Chat Theme & Wallpaper Studio'**
  String get chatStudioTitle;

  /// No description provided for @chatStudioPresets.
  ///
  /// In en, this message translates to:
  /// **'Presets'**
  String get chatStudioPresets;

  /// No description provided for @chatStudioSolidGradient.
  ///
  /// In en, this message translates to:
  /// **'Solid & Gradient'**
  String get chatStudioSolidGradient;

  /// No description provided for @chatStudioPhoto.
  ///
  /// In en, this message translates to:
  /// **'Photo'**
  String get chatStudioPhoto;

  /// No description provided for @chatStudioBubbleColor.
  ///
  /// In en, this message translates to:
  /// **'Bubble Color'**
  String get chatStudioBubbleColor;

  /// No description provided for @chatStudioScopeAllChats.
  ///
  /// In en, this message translates to:
  /// **'Applying to: all chats'**
  String get chatStudioScopeAllChats;

  /// No description provided for @chatStudioScopeThisChat.
  ///
  /// In en, this message translates to:
  /// **'Applying to: this chat'**
  String get chatStudioScopeThisChat;

  /// No description provided for @chatStudioBubbleShape.
  ///
  /// In en, this message translates to:
  /// **'Bubble shape'**
  String get chatStudioBubbleShape;

  /// No description provided for @chatStudioTextSize.
  ///
  /// In en, this message translates to:
  /// **'Chat text size'**
  String get chatStudioTextSize;

  /// No description provided for @chatStudioDarkBrightness.
  ///
  /// In en, this message translates to:
  /// **'Dark mode brightness'**
  String get chatStudioDarkBrightness;

  /// No description provided for @chatStudioContrastWarning.
  ///
  /// In en, this message translates to:
  /// **'This color combination is hard to read. Try a different bubble or text color.'**
  String get chatStudioContrastWarning;

  /// No description provided for @chatAiLabel.
  ///
  /// In en, this message translates to:
  /// **'AI'**
  String get chatAiLabel;

  /// No description provided for @saathiHeaderTag.
  ///
  /// In en, this message translates to:
  /// **'Saathi · AI companion'**
  String get saathiHeaderTag;

  /// No description provided for @saathiIntroTitle.
  ///
  /// In en, this message translates to:
  /// **'Meet Saathi'**
  String get saathiIntroTitle;

  /// No description provided for @saathiConsentBody.
  ///
  /// In en, this message translates to:
  /// **'Saathi is an AI conversation companion to help you practice and build confidence. It is not a real person and not a substitute for human connection. 18+ only.'**
  String get saathiConsentBody;

  /// No description provided for @saathiConfirm18.
  ///
  /// In en, this message translates to:
  /// **'I confirm I am 18 or older'**
  String get saathiConfirm18;

  /// No description provided for @saathiSettingsProactive.
  ///
  /// In en, this message translates to:
  /// **'Let Saathi message me first'**
  String get saathiSettingsProactive;

  /// No description provided for @saathiPause.
  ///
  /// In en, this message translates to:
  /// **'Pause Saathi'**
  String get saathiPause;

  /// No description provided for @saathiMemoryTitle.
  ///
  /// In en, this message translates to:
  /// **'What Saathi Remembers'**
  String get saathiMemoryTitle;

  /// No description provided for @saathiMemoryClearAll.
  ///
  /// In en, this message translates to:
  /// **'Clear all'**
  String get saathiMemoryClearAll;

  /// No description provided for @safetyShareMyDate.
  ///
  /// In en, this message translates to:
  /// **'Share My Date'**
  String get safetyShareMyDate;

  /// No description provided for @settingsNotifications.
  ///
  /// In en, this message translates to:
  /// **'Notifications'**
  String get settingsNotifications;

  /// No description provided for @settingsAccount.
  ///
  /// In en, this message translates to:
  /// **'Account settings'**
  String get settingsAccount;

  /// No description provided for @settingsLanguage.
  ///
  /// In en, this message translates to:
  /// **'Language & Accessibility'**
  String get settingsLanguage;

  /// No description provided for @settingsPaymentMethods.
  ///
  /// In en, this message translates to:
  /// **'Payment Methods'**
  String get settingsPaymentMethods;

  /// No description provided for @settingsSubscription.
  ///
  /// In en, this message translates to:
  /// **'Subscription Plans'**
  String get settingsSubscription;

  /// No description provided for @settingsHelp.
  ///
  /// In en, this message translates to:
  /// **'Help & Support'**
  String get settingsHelp;

  /// No description provided for @errorGeneric.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Please try again.'**
  String get errorGeneric;

  /// No description provided for @aiUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Milan\'s AI is taking a breather — try again shortly.'**
  String get aiUnavailable;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ne'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ne':
      return AppLocalizationsNe();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
