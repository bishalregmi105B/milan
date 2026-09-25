import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/chat/presentation/screens/chat_extra_screens.dart';
import '../features/chat/presentation/screens/chat_thread_screen.dart';
import '../features/chat/presentation/screens/matches_inbox_screen.dart';
import '../features/discovery/presentation/screens/discovery_extra_screens.dart';
import '../features/discovery/presentation/screens/discover_screen.dart';
import '../features/jhalak/presentation/screens/jhalak_extra_screens.dart';
import '../features/jhalak/presentation/screens/jhalak_snap_screen.dart';
import '../features/jhalak/presentation/screens/snap_composer_screens.dart';
import '../features/onboarding/presentation/screens/interview_screen.dart';
import '../features/onboarding/presentation/screens/onboarding_intro_screens.dart';
import '../features/onboarding/presentation/screens/onboarding_media_screens.dart';
import '../features/onboarding/presentation/screens/onboarding_screens.dart';
import '../features/profile/presentation/screens/my_profile_screen.dart';
import '../features/profile/presentation/screens/my_profile_view_screen.dart';
import '../features/profile/presentation/screens/public_profile_screen.dart';
import '../features/discovery/presentation/screens/user_search_screen.dart';
import '../features/profile/presentation/screens/add_phone_screen.dart';
import '../features/profile/presentation/screens/profile_edit_screens.dart';
import '../features/saathi/presentation/screens/saathi_chat_screen.dart'
    show SaathiChatScreen;
import '../features/saathi/presentation/screens/saathi_extra_screens.dart';
import '../features/saathi/presentation/screens/saathi_memory_screen.dart';
import '../features/safety/presentation/screens/safety_screens.dart';
import '../features/settings/presentation/screens/settings_screens.dart';
import '../features/settings/presentation/screens/appearance_screen.dart';
import '../shared/widgets/main_shell.dart';

/// Doc 3 §5 navigation graph — routes mirror doc 2 §3 screen inventory.
/// Every inventory screen has both a route and a screen implementation.
final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    debugLogDiagnostics: false,
    routes: [
      // Onboarding (screens 1-11)
      GoRoute(path: '/splash', builder: (c, s) => const SplashScreen()),
      GoRoute(path: '/', redirect: (_, __) => '/splash'),
      GoRoute(
        path: '/onboarding/language',
        builder: (c, s) => const LanguageSelectScreen(),
      ),
      GoRoute(
        path: '/onboarding/welcome',
        builder: (c, s) => const OnboardingIntroScreen(),
      ),
      GoRoute(
        path: '/onboarding/phone',
        builder: (c, s) => const PhoneEntryScreen(),
      ),
      GoRoute(
        path: '/onboarding/otp',
        builder: (c, s) => OtpVerifyScreen(
          phone: s.uri.queryParameters['phone'],
          email: s.uri.queryParameters['email'],
        ),
      ),
      GoRoute(
        path: '/onboarding/basic-info',
        builder: (c, s) => BasicInfoScreen(
          phone: s.uri.queryParameters['phone'],
          email: s.uri.queryParameters['email'],
          code: s.uri.queryParameters['code'] ?? '',
          googleUser: s.uri.queryParameters['google'] == '1',
        ),
      ),
      GoRoute(
        path: '/onboarding/photos',
        builder: (c, s) => const PhotoUploadScreen(),
      ),
      GoRoute(
        path: '/onboarding/video-intro',
        builder: (c, s) => const VideoIntroScreen(),
      ),
      GoRoute(
        path: '/onboarding/liveness',
        builder: (c, s) => const LivenessScreen(),
      ),
      GoRoute(
        path: '/onboarding/interview',
        builder: (c, s) => const InterviewScreen(),
      ),
      GoRoute(
        path: '/onboarding/location-primer',
        builder: (c, s) => const PermissionPrimerScreen(isNotifications: false),
      ),
      GoRoute(
        path: '/onboarding/notification-primer',
        builder: (c, s) => const PermissionPrimerScreen(isNotifications: true),
      ),

      // Profile & Identity (screens 12-18)
      GoRoute(path: '/profile/me', builder: (c, s) => const MyProfileScreen()),
      GoRoute(
        path: '/profile/me/view',
        builder: (c, s) => const MyProfileViewScreen(),
      ),
      // Public profile (doc 8 Part D.7) — search results and deck tap-through.
      GoRoute(
        path: '/profile/:userId/public',
        builder: (c, s) =>
            PublicProfileScreen(userId: s.pathParameters['userId']!),
      ),
      // Dedicated people search (doc 8 §A4.9).
      GoRoute(
        path: '/discover/search',
        builder: (c, s) => const UserSearchScreen(),
      ),
      GoRoute(
        path: '/profile/add-phone',
        builder: (c, s) => const AddPhoneScreen(),
      ),
      GoRoute(
        path: '/profile/edit',
        builder: (c, s) => const EditProfileScreen(),
      ),
      GoRoute(
        path: '/profile/prompts',
        builder: (c, s) => const PromptsEditorScreen(),
      ),
      GoRoute(
        path: '/profile/bio-assistant',
        builder: (c, s) => const BioAssistantScreen(),
      ),
      GoRoute(
        path: '/profile/prompt-feedback',
        builder: (c, s) => PromptFeedbackScreen(
          initialAnswer: s.uri.queryParameters['answer'] ?? '',
        ),
      ),
      GoRoute(
        path: '/profile/verification',
        builder: (c, s) => const VerificationStatusScreen(),
      ),
      GoRoute(
        path: '/profile/privacy',
        builder: (c, s) => const EditProfileScreen(),
      ), // discreet toggle lives here
      // Root shell with 4 tabs + Saathi FAB (doc 3 §5)
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => MainShell(shell: shell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/discover',
                builder: (c, s) => const DiscoverScreen(),
              ),
              GoRoute(
                path: '/discover/filters',
                builder: (c, s) => const DiscoveryFiltersScreen(),
              ),
              GoRoute(
                path: '/discover/mode',
                builder: (c, s) => const ModeSwitchScreen(),
              ),
              GoRoute(
                path: '/discover/match/:matchId',
                builder: (c, s) => MatchDetailScreen(
                  matchId: s.pathParameters['matchId']!,
                  showCelebration:
                      s.uri.queryParameters['celebration'] == 'true',
                ),
              ),
              GoRoute(
                path: '/discover/kundali/:matchId',
                builder: (c, s) =>
                    KundaliScreen(matchId: s.pathParameters['matchId']!),
              ),
              GoRoute(
                path: '/discover/who-liked-you',
                builder: (c, s) => const WhoLikedYouScreen(),
              ),
              GoRoute(
                path: '/discover/boost',
                builder: (c, s) => const BoostScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              // Jhalak v2 (§pivot): view-once image snaps, Snapchat-style.
              GoRoute(
                path: '/jhalak',
                builder: (c, s) => const JhalakSnapScreen(),
              ),
              GoRoute(
                path: '/jhalak/compose',
                builder: (c, s) => const SnapComposerScreen(),
              ),
              GoRoute(
                path: '/jhalak/mine',
                builder: (c, s) => const MySnapsScreen(),
              ),
              GoRoute(
                path: '/jhalak/duet/:reelId',
                builder: (c, s) =>
                    DuetRecorderScreen(reelId: s.pathParameters['reelId']!),
              ),
              GoRoute(
                path: '/jhalak/stories',
                builder: (c, s) => const StoriesBarScreen(),
              ),
              GoRoute(
                path: '/jhalak/stories/:userId',
                builder: (c, s) =>
                    StoryViewerScreen(userId: s.pathParameters['userId']!),
              ),
              GoRoute(
                path: '/jhalak/stories/camera',
                builder: (c, s) => const StoryCameraScreen(),
              ),
              GoRoute(
                path: '/jhalak/circles',
                builder: (c, s) => const CirclesDirectoryScreen(),
              ),
              GoRoute(
                path: '/jhalak/circles/:circleId',
                builder: (c, s) =>
                    CircleDetailRoute(circleId: s.pathParameters['circleId']!),
              ),
              GoRoute(
                path: '/jhalak/circles/:circleId/room',
                builder: (c, s) => LiveAudioRoomScreen(
                  circleId: s.pathParameters['circleId']!,
                ),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/chat',
                builder: (c, s) => const MatchesInboxScreen(),
              ),
              GoRoute(
                path: '/chat/:matchId',
                builder: (c, s) =>
                    ChatThreadScreen(matchId: s.pathParameters['matchId']!),
              ),
              GoRoute(
                path: '/chat/:matchId/snap-camera',
                builder: (c, s) =>
                    SnapCameraScreen(matchId: s.pathParameters['matchId']!),
              ),
              GoRoute(
                path: '/chat/:matchId/theme',
                builder: (c, s) =>
                    ChatThemeRouteScreen(matchId: s.pathParameters['matchId']!),
              ),
              GoRoute(
                path: '/chat/:matchId/voice-note',
                builder: (c, s) =>
                    VoiceNoteScreen(matchId: s.pathParameters['matchId']!),
              ),
              GoRoute(
                path: '/chat/:matchId/share-date',
                builder: (c, s) =>
                    ShareDateScreen(matchId: s.pathParameters['matchId']!),
              ),
              GoRoute(
                path: '/chat/:matchId/video-call',
                builder: (c, s) => CallScreen(
                  video: true,
                  matchId: s.pathParameters['matchId']!,
                ),
              ),
              GoRoute(
                path: '/chat/:matchId/voice-call',
                builder: (c, s) => CallScreen(
                  video: false,
                  matchId: s.pathParameters['matchId']!,
                ),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/profile',
                builder: (c, s) => const MyProfileScreen(),
              ),
            ],
          ),
        ],
      ),

      // Saathi AI (screens 46-53)
      GoRoute(
        path: '/saathi/intro',
        builder: (c, s) => const SaathiIntroScreen(),
      ),
      GoRoute(
        path: '/saathi/characters',
        builder: (c, s) => const SaathiGalleryRouteScreen(),
      ),
      GoRoute(
        path: '/saathi/characters/:characterId',
        builder: (c, s) => CharacterDetailScreen(
          characterId: s.pathParameters['characterId']!,
        ),
      ),
      GoRoute(
        path: '/saathi/chat/:characterId',
        builder: (c, s) =>
            SaathiChatScreen(characterId: s.pathParameters['characterId']!),
      ),
      GoRoute(
        path: '/saathi/chat/:characterId/theme',
        builder: (c, s) => SaathiThemeRouteScreen(
          characterId: s.pathParameters['characterId']!,
        ),
      ),
      GoRoute(
        path: '/saathi/chat/:characterId/voice',
        builder: (c, s) => SaathiVoiceCallScreen(
          characterId: s.pathParameters['characterId']!,
        ),
      ),
      GoRoute(
        path: '/saathi/settings',
        builder: (c, s) {
          final character = s.uri.queryParameters['character'] ?? 'asha';
          return SaathiSettingsScreen(characterId: character);
        },
      ),
      GoRoute(
        path: '/saathi/debrief/:matchId',
        builder: (c, s) =>
            SessionDebriefScreen(matchId: s.pathParameters['matchId']!),
      ),
      GoRoute(
        path: '/saathi/memory',
        builder: (c, s) => SaathiMemoryScreen(
          sessionId: s.uri.queryParameters['session'] ?? '',
        ),
      ),

      // Safety (screens 54-59)
      GoRoute(path: '/safety', builder: (c, s) => const SafetyCenterScreen()),
      GoRoute(
        path: '/safety/report/:targetId',
        builder: (c, s) =>
            ReportFlowScreen(targetId: s.pathParameters['targetId']!),
      ),
      GoRoute(
        path: '/safety/blocklist',
        builder: (c, s) => const BlockListScreen(),
      ),
      GoRoute(path: '/safety/panic', builder: (c, s) => const PanicScreen()),
      GoRoute(
        path: '/safety/verification',
        builder: (c, s) => const VerificationDetailScreen(),
      ),

      // Notifications & Settings (screens 60-66)
      GoRoute(
        path: '/notifications',
        builder: (c, s) => const NotificationCenterScreen(),
      ),
      GoRoute(
        path: '/settings/notifications',
        builder: (c, s) => const NotificationPreferencesScreen(),
      ),
      GoRoute(
        path: '/settings/account',
        builder: (c, s) => const AccountSettingsScreen(),
      ),
      GoRoute(
        path: '/settings/language',
        builder: (c, s) => const LanguageAccessibilityScreen(),
      ),
      // doc 8 §A3.3: my_profile_screen pushes /settings/appearance — the
      // route never existed, so the tap hit GoRouter's error page.
      GoRoute(
        path: '/settings/appearance',
        builder: (c, s) => const AppearanceScreen(),
      ),
      GoRoute(
        path: '/settings/payment-methods',
        builder: (c, s) => const PaymentMethodsScreen(),
      ),
      GoRoute(
        path: '/settings/subscription',
        builder: (c, s) => const SubscriptionPlansScreen(),
      ),
      GoRoute(path: '/settings/help', builder: (c, s) => const HelpFaqScreen()),

      // Personalization (screen 67)
    ],
  );
});
