# Milan v2 — Flutter App Build Prompt

> **Document 3 of 7.** This is a direct, paste-into-your-AI-code-editor build prompt (Claude Code, Cursor, Windsurf, GitLab Duo, etc.). It assumes the AI editor also has access to `02_milan_design_system_and_screens.md` (tokens + screen list) and `05_milan_ai_companion_and_matching_groq_prompt.md` (AI request/response contracts). If your editor can only take one file at a time, paste document 2 first, then this one, then document 5.

---

## Prompt starts here

You are building **Milan v2**, a Flutter dating and connection app for the Nepal market. Follow this specification exactly. Where a decision isn't specified, prefer the simplest option consistent with the architecture below, and leave a `// TODO(milan):` comment explaining the assumption rather than silently guessing.

### 1. Architecture

- **State management:** Riverpod (`flutter_riverpod` + `riverpod_annotation` for code-gen providers). No `Provider`, no `GetX`, no `Bloc` — Riverpod only, for consistency with the existing codebase.
- **Navigation:** `go_router`, declarative routes, deep-link-ready (`milan://` scheme + universal links for match/chat/reel sharing).
- **Models:** `freezed` + `json_serializable` for every data class. No hand-written `toJson`/`fromJson`.
- **Networking:** `dio` with an interceptor-based client (`ApiClient`) handling auth headers, refresh-token retry, and error mapping to a shared `AppException` type.
- **Real-time:** `socket_io_client` (matches the Flask-SocketIO backend in document 4) for chat messages, typing indicators, presence, and live audio room signaling.
- **Folder structure:** feature-first, not layer-first.

```
lib/
  app/
    app.dart                  // MaterialApp.router root
    router.dart                // go_router config, all routes from doc 2 §3
    theme/
      color_tokens.dart        // §2.1 of doc 2, light + dark ColorScheme
      type_tokens.dart         // §2.2, TextTheme + AppText widget (Devanagari auto-detect)
      spacing_tokens.dart
      motion_tokens.dart
      chat_theme_tokens.dart    // §2.7 of doc 2 — preset pack definitions, doodle overlay assets
  core/
    network/
      api_client.dart
      websocket_client.dart
    storage/
      secure_storage.dart      // tokens, biometric opt-in flags
      local_db.dart            // drift/sqflite for offline cache (matches, chat history, resolved chat themes)
    localization/
      app_localizations.dart   // Nepali + English, ARB-based
    permissions/
      permission_service.dart  // camera, mic, location, notifications
    media/
      camera_shell.dart        // shared CameraShell component, doc 2 §2.6
      compression_service.dart // client-side image/video compression for low-bandwidth, also used for custom wallpaper uploads
    notifications/
      push_service.dart        // FCM/OneSignal wrapper, category-aware (doc 2 screen 61)
  features/
    onboarding/                // screens 1–11
    profile/                   // screens 12–18
    discovery/                 // screens 19–27
    chat/                      // screens 28–36
    jhalak/                    // reels + stories + circles, screens 37–45
    saathi/                    // AI companion, screens 46–53
    safety/                    // screens 54–59
    settings/                  // screens 60–66
    personalization/           // chat theme & wallpaper system, screen 67 — new in this revision
  shared/
    widgets/                   // SwipeCard, ChatBubble, TypingIndicator, StoryRing,
                                // VerifiedBadge, ReelPlayerControls, AICharacterCard,
                                // CompatibilityMeter, NotificationPreferenceRow,
                                // ThemePickerSheet, WallpaperPreviewCard
    models/                    // shared freezed models used across ≥2 features
```

Each `features/<name>/` folder follows the same internal shape:
```
features/<name>/
  data/            // repositories, DTOs
  domain/          // freezed models, use-cases
  application/     // Riverpod providers/notifiers
  presentation/
    screens/       // one file per screen from doc 2
    widgets/       // feature-local widgets only
```

### 2. Key packages (pubspec.yaml)

| Purpose | Package |
|---|---|
| State | `flutter_riverpod`, `riverpod_annotation`, `riverpod_generator` |
| Routing | `go_router` |
| Models | `freezed`, `freezed_annotation`, `json_serializable`, `json_annotation` |
| Networking | `dio`, `socket_io_client` |
| Camera/media | `camera`, `video_player`, `video_compress`, `image_picker`, `record` (voice notes), `just_audio` (playback) |
| Local storage | `flutter_secure_storage`, `drift` (or `sqflite` if the team prefers less code-gen) |
| Push | `firebase_messaging` or `onesignal_flutter` (pick one — do not integrate both) |
| Location | `geolocator`, `geocoding` |
| Permissions | `permission_handler` |
| Localization | `flutter_localizations`, `intl` |
| Fonts | Local assets for Sora, Manrope, Noto Sans Devanagari (do **not** use `google_fonts` runtime-fetch — Nepal's network conditions make bundled fonts the right call) |
| Payments | `esewa_flutter_sdk` if available/maintained, else a `WebView`-based checkout via `webview_flutter` for eSewa/Khalti/Fonepay |
| Personalization | `flutter_colorpicker` (or equivalent) for the bubble-color and gradient pickers in `ThemePickerSheet`; `image_cropper` for the custom-wallpaper crop/fit step (doc 2 §2.7.2) |
| Utilities | `share_plus`, `cached_network_image`, `flutter_svg`, `shimmer` (loading states), `connectivity_plus` (low-bandwidth/offline detection) |

### 3. Theming implementation

- Build `AppColorScheme` (light) and `AppColorSchemeDark` from the tokens in document 2 §2.1 — map `marigold.500` → `ColorScheme.primary`, `dhaka.500` → `ColorScheme.secondary`, `pine.500` → a custom `ThemeExtension<MilanColors>` field (Flutter's base `ColorScheme` has no "tertiary success" slot that matches our intent — use a `ThemeExtension`).
- Build `AppText` as a widget wrapper, not a raw `Text` replacement everywhere — it inspects the string for Devanagari codepoints (`\u0900`–`\u097F`) and swaps `fontFamily` to Noto Sans Devanagari for that specific `TextSpan` run, so mixed Nepali/English sentences render both scripts correctly in one line.
- Implement dark mode fully, not as an afterthought — every screen in document 2 must look correct in both, and the app should default to system theme with a manual override in Settings (screen 63).
- Build a second, independent `ThemeExtension<ChatWallpaperTheme>` (wallpaper source, bubble colors, bubble shape, text scale, dark-mode brightness — doc 2 §2.7) that is resolved *per chat scope* rather than app-wide, since it must vary between the global default, an individual match's chat, and an individual Saathi character's chat simultaneously. Keep this fully separate from the app-wide light/dark `ColorScheme` — a user's wallpaper choice must not be coupled to their system theme choice beyond the dark-mode-brightness slider it explicitly exposes.

### 4. State management pattern per domain

Use `AsyncNotifier`/`Notifier` (Riverpod 2.x code-gen style) consistently:

- **`authProvider`** — phone/OTP flow, token storage, session state (`AsyncValue<Session?>`).
- **`profileProvider`** — current user's own profile, edit mutations optimistic-update then reconcile with server response.
- **`discoveryProvider`** — paginated candidate queue (`AsyncNotifier<List<CandidateProfile>>`), pre-fetches the next page when 3 cards remain in the local stack so swiping never blocks on network.
- **`matchesProvider` / `chatThreadProvider(matchId)`** — matches list is a `StreamNotifier` backed by the websocket client so new messages/matches arrive live; each open chat thread subscribes to its own room.
- **`presenceProvider`** — tracks online/typing state per user id, driven by socket events, consumed by `TypingIndicator` and `ChatBubble`.
- **`jhalakFeedProvider`** — cursor-paginated reel feed, prefetches next video's first frame while current one plays.
- **`saathiSessionProvider(characterId)`** — companion chat state; must include `lastProactiveMessageAt` and enforce the daily cap client-side as a UX safeguard in addition to the server-side enforcement in document 5.
- **`notificationPrefsProvider`** — per-category toggles (screen 61), syncs to backend, read by `push_service.dart` to locally suppress categories the user muted (defense in depth even though the server should also respect this).
- **`safetyProvider`** — report/block actions, scam-warning interstitial trigger state.
- **`themeProvider`** — new in this revision. `AsyncNotifier` holding the resolved `ChatWallpaperTheme` for a given scope key (`'global'`, `'match:<matchId>'`, or `'saathi:<characterId>'`). Resolution order: scoped override (if one exists in `local_db`/backend) → global default → hardcoded Milan factory default. Writes go through an optimistic local update (via `local_db`, so switching a theme is instant and works offline) followed by a sync call to `/api/v1/personalization/theme*` (document 4 §2/§3); if the sync fails, keep the local value and retry silently rather than reverting the user's choice mid-session.

### 5. Navigation graph

Route structure (go_router), grouped to mirror document 2:

```
/onboarding/language
/onboarding/phone
/onboarding/otp
/onboarding/basic-info
/onboarding/photos
/onboarding/video-intro
/onboarding/liveness
/onboarding/interview
/onboarding/location-primer
/onboarding/notification-primer

/profile/me
/profile/edit
/profile/prompts
/profile/bio-assistant
/profile/prompt-feedback
/profile/verification
/profile/privacy

/discover                         // screen 19, the app's default authenticated home
/discover/filters
/discover/mode
/discover/match/:matchId          // celebration → detail via query param `celebration=true`
/discover/kundali/:matchId
/discover/who-liked-you
/discover/boost

/chat                              // matches inbox
/chat/:matchId
/chat/:matchId/icebreakers
/chat/:matchId/voice-note
/chat/:matchId/snap-camera
/chat/:matchId/snap/:snapId
/chat/:matchId/share-date
/chat/:matchId/video-call
/chat/:matchId/voice-call
/chat/:matchId/theme               // ThemePickerSheet scoped to this match, doc 2 §2.7.4

/jhalak                            // reels feed, default tab alongside /discover
/jhalak/compose
/jhalak/duet/:reelId
/jhalak/stories
/jhalak/stories/:userId
/jhalak/stories/camera
/jhalak/circles
/jhalak/circles/:circleId
/jhalak/circles/:circleId/room

/saathi/intro
/saathi/characters
/saathi/characters/:characterId
/saathi/chat/:characterId
/saathi/chat/:characterId/voice
/saathi/chat/:characterId/theme    // ThemePickerSheet scoped to this Saathi character
/saathi/settings
/saathi/debrief/:matchId
/saathi/memory

/safety
/safety/report/:targetId
/safety/blocklist
/safety/panic
/safety/verification

/settings/notifications
/settings/account
/settings/language
/settings/payment-methods
/settings/subscription
/settings/help
/settings/chat-theme               // Chat Theme & Wallpaper Studio, screen 67, scoped to "all chats"
```

Root shell: a `StatefulShellRoute` (go_router's branch-based bottom nav) with 4 tabs — **Discover**, **Jhalak**, **Chat**, **Profile** — with a Saathi AI entry point surfaced as a floating action button or a 5th tab depending on final nav-bar real estate; do not bury Saathi more than one tap from any main tab.

### 6. Feature implementation notes

**Onboarding (screens 1–11):** The conversational interview screen (10) should render like a chat thread even though it's a structured data-collection flow underneath — each AI question is a `ChatBubble` (AI-labeled), each user answer is a normal bubble or an inline quick-reply chip set where the answer is categorical (e.g., relationship intent). Persist partial progress locally so a dropped connection doesn't restart the whole interview.

**Discovery (19–27):** `SwipeCard` must support a mixed media carousel (photos + video intro in one card, dot-indicator to page through), not just photos. Implement drag physics per document 2 §2.4. The Mode Switch (Serious/Casual, screen 21) changes the `discoveryProvider` query params and should visibly re-theme the swipe deck header (e.g., a small colored strip) so users always know which mode they're in. Kundali Mode (screen 24, formerly "Milan Mode") uses `CompatibilityMeter` alongside its own AI-generated narrative — keep it visually and structurally distinct from the "Why We Matched" screen (23) even though both use the same meter component, since one is a grounded compatibility explainer and the other is an explicitly cultural/fun signal (document 1 §4.1).

**Chat (28–36):** `ChatBubble` needs three visual variants: standard sent/received, AI-labeled (Saathi/icebreaker-suggested content), and ephemeral-snap (thumbnail with a timer ring, opens `Ephemeral Snap Viewer` on tap, single-view snaps show a "viewed" state and cannot be reopened). Read receipts and typing indicators run over the websocket, not polling. Every chat thread and Saathi chat screen renders its background and bubble colors from `themeProvider`'s resolved value for that scope (§4) — never a hardcoded color, since the whole point of the personalization system is that it's live-swappable without a rebuild.

**Jhalak (37–45):** Reel feed is a `PageView` with `scrollDirection: Axis.vertical`, one `VideoPlayerController` active at a time, next video pre-buffered. Duet recorder needs a split-screen `CameraShell` variant — original clip audio plays back while recording the new half. Live audio rooms (screen 45) use the same websocket connection with a WebRTC or Agora-style audio SDK layered on top (pick a maintained Flutter package at build time — do not build raw WebRTC signaling by hand for v1).

**Saathi AI (46–53):** This feature must visually and structurally telegraph "this is AI" everywhere — persistent header tag, AI-labeled `ChatBubble` variant, no photo-realistic human avatar (use the curated illustrated character art from doc 2's `AICharacterCard`, not a photoreal face — this is a deliberate product decision from document 1 §2.4/§4.2, not a placeholder-art gap to fill in later). The "What Saathi Remembers" screen (53) must render actual stored memory items from the backend (document 5 §2.3), not a static privacy-policy page — this is a real, per-item-deletable data view. Each curated character ships with a signature default entry from the Saathi wallpaper pack (doc 2 §2.7.2), applied the first time a user opens that character's chat, fully overridable via the theme entry point in the header menu.

**Safety (54–59):** Report flow (55) must be reachable in ≤2 taps from every profile, chat thread, and reel — put a report affordance in the app bar or overflow menu of each of those screen types, not only inside the Safety Center.

**Settings (60–66):** Payment methods (64) integrates eSewa/Khalti/Fonepay/ConnectIPS — implement via each provider's official SDK where available, WebView checkout as fallback; never store raw card/wallet credentials client-side, always tokenize server-side (document 4 §7).

**Personalization (67 — new):** The Chat Theme & Wallpaper Studio is one screen with four tabs (Presets / Solid & Gradient / Photo / Bubble Color) plus a persistent live-preview pane at the top showing two sample bubbles (one sent, one received) over the currently-selected wallpaper — every control change updates the preview immediately, before the user taps "Apply." When opened from a chat or Saathi entry point (§5), show a small scope indicator ("Applying to: this chat" vs. "Applying to: all chats") so the user always knows what they're about to change, with an explicit toggle to widen the scope to "all chats" if they want. Custom photo uploads go through `compression_service.dart` before both the local preview and the upload call, exactly like any other media upload (§8). Run the contrast check from document 2 §2.7.3 client-side before enabling "Apply," so a user gets immediate feedback rather than a server-side rejection.

### 7. Localization

- ARB files: `app_en.arb`, `app_ne.arb`. Every user-facing string goes through `AppLocalizations`, no hardcoded strings in widgets.
- Default to device locale; explicit override available in Settings (screen 63).
- Number/date formatting via `intl` with Nepali locale where it materially differs (e.g., BS calendar display as a secondary/optional date reference in profile birth-date fields, relevant to Kundali Mode's kundali flow).

### 8. Low-bandwidth handling

- All outgoing photos/videos pass through `compression_service.dart` before upload; target adaptive quality based on `connectivity_plus` network-type signal (more aggressive compression on 2G/3G). This includes custom chat-wallpaper uploads (§6).
- Reels and stories should default to a lower initial bitrate with a manual "watch in HD" toggle rather than always fetching max quality.
- Provide a global "Data Saver" toggle (Settings) that disables autoplay video in Jhalak and defaults chat media to tap-to-load; consider also defaulting custom-photo wallpapers to a lower-resolution cached copy for the live preview, fetching full resolution only once "Apply" is confirmed.

### 9. Testing expectations

- Widget tests for every shared component in `shared/widgets/`, including `ThemePickerSheet` and `WallpaperPreviewCard`.
- Provider unit tests for `discoveryProvider` pagination logic, `saathiSessionProvider` proactive-message capping logic, and `themeProvider`'s scope-resolution order (override → default → factory) specifically — these have the highest risk of silent behavioral bugs.
- Golden tests for `ChatBubble` and `SwipeCard` in both light and dark theme, and for `ChatBubble` across at least two different chat-wallpaper presets, to catch contrast/legibility regressions introduced by the personalization system.

### 10. Build checklist for the AI editor

Before considering a feature "done," confirm:
- [ ] Every screen from document 2 §3 has a corresponding route and screen file
- [ ] Dark mode implemented, not just light mode with a dark `ColorScheme` stub
- [ ] Every AI-generated or AI-suggested piece of UI is visually labeled as such
- [ ] No feature silently bypasses the notification frequency caps or the Saathi proactive-message cap
- [ ] All user-facing strings are localized, none hardcoded
- [ ] Report/block affordances present on profile, chat, and reel surfaces
- [ ] Chat and Saathi backgrounds/bubbles read from `themeProvider`, never a hardcoded color, and a theme change in one chat scope never leaks into another scope or into the other participant's view

Proceed to document 4 for the backend this app talks to, and document 5 for the exact request/response contracts the Saathi AI and matching-intelligence screens expect from the API.
