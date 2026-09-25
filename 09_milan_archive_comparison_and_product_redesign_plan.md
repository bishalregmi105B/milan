# Milan Archive Comparison and Product Redesign Plan

**Artifact status:** Decision and delivery-control document  
**Prepared:** 2026-09-25  
**Primary archive:** `Flutter Complete Dating App v1.1.9.rar`  
**Related project:** `/home/bishal-regmi/Desktop/Milan`  
**Scope:** Archive research, product comparison, UI/UX redesign, feature strategy, safety/privacy, implementation roadmap, and release-quality gates

> This document is the consolidated control plan for the Milan archive comparison. It is intentionally more authoritative than the older numbered build prompts: when two older documents conflict, this document records the decision that must be made before implementation. It does not modify application code.

---

## 1. Executive decision

The RAR is a feature-rich Firebase dating-app starter/template, not a production-ready application and not a safe technical foundation for Milan.

The correct decision is:

1. **Keep Milan’s current direction:** Nepal-first, safety-led, AI-native connection product with optional Saathi coaching.
2. **Borrow selected product concepts and interaction patterns from the archive**, especially Passport/travel discovery, remote configuration, rejected-profile recovery, privacy-controlled profile insights, and operational-console information architecture.
3. **Do not merge the archive as a product or Firebase foundation.** Reimplement useful ideas inside Milan’s Riverpod, GoRouter, Flask, server-authoritative, tokenized architecture.
4. **Stabilize the dating core before adding more companion, group, live-room, or theme innovation.**
5. **Treat “zero bugs” as a measurable release program:** zero known critical/high defects, zero privacy/safety leaks, zero dead primary controls, and zero unowned product claims. No software program can honestly guarantee that an undiscovered defect will never exist.

### Product positioning

> Milan is a culturally grounded connection product for adults who want meaningful real-world relationships, with optional AI coaching that helps them start conversations and build confidence without replacing human connection.

Milan should compete on:

- Trustworthy verification and safety
- Clear privacy controls
- Culturally relevant Nepal/diaspora experiences
- Conversation-to-date conversion
- Explainable recommendations
- Ethical, transparent AI assistance

Milan should not compete on:

- Swipe volume
- Fake activity or urgency
- Maximum AI session time
- Paid safety controls
- Unverified “premium = trusted” claims
- Unmoderated group or live-room launches

---

## 2. Research scope and evidence rules

### 2.1 Archive verification

The physical archive is:

`/home/bishal-regmi/Desktop/Milan/Flutter Complete Dating App v1.1.9.rar`

Verified properties:

| Property | Result |
|---|---|
| Format | RAR5, single volume, unencrypted, non-solid |
| Compressed size | 3,688,500 bytes |
| Uncompressed payload | 14,162,334 bytes |
| Contents | 414 files and 127 directories |
| Integrity | `unrar t` completed with `All OK` |
| SHA-256 before/after inspection | `388da12a0f97e17d67217f250d2c8e24a4948e8d84018a780680ffc044e0fd3c` |

For compact archive citations, this document uses:

```text
M = /Flutter Complete Dating App v1.1.9/codecanyon-29438891-flutter-complete-dating-app-for-android-ios-with-admin-panel
```

For example:

```text
M/Dating-App/lib/screens/passport_screen.dart:10
```

The archive was streamed for inspection and was not extracted into the repository. The archive itself must not be modified.

### 2.2 Evidence labels

- **Verified:** Directly observed in the archive or current Milan source.
- **Strong hypothesis:** The code pattern strongly indicates a failure, but the runtime path was not exercised.
- **Recommendation:** Proposed product or engineering direction.
- **External claim:** First-party competitor, vendor, or survey claim; not automatically neutral evidence.

### 2.3 Privacy rule

The archive contains tester contact information in documentation. This artifact intentionally does not reproduce names, emails, phone numbers, or other tester PII. Those materials must be handled as sensitive research data and must not be copied into source control.

---

## 3. Source-of-truth hierarchy

Milan currently contains several planning layers that do not always agree. The following hierarchy is mandatory:

1. **This document** — product decisions, release gates, and the approved redesign direction.
2. **Verified current implementation** — routes, endpoints, models, tests, and deployed behavior.
3. **Privacy, safety, terms, and regulatory requirements** — override marketing and feature ambition.
4. **Approved capability ledger** — status, evidence, owner, and acceptance test for each feature.
5. **Older documents 00–08** — historical context and prompts; no longer authoritative when they conflict with this document.
6. **Archive implementation** — reference material only; never a security or architecture authority.

### 3.1 Product-truth rule

No public claim may be published unless:

- The feature is reachable from a real user entry point.
- The primary action has a passing end-to-end test.
- Loading, empty, error, offline, blocked, expired, and unauthorized states are defined.
- The claim matches the actual implementation and privacy policy.
- The feature has an owner and a rollback or feature-flag path.

### 3.2 Saathi policy decision required

Earlier Milan documents describe Saathi as a non-romantic practice or coach, while later material introduces romantic or warm-companion language. Milan must choose one of these before public launch:

- **Option A — Practice-first:** Saathi is a conversation trainer, confidence coach, and safe practice partner; it is not a romantic substitute.
- **Option B — Clearly labeled warm companionship:** Saathi may provide warm companionship, but it must be persistently labeled as AI, disclose memory and limitations, prohibit dependency/guilt mechanics, and maintain clear boundaries.

**Recommended default:** Option A for the first release. Add Option B only after research, safety review, and explicit product approval.

---

## 4. Archive technical inventory

### 4.1 Archive structure and size

| Area | Approximate contents | Notes |
|---|---:|---|
| Mobile first-party Dart | 78 files / 10,798 lines | Main dating application |
| Mobile vendored plugins | 27 files / 3,319 lines | Old copies of swipe, OTP, carousel, geofire, and place-picker code |
| Mobile assets/localization | 60 files | 51 SVGs, 8 raster images, 1 English JSON file |
| Android project/data | 52 files | Includes approximately 10.38 MB of stale Gradle cache |
| iOS project/data | 56 files | App icons, generated configuration, Pod lock |
| Admin first-party Dart | 27 files / 3,233 lines | Flutter Web operations panel |
| Documentation | 74+ files | HTML documentation, screenshots, CSS/vendor files |
| Cloud Function | 1 file | Firebase callable push function only |
| Promotional files | 2 HTML redirects | Must not be opened or shipped |

The Gradle cache accounts for approximately 73% of the uncompressed payload. Nine `.DS_Store` files and generated Dart/iOS files are also included.

### 4.2 Archive architecture

The mobile app is a direct Firebase client:

- Firebase Phone Authentication
- Cloud Firestore
- Firebase Storage
- Firebase Cloud Messaging
- Firebase callable functions
- Google Maps and Places
- Google Mobile Ads
- In-app purchases
- Global `AppModel` and `UserModel` scoped state

Most business rules are implemented in the client. There is no trusted application server enforcing matching, blocking, premium entitlement, moderation, or account lifecycle rules.

### 4.3 Firestore data model

| Collection/path | Archive purpose | Milan implication |
|---|---|---|
| `AppInfo/settings` | Versions, store IDs, policy URLs, subscription IDs, radius limits, admin credentials | Must never contain secrets or admin credentials |
| `Users/{uid}` | Profile, exact geolocation, phone, email, gallery, device token, statistics | Requires field-level privacy and server authorization |
| `FlaggedUsers/{autoId}` | Report reason, target, reporter, timestamp | Use a moderation queue, not an immediate destructive flag |
| `Likes/{autoId}` | Directional like relationship | Store swipe state server-side |
| `Dislikes/{autoId}` | Directional rejection relationship | Support safe rewind without bypassing blocks |
| `Visits/{autoId}` | Unique profile-visit relationship | Use privacy-bucketed insights, not exact stalking data |
| `BlockedUsers/{autoId}` | Directional block relationship | Enforce centrally on every read/write path |
| `Notifications/{autoId}` | Like, visit, alert | Add message deep-link handling and privacy-safe previews |
| `Connections/{uid}/Matches/{peer}` | Match relationship | Use transactions and authoritative match state |
| `Connections/{uid}/Conversations/{peer}` | Last-message summary | Add pagination and deletion semantics |
| `Messages/{uid}/{peer}/{autoId}` | Text/image conversation copy | Avoid duplicating uncontrolled message copies |

### 4.4 Missing backend artifacts

The archive does not contain:

- `firebase_options.dart` for either Flutter project
- `google-services.json`
- `GoogleService-Info.plist`
- `firebase.json`
- Firestore rules
- Storage rules
- `firestore.indexes.json`
- Cloud Functions `package.json`
- API authorization layer
- Purchase receipt validation
- Moderation service
- Tests or CI

The database indexes appear only as screenshots in documentation and are not deployable configuration.

### 4.5 Screen and navigation map

#### Mobile entry flow

1. Splash — `M/Dating-App/lib/screens/splash_screen.dart:17`
2. Sign in — `M/Dating-App/lib/screens/sign_in_screen.dart:9`
3. Phone number — `M/Dating-App/lib/screens/phone_number_screen.dart:16`
4. OTP — `M/Dating-App/lib/screens/verification_code_screen.dart:12`
5. Registration — `M/Dating-App/lib/screens/sign_up_screen.dart:18`
6. Required location onboarding — `M/Dating-App/lib/screens/update_location_sceen.dart:14`
7. Blocked-account screen — `M/Dating-App/lib/screens/blocked_account_screen.dart:5`
8. Forced update — `M/Dating-App/lib/screens/update_app_screen.dart:9`

#### Home tabs

1. Discover — `M/Dating-App/lib/tabs/discover_tab.dart:21`
2. Matches — `M/Dating-App/lib/tabs/matches_tab.dart:15`
3. Chats — `M/Dating-App/lib/tabs/conversations_tab.dart:16`
4. Profile — `M/Dating-App/lib/tabs/profile_tab.dart:11`

#### Secondary screens

| Screen | Archive path |
|---|---|
| Public profile | `M/Dating-App/lib/screens/profile_screen.dart:20` |
| Edit profile | `M/Dating-App/lib/screens/edit_profile_screen.dart:12` |
| Likes | `M/Dating-App/lib/screens/profile_likes_screen.dart:19` |
| Visits | `M/Dating-App/lib/screens/profile_visits_screen.dart:18` |
| Disliked profiles | `M/Dating-App/lib/screens/disliked_profile_screen.dart:19` |
| Settings | `M/Dating-App/lib/screens/settings_screen.dart:14` |
| Passport | `M/Dating-App/lib/screens/passport_screen.dart:10` |
| Chat | `M/Dating-App/lib/screens/chat_screen.dart:25` |
| Notifications | `M/Dating-App/lib/screens/notifications_screen.dart:15` |
| Delete account | `M/Dating-App/lib/screens/delete_account_screen.dart:18` |
| About | `M/Dating-App/lib/screens/about_us_screen.dart:8` |

#### Admin navigation

The admin panel includes dashboard, users, flagged users, app settings, in-app purchase product IDs, broadcast push notifications, admin profile, and logout. It uses direct `Navigator` calls and has no route guard or server-issued admin session.

---

## 5. Archive UI/UX inventory

### 5.1 Visual system

The archive uses a simple pink theme:

- Primary: `Colors.pink`
- Accent: `Colors.pinkAccent`
- Background: white
- Secondary text: grey
- No dark theme
- No semantic token layers
- No custom font family
- Hardcoded sizes concentrated around 15–30px

The global theme is defined at `M/Dating-App/lib/main.dart:99-146`. The main card uses an asymmetric border with 28px and 8px corner radii at `M/Dating-App/lib/widgets/default_card_border.dart:5-13`.

This is visually recognizable but not a mature design system. It lacks:

- Semantic text hierarchy
- Contrast-safe color roles
- State tokens
- Responsive type scale
- Motion preferences
- Accessibility labels
- A shared web/mobile contract

### 5.2 Reusable component inventory

Useful concepts to study:

- Profile card and profile summary card
- Gallery card
- Profile statistics card
- User grid
- Chat bubble
- Circular action button
- Badge and unread counter
- Loading shimmer
- Empty-state view
- Primary button
- Image source/crop sheet
- Section card and section header
- SVG wrapper
- Store product and VIP card
- Admin statistics card
- Admin user-status badge
- Admin version stepper

Do not copy the underlying implementations without audit. Several use image-only gestures, raw `GestureDetector`, weak labels, or custom navigation patterns.

### 5.3 Motion and feedback

The archive uses:

- 200ms swipe animation
- 35-degree maximum card rotation
- 30%-of-width swipe threshold
- 6-unit card-stack translation
- 0.03 scale interval
- 300ms carousel transition
- 100ms progress-dialog animation
- LIKE/DISLIKE stamps
- Shimmer loading
- Hero transitions for chat images
- Default Material page transitions

It has no reduced-motion support. Milan’s existing reduced-motion and typed swipe work should be retained.

### 5.4 Archive feature ledger

| Feature | Archive status | Milan decision |
|---|---|---|
| Phone OTP | Implemented but broken on failure | Replace with server-authoritative generic OTP flow |
| Registration | Implemented | Rebuild with independent identity/intent fields |
| 18+ gate | Client-only | Enforce server-side on every path |
| GPS capture | Implemented | Reimplement with privacy and fallback states |
| Geohash discovery | Implemented | Use server-side discovery and reduced precision |
| Gender preference | Binary men/women/everyone | Replace with independent identity and attraction fields |
| Age range | Client-side filtering | Enforce server-side and explain hard constraints |
| Distance radius | Implemented | Keep with free/VIP rules and privacy controls |
| Swipe cards | Implemented but callback bug | Keep Milan’s typed swipe and fix state contract |
| Button swipes | Implemented | Reconnect button intent to actual command |
| Likes/dislikes | Implemented | Add server state, undo, and block enforcement |
| Match dialog | Implemented but racy | Use transactional persistence before success UI |
| Matches list | Implemented | Add pagination and honest activity state |
| Text chat | Implemented | Keep Milan’s richer chat architecture |
| Image chat | Implemented | Separate profile, chat, Jhalak, and payment media |
| Delivery state | Missing | Add sending, sent, delivered, failed, retry states |
| Likes/visits | Premium-gated | Add privacy-bucketed Milan Pulse |
| Disliked profiles | Implemented with reversal bug | Reimplement server-backed passed/rewind flow |
| Hide profile | Implemented | Add granular visibility controls |
| Profile gallery | Implemented | Build full media manager with ordering/deletion/moderation |
| Passport | Implemented | Adapt as expiring Milan Passport |
| Notifications | Partial | Fix message deep links and discreet previews |
| VIP purchases | Partial and insecure | Replace with server-authoritative entitlements |
| Restore purchases | Partial | Add provider receipt/server validation |
| Verification | Purchase-derived and misleading | Separate payment tier from identity verification |
| Report/block | Partial/client-side | Centralize server enforcement and evidence |
| Account deletion | Partial and unsafe | Server-mediated deletion/export job |
| Social login | Not implemented | Do not expose unused UI |
| Voice/video calls | Not implemented | Hide until real transport is integrated |
| Automated moderation | Not implemented | Keep Milan’s server moderation and media scanning |
| Localization scaffolding | English only | Use Milan’s Nepali/English foundation and close coverage gaps |
| Admin dashboard | Implemented | Rebuild with RBAC, MFA, audit logs, and moderation queue |
| Tests/CI | None | Add complete quality gates |

---

## 6. Archive findings: adapt, reimplement, reject

### 6.1 Adapt as product concepts

#### Milan Passport

The archive’s strongest distinctive idea is Passport: temporarily browse another city or country. Milan should support:

```text
home_location
current_location
active_discovery_location
passport_enabled
passport_started_at
passport_expires_at
passport_visibility
```

Requirements:

- Never overwrite the user’s real home coordinates.
- Show a persistent “Browsing from [location]” state.
- Provide Return Home.
- Expire automatically.
- Use reduced-precision coordinates.
- Explain whether the visit location is visible to matches.
- Continue enforcing blocks, reports, and regional safety rules.
- Research Gulf, Malaysia, Europe, and return-home journeys before launch.

#### Remote configuration and minimum-build service

Adapt the archive’s remote version/configuration concept into a signed, cached Milan backend service for:

- Minimum supported app version
- Feature availability
- Support links
- Emergency notices
- Policy versions
- Store identifiers
- Safe feature flags

Never put secrets or admin credentials in the same configuration document.

#### Passed profiles and rewind

Use the archive’s rejected-profile information architecture, but implement it server-side:

- Record every swipe direction and timestamp.
- Allow a short undo window.
- Deactivate an accidental match when rewound.
- Never allow rewind to bypass blocks, reports, or moderation.
- Make “Previously passed” optional and privacy-controlled.

#### Profile insights

Adapt the Likes/Visits concept into Milan Pulse:

- Likes received
- Unique profile viewers
- Recent match activity
- Delayed/bucketed reveals
- No exact visit timeline by default
- No public rankings
- No pressure-oriented counters

#### Authenticated operations console

The archive’s admin information architecture is useful, but it must be rebuilt with:

- Server-issued admin sessions
- MFA for privileged actions
- Server-side RBAC
- Immutable audit history
- Moderation queue
- Paginated server queries
- No browser-side password comparison
- No unrestricted direct Firestore writes

### 6.2 Reimplement safely

Do not copy these features directly even if the archive has a UI:

- Location permission and discovery
- Profile galleries
- Report and block actions
- Account deletion and export
- Premium purchase and restore
- Push broadcast operations
- App version gates
- Profile statistics
- Hide-profile behavior
- Chat deletion/unmatch semantics

Each must be backed by a server-authoritative API, explicit privacy state, error recovery, and an E2E test.

### 6.3 Reject outright

Do not copy:

- Global Firestore read/write rules
- Plaintext client-side admin credentials
- Unauthenticated callable push functions
- Client-side purchase trust
- Purchase-as-verification logic
- Custom OTP implementation
- Custom swipe stack implementation
- Direct `Navigator` navigation architecture
- Hardcoded pink/grey visual tokens
- Vendored stale OTP/swipe/carousel/place-picker code
- Generated caches and developer-specific paths
- Promotional redirect files
- Client-only account deletion orchestration
- Self-reported or client-only safety state

---

## 7. Archive defects and security findings

### P0 — deployment blockers

#### 7.1 Global Firestore access

`M/Documentation-README-FIRST/index.html:647-682` instructs operators to use:

```text
match /{document=**} {
  allow read, write;
}
```

This would expose or permit modification of coordinates, phone numbers, email, birth dates, galleries, messages, device tokens, likes, blocks, matches, configuration, and admin credentials.

**Required Milan response:** Never deploy client-owned business rules as the security boundary. All sensitive operations must be authorized by Milan’s backend.

#### 7.2 Plaintext admin credentials

Archive paths:

- `M/Web-Admin-Panel/lib/models/app_model.dart:29-45`
- `M/Web-Admin-Panel/lib/datas/app_info.dart:16-18,38-52`
- `M/Documentation-README-FIRST/index.html:1239-1258`

The same settings document is readable by the mobile app, so field-level separation is impossible.

**Required Milan response:** Remove credentials from client configuration. Use backend sessions, password hashing or SSO, MFA, RBAC, and audit logs.

#### 7.3 Unauthenticated push callable

`M/Cloud Functions/index.js:6-60` does not check `context.auth`, App Check, role, or input ownership. A caller could send arbitrary push text to arbitrary tokens or broadcast to all users.

**Required Milan response:** Trigger notifications from trusted server-side domain events only. Require admin role, audience preview, quiet hours, rate limits, localization, and delivery audit.

#### 7.4 Debug signing for release

`M/Dating-App/android/app/build.gradle:59-75` uses the debug signing configuration for release.

**Required Milan response:** Use a protected release keystore, CI signing, key rotation process, and separate debug/release configuration.

#### 7.5 Missing Firebase resources

Missing:

- `Dating-App/lib/firebase_options.dart`
- `Web-Admin-Panel/lib/firebase_options.dart`
- `Dating-App/android/app/google-services.json`
- `Dating-App/ios/Runner/GoogleService-Info.plist`

The documentation incorrectly says these can be skipped at `M/Documentation-README-FIRST/index.html:532-538`.

**Required Milan response:** Add a reproducible environment setup check that fails before build when required configuration is absent.

#### 7.6 Developer-specific generated paths

Examples:

- `M/Dating-App/android/local.properties:1-5`
- `M/Dating-App/ios/Flutter/Generated.xcconfig:2-4`
- `M/Dating-App/ios/Flutter/flutter_export_environment.sh:3-4`

**Required Milan response:** Clean generated artifacts from source packages and regenerate them in CI or local setup.

### P1 — major functional and privacy defects

- OTP failure can falsely report success: `M/Dating-App/lib/screens/verification_code_screen.dart:41-70`.
- Swipe callbacks can act on the previous profile: `M/Dating-App/lib/plugins/swipe_stack/swipe_stack.dart:150-155` and `M/Dating-App/lib/tabs/discover_tab.dart:96-133`.
- Profile cards can show the logged-in user’s age: `M/Dating-App/lib/widgets/profile_card.dart:40-44`.
- Re-liking from Disliked has unreachable logic: `M/Dating-App/lib/screens/profile_screen.dart:337-355`.
- Several Firestore error handlers return an exception as query data: `M/Dating-App/lib/api/blocked_users_api.dart:29-33,66-71,99-104` and related API files.
- Message push taps are not handled: `M/Dating-App/lib/screens/chat_screen.dart:257-265` and `M/Dating-App/lib/helpers/app_notifications.dart:21-59`.
- Purchase sets `user_is_verified = true`: `M/Dating-App/lib/screens/home_screen.dart:88-100`.
- Purchase entitlement is trusted on-device: `M/Dating-App/lib/widgets/store_products.dart:39-63`, `M/Dating-App/lib/screens/home_screen.dart:77-155`, and `M/Dating-App/lib/helpers/app_helper.dart:21-31`.
- Account deletion is non-atomic and incomplete: `M/Dating-App/lib/screens/delete_account_screen.dart:55-100,142-151`.
- Image replacement deletes the old image before replacement succeeds: `M/Dating-App/lib/models/user_model.dart:615-638`.
- Block/report rules are not server-enforced: `M/Dating-App/lib/models/user_model.dart:438-450`.
- Custom report reasons can be accepted without validation: `M/Dating-App/lib/dialogs/flag_user_dialog.dart:115-170`.
- Match persistence returns before the write completes: `M/Dating-App/lib/api/matches_api.dart:54-85`.
- Admin updates can report success before persistence: `M/Web-Admin-Panel/lib/models/app_model.dart:67-78`.

### P2 — accessibility, performance, and maintainability

- No meaningful `Semantics`, screen-reader state, or tooltip coverage.
- Custom OTP keypad blocks paste/autofill.
- Swipe/rewind controls can be smaller than 48 logical pixels.
- Carousel dots have approximately 8px hit regions.
- No reduced-motion support.
- Pink/grey combinations fail normal-text contrast.
- Exact birth dates, exact coordinates, phone numbers, and messages are exposed in the data model.
- No media/message moderation.
- No age assurance beyond a client check.
- No pagination for discovery, messages, notifications, or conversations.
- Chat reverses the entire message list inside each item builder, producing quadratic work.
- `FutureBuilder` creates new futures during rebuilds.
- Map search issues stale reverse-geocode and nearby requests.
- Gradle cache, `.DS_Store`, generated files, unused SVGs, and promotional redirects are shipped.
- Version labels drift between archive/docs and app metadata.

---

## 8. Current Milan capability ledger

### 8.1 Substantially implemented

- OTP/email authentication path
- Google authentication path
- Profile CRUD
- Liveness upload
- Candidate discovery and matching backend
- Swiping/matching models
- Chat persistence
- Socket.IO/presence
- Notification preferences
- Role-gated admin pages
- Manual QR payments
- Chat-theme CRUD
- Companion language mirroring
- Context compaction
- Persona bibles
- Simulated schedules
- Initiative/proactive messaging infrastructure
- Memory/status/quest/capsule/recap APIs
- Jhalak snap persistence and composer
- Nepali/English localization foundations
- Per-chat theme architecture with contrast concepts

### 8.2 Partial, orphaned, or static

- Most of the 67-screen inventory
- Calls
- Jhalak stories/camera/viewer
- Circles and live rooms
- Privacy/account lifecycle
- Global Theme Studio
- Rewind UI
- Location capture
- Complete profile ordering
- Server-side interview storage
- Full localization
- Production APK
- CDN/compression/purge
- Load testing
- Prompt-injection/media-safety testing
- Real payment providers
- Saathi voice/debrief/recap UI
- Notification actions
- Support and broadcast operations

### 8.3 Current Milan release blockers

| Area | Evidence | Status |
|---|---|---|
| Production config | `backend/app/__init__.py:12-15`; `backend/app/config.py:128-151` | Critical |
| OTP enumeration/logging | `backend/app/blueprints/auth/__init__.py:42-60`; `backend/app/utils/otp.py:73-99` | Critical |
| Google age path | `backend/app/blueprints/auth/__init__.py:146-171` | Critical |
| Swipe intent | `mobile/lib/shared/widgets/swipe_card.dart:11-23,97-105` | Critical UX |
| Private photo response | `backend/app/blueprints/profile/__init__.py:397-418` | High |
| Blocked match access | `backend/app/blueprints/safety/__init__.py:56-62`; `backend/app/blueprints/chat/__init__.py:17-35` | High |
| View-once replay | `backend/app/blueprints/jhalak/__init__.py:103-136` | High |
| Media URL moderation | `backend/app/services/moderation_service.py:84-114` | High |
| Media fetch/SSRF | `backend/app/services/media_service.py:76-95` | High |
| Audio room authorization | `backend/app/sockets/audio_room_events.py:5-32` | High |
| Voice metadata | `mobile/lib/features/chat/presentation/screens/chat_extra_screens.dart:53-65` | High |
| Theme Studio | `mobile/lib/app/router.dart:222-223`; `chat_theme_studio_screen.dart:47-114` | High |
| Chat text scale | `chat_thread_screen.dart:293-295`; `chat_bubble.dart:89-96` | High |
| Language persistence | `onboarding_screens.dart:91-115` | High |
| Location capture | `onboarding_screens.dart:597-645` | High |
| Report target ID | `chat_thread_screen.dart:247-252`; `safety/__init__.py:16-24` | High |
| Account export/delete | `settings_screens.dart:192-228` | High |
| Calls/Jhalak/Saathi shells | `jhalak_extra_screens.dart:51-221`; `chat_extra_screens.dart:285-340`; `saathi_extra_screens.dart:287-443` | High |
| Snap double-pop | `snap_composer_screens.dart:42-63` | High |
| APK link | `web/src/app/(site)/page.tsx:42-47,471-477`; `download-client.tsx:22-28` | High |
| Admin payment JSON | `web/src/lib/admin-api.ts:203-212,368-389` | High |
| Recap route | `backend/app/blueprints/saathi/__init__.py:1269-1310`; no Next route | High |
| Discovery contract | `discovery_provider.dart:48-74`; `backend/app/blueprints/discovery/__init__.py:30-57` | Medium/High |
| AI inclusion setting | `profile/__init__.py:116-118`; discovery hard-filter at `discovery/__init__.py:46-52,239-245` | Medium |
| Match explainer context | `backend/app/services/matching_service.py:309-333` | Strong hypothesis |
| Top Picks rerank | `backend/app/tasks/matching_tasks.py:13-25` | High |
| Interview persistence | `models/user.py:109-112`; `profile/__init__.py:235-278` | High |
| Memory deletion completeness | `saathi/__init__.py:526-548`; `context_engine.py:121-152`; `companion_prompt.py:226-232` | High |
| Ephemeral purge | `backend/app/extensions.py:40-97`; `tasks/media_tasks.py:9-26` | High |
| Test safety stubs | `backend/tests/conftest.py:27-38` | High release risk |

### 8.4 Current web quality gap

`web/package.json:4-9` defines `dev`, `build`, `start`, and `lint`, but no test script. There is no visible component or browser E2E test command in the project manifest.

### 8.5 Current backend test gap

`backend/tests/conftest.py:27-38` globally replaces moderation, prompt-injection, scam classification, match explanation, and proactive generation with fixed results. This is useful for unit isolation but unsafe as the only test environment for safety behavior.

The suite must be split into:

- Pure unit tests
- Integration tests against real persistence
- Contract tests for authorization and media
- Adversarial safety tests
- Browser/mobile E2E tests
- Staged external-provider tests

### 8.6 Current mobile test gap

Existing tests cover selected theme and realtime behaviors, including:

- `mobile/test/theme_provider_test.dart`
- `mobile/test/realtime_chat_test.dart`
- `mobile/test/chat_theme_test.dart`
- `mobile/test/email_auth_flow_test.dart`

The primary journey still needs tests for:

- Onboarding and age policy
- Location and Passport
- Swipe intent
- Profile media
- Report/block
- Voice/media round trips
- Account export/delete
- Calls/Share Date visibility
- Saathi memory and pause controls
- Accessibility and localization

---

## 9. Competitive and market lessons

### 9.1 BiheNepal and Veya feedback context

The Veya Feedback archive is beta feedback, not a competitor binary or product specification. It identifies **BiheNepal Blind Date** as a named comparator and reports the following themes:

- Interest, hobby, personality, lifestyle, and genuine compatibility
- Onboarding friction around multiple photo uploads and birth-date resets
- Daily dislike caps and seven-hour lockouts
- Camera/gallery confusion
- Non-binary identity representation
- Approximate or ghost location instead of exact location
- Anonymous alias, bounded text session, mutual reveal, and optional continuation
- Layered photo privacy
- Swipe-deck persistence and card interaction issues
- Dummy profiles and lack of real users during beta
- Broken access links and incomplete platform availability

BiheNepal’s public strengths are cultural specificity, serious-intent positioning, multiple modes, verification claims, and privacy controls. Its weaknesses include trust inconsistencies, payment/value problems, suspicious or repetitive profiles, broken Blind Date behavior, unclear age rules, and weak support response.

Milan opportunity:

- Clear and consistent privacy claims
- Server-verified trust states
- Better report/block resolution
- No paywalled safety controls
- Transparent activity and queue behavior
- Culturally specific experience without opaque ranking or fake urgency

### 9.2 External product research

- Hinge emphasizes fewer, better matches, relationship intent, prompt feedback, tailored conversation starters, Match Notes, and attention to existing conversations: [Hinge Dating Forward](https://hinge.co/newsroom/dating-forward) and [Hinge product evolution](https://hinge.co/newsroom/hinge-2025-product-evolution).
- Bumble emphasizes curated daily profiles, intent and interest badges, Opening Moves, ID verification, Share Date, in-app calls, sensitive-image protection, and Review Before Send: [Bumble features](https://bumble.com/the-buzz/bumble-dating-features) and [Bumble safety](https://bumble.com/en-us/the-buzz/safety).
- Romance scams increasingly use AI, move users off-platform, refuse meetings, and request money, gifts, cryptocurrency, or irreversible transfers: [FTC 2025](https://consumer.ftc.gov/consumer-alerts/2025/02/looking-love-watch-out-scammers) and [FTC 2026](https://consumer.ftc.gov/consumer-alerts/2026/02/why-cant-new-love-interest-meet-person).
- Hinge’s LGBTQ research highlights label fatigue and the need for independent identity, attraction, and communication preferences: [Hinge LGBTQ report](https://hinge.co/newsroom/2025-LGBTQ-Report).
- AI companion retention and safety require caution. Relevant sources include [Common Sense Media](https://www.commonsensemedia.org/research/talk-trust-and-trade-offs-how-and-why-teens-use-ai-companions), the [FTC companion inquiry](https://www.ftc.gov/news-events/news/press-releases/2025/09/ftc-launches-inquiry-ai-chatbots-acting-companions), [RevenueCat](https://www.revenuecat.com/state-of-subscription-apps/), and this [academic preprint](https://arxiv.org/abs/2503.17473).
- EU AI-content transparency and DSA guidance create additional requirements for disclosure, non-profiling options, privacy-preserving age assurance, moderation reasons, and non-deceptive design: [EU AI Act](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) and [DSA guidance](https://digital-strategy.ec.europa.eu/en/policies/dsa-impact-platforms).

---

## 10. Product positioning and target segments

### 10.1 Primary segments

Research and product design must distinguish:

1. Serious relationship seekers
2. Marriage-oriented users
3. Friendship and local community seekers
4. Diaspora users temporarily in another country
5. Users who want Saathi practice or confidence coaching
6. Privacy-conscious and discreet-mode users
7. Low-bandwidth and older-device users

Do not assume one onboarding flow or one intent model fits all segments.

### 10.2 Product principles

- Real users are clearly identified.
- AI is clearly identified.
- Privacy is layered and user-controlled.
- Users control memory, visibility, pace, and attention.
- Safety features are never paywalled.
- No fake scarcity, fake match counts, guilt, jealousy, or urgency.
- Blocked users lose all access to the blocker’s data and media.
- Every recommendation explains why it exists.
- Every sensitive field has a deletion path.
- Every static shell is completed or removed.
- No feature is advertised before it passes an end-to-end acceptance test.

---

## 11. End-to-end journey blueprints

### 11.1 Onboarding and eligibility

Target initial path: approximately 60–90 seconds.

Ask only what is needed for a useful first recommendation:

1. What brings you here?
   - Serious relationship
   - New friends
   - Local community
   - Saathi practice
2. Age eligibility
3. Identity and pronouns
4. Who the user wants to meet
5. Three interests or values
6. Privacy preference
7. Optional profile media
8. Optional voice introduction

Ask sensitive ethnicity, caste, religion, and family expectations later, optionally, and mutually.

Do not:

- Force binary gender
- Require exact location
- Require three photos before showing value
- Fabricate a date of birth
- Reset birth date or profile state unexpectedly
- Hide a skip/back path for optional questions

### 11.2 Home, current location, and Passport

The home surface should show:

- Current discovery location
- Home location
- Passport state
- Return-home action
- Expiry date
- Privacy explanation
- Offline/error state

Recommended data model:

```text
home_location
current_location
active_discovery_location
passport_enabled
passport_started_at
passport_expires_at
passport_visibility
```

Location permission must be optional, explain the benefit before requesting it, and support approximate/ghost location.

### 11.3 Profile and media manager

Profile media must be separated by context:

- Profile photo
- Additional gallery photos
- Chat media
- Jhalak media
- Payment evidence
- Wallpaper/theme assets

The generic `kind=photo` upload currently creates a profile `Photo` row at `backend/app/blueprints/media/__init__.py:31-39`. This must be corrected before adding more upload surfaces.

Profile manager requirements:

- Camera and gallery capture
- Crop and reorder
- Primary photo
- Approved/moderation state
- Delete and replace safely
- Blur/privacy layers
- Accessibility descriptions
- Low-bandwidth placeholders
- No accidental payment or chat media in the profile gallery

### 11.4 Discovery and recommendations

Replace an endless deck with four to six explainable daily recommendations.

Each card should include:

- Primary photo preview
- Age band
- Broad location
- Two grounded shared reasons
- One uncertainty to discuss
- Availability
- One or two prompts
- Privacy state
- Clear action controls

Actions:

- Interested
- Pass
- Maybe later
- Report
- Hide

Separate:

- Hard dealbreakers
- Ranking signals
- Optional curiosity signals

Do not claim personality facts that have not been established.

### 11.5 Match and first conversation

A match should create a safe, low-pressure beginning:

- Shared prompt
- Optional voice note
- Suggested opener
- Human/AI identity labels
- Report/block always visible
- No auto-send
- Clear “send message” and “keep exploring” actions
- Match persistence completed transactionally before success UI

### 11.6 Chat

Support a defined media contract:

- Text
- Image
- Voice
- Optional Jhalak snap
- Optional call only after real transport exists

Every message needs:

- Sending
- Sent
- Delivered
- Failed
- Retry
- Moderation blocked
- Withdrawn/deleted

Voice notes must send `media_type: audio`. Images must not be inferred from a missing or incorrect media type.

### 11.7 Safety, report, block, and moderation

Report/block must work from:

- Profile
- Discovery
- Match
- Chat
- Search
- Jhalak
- Group/Circle

The server must resolve the correct target and enforce:

- Block direction
- Account status
- Match activity
- Media access
- Notification suppression
- Conversation access
- Report evidence

The current chat report path passes a match ID where the backend expects a user ID at `mobile/lib/features/chat/presentation/screens/chat_thread_screen.dart:247-252` and `backend/app/blueprints/safety/__init__.py:16-24`.

### 11.8 Privacy and data lifecycle

Required controls:

- Layered photo visibility
- Hidden full name option
- Age band option
- Approximate location
- Discreet notifications
- App lock
- Memory viewer
- Memory editor
- Memory deletion
- Data export
- Account deletion
- Session/device management
- Consent history

Deletion must be server-mediated, auditable, recoverable during a defined grace period where appropriate, and followed by durable media cleanup.

### 11.9 Payment and entitlement

Use one canonical tier matrix across:

- Mobile UI
- Web pricing
- Backend entitlement API
- App Store/Play Store validation
- Refund/revoke handling
- Restore purchase
- Admin operations

Never equate payment with identity verification.

### 11.10 Saathi

Recommended first-release scope: practice-first Saathi.

Inside every Saathi thread:

- Persistent AI label
- Practice scope explanation
- Memory view/edit/delete
- Pause
- Quiet hours
- Session-time visibility
- Proactive-message controls
- Voice status
- Draft approval
- No guilt, jealousy, exclusivity, or manipulative urgency

A later Match Bridge can connect Saathi practice to a real conversation or date, but the user must initiate the transition.

### 11.11 Circles and group discussion

Start with asynchronous, moderated topic circles:

- Clear rules
- Host/moderator controls
- Report/block
- No pressure to move to direct messages
- Optional anonymous participation
- Private invitations
- Clear human versus AI content labeling

Do not launch live audio until membership authorization, signaling, moderation, reporting, and emergency behavior are real.

---

## 12. UI/UX redesign system

### 12.1 Intent

**Human:** An adult Nepalese or diaspora user opening Milan after work or late at night, curious about dating but unsure how to begin, concerned about privacy and authenticity, and wanting a calm first step rather than an endless feed.

**Primary verb:** Choose, understand, and begin safely.

**Feeling:** Calm, hopeful, transparent, culturally grounded, and quietly intelligent.

### 12.2 Domain exploration

Domain concepts:

- First hello
- Mutual curiosity
- Safe closeness
- Consent
- Shared attention
- Repair after awkwardness
- Small rituals
- Belonging
- Boundaries
- Memory with user control
- Becoming comfortable before meeting

### 12.3 Color world

The palette should come from the product’s physical and emotional world:

- White paper and open space
- Pale morning sky
- Clear blue horizon
- Deep water
- Sea glass
- Ink and handwriting
- Warm dawn for emotional emphasis
- Pine green for trusted states
- Amber for caution
- Red for danger

### 12.4 Signature: the Trust Thread

A thin sky-blue line connects:

1. Profile
2. Shared value
3. Shared prompt
4. Safety state
5. First conversation
6. Date or next step

It should appear in match cards, match confirmation, chat headers, Blind First, Circles, and Saathi milestones. It should animate only when the user advances a meaningful state.

### 12.5 Defaults to reject

- Generic pink/red romance gradients → white and sky blue with one controlled warm connection accent
- Endless swipe decks → small, explainable daily recommendations
- Blank AI chat → visible conversation runway with memory and boundary controls
- All-or-nothing photo blur → layered privacy with separate controls
- Unverified badges → plain-language trust states with evidence
- Fake activity and urgency → honest queue and response expectations

### 12.6 Default Milan Sky palette

```css
:root {
  --milan-canvas: #FFFFFF;
  --milan-sky-surface: #F0F9FF;
  --milan-sky-soft: #E0F2FE;
  --milan-surface-raised: #FFFFFF;
  --milan-surface-inset: #F8FBFE;

  --milan-sky: #38BDF8;
  --milan-action: #0369A1;
  --milan-action-hover: #075985;

  --milan-ink: #0B1520;
  --milan-ink-secondary: #38546B;
  --milan-ink-tertiary: #64748B;

  --milan-border: #CBD5E1;
  --milan-border-subtle: #E2E8F0;
  --milan-focus: #0369A1;
}
```

Contrast rules:

- White text on `#38BDF8` is not suitable for normal text.
- White on `#0369A1` is suitable for normal text after contrast testing.
- `#0B1520` on `#38BDF8` is readable.
- Bright sky is for fills, selection, progress, and decorative states.
- Deep sky is for text-bearing buttons and links.
- Custom themes derive `onAccent`, focus, muted, and border colors automatically.

Keep semantic colors fixed:

- Trusted/verified
- Warning
- Danger
- Blocked
- Scam warning
- System status

A user may customize the emotional accent, but not the meaning of trust or danger.

### 12.7 Cross-platform token contract

Create a versioned `design-tokens.json` source consumed by:

- Web CSS variables
- Flutter `ColorScheme` and `ThemeExtension`
- Backend theme validation
- Visual regression fixtures
- Documentation and screenshots

Suggested contract:

```json
{
  "version": 1,
  "mode": "light",
  "accent": "#38BDF8",
  "surface": "sky",
  "contrast": "AA",
  "textScale": 1,
  "density": "comfortable",
  "motion": "full",
  "radius": "soft"
}
```

The server validates ranges and derives semantic colors. The client never accepts arbitrary CSS.

### 12.8 Theme Studio

The existing Theme Studio is a P0/P1 gap because the route is missing and controls are no-ops.

Required experience:

- Preset gallery
- Milan Sky default
- Cloud High Contrast preset
- Optional dark preset
- Accent color picker
- Surface warmth selector
- Text-size preview
- Motion toggle
- Density toggle
- Contrast warning
- Live preview across profile, match, chat, and settings
- Reset to default
- Offline local save
- Account sync when online
- Global/per-chat/saathi scope isolation
- Pending-moderation state for user-uploaded assets
- No override of safety semantics

### 12.9 Component standards

Every component must define:

- Default
- Hover
- Pressed
- Focus-visible
- Disabled
- Loading
- Empty
- Error
- Offline
- Unauthorized
- Expired
- Reduced-motion behavior

Primary components:

- App shell and bottom navigation
- Profile card
- Profile media manager
- Match card
- Recommendation explanation
- Prompt chip
- Trust badge
- Report/block sheet
- Chat bubble and composer
- Voice-note player
- Jhalak snap viewer
- Theme Studio controls
- Date/availability selector
- Group/Circle card
- Admin data table
- Audit-log viewer

### 12.10 Accessibility and motion

- 44px minimum web touch targets; 48px preferred mobile targets
- 4.5:1 normal-text contrast
- Visible focus rings
- Semantic labels for icon-only actions
- Screen-reader announcements for match, message, and safety states
- OS text-scale inheritance
- Reduced-motion support
- Non-gesture alternatives for swipe actions
- Large hit areas for rewind, carousel, and theme controls
- No color-only status meaning
- Localized dates, currencies, and legal copy
- Low-bandwidth image and voice fallbacks

---

## 13. Differentiated innovations

### 13.1 Milan Passport

A privacy-safe, expiring travel discovery mode for diaspora and temporary relocation.

### 13.2 Explainable daily recommendations

Show two grounded shared reasons and one uncertainty. Let users tune more/less without exposing private ranking signals.

### 13.3 Blind First

A verified, bounded, anonymous first conversation:

- Temporary alias/avatar
- Shared prompt
- 15–20 minute session
- Skip, pause, and end controls
- Mutual reveal
- Coarse presence only
- No payment/contact requests
- Inherited report/block and safety shortcuts

### 13.4 Saathi Match Bridge

A user-initiated transition from AI practice to a real conversation or date:

- Practice an opener
- Review a draft
- Send only with approval
- Debrief after a date
- Gradually reduce companion reliance

### 13.5 Visible memory

Users can see, edit, pause, export, or delete what Saathi remembers. The memory screen must be reachable from the active companion thread.

### 13.6 Milan Pulse

A restrained activity surface:

- New matches
- People you liked
- Recoverable passes
- Bucketed profile interest
- No exact stalking timeline
- No public rankings

### 13.7 Asynchronous Circles

Topic-based group discussion before live rooms:

- Shared interests
- Moderated hosts
- Privacy controls
- Human/AI labels
- No pressure to move to DMs

### 13.8 Remote minimum-build and emergency configuration

A signed, cached configuration service can provide:

- Minimum supported build
- Feature flags
- Policy updates
- Support links
- Emergency notices
- Safe deprecation of unsafe routes

---

## 14. Prioritized gap matrix

| Priority | Domain | Current state | Required outcome |
|---|---|---|---|
| P0 | Product truth | Plans and public copy conflict | One approved Saathi policy and capability ledger |
| P0 | Secrets/config | Production secret guard and local artifacts are unsafe | Rotate secrets and fail closed |
| P0 | Auth/age | OTP and Google paths can bypass age/eligibility | Generic, rate-limited, age-enforced auth |
| P0 | Block/privacy | Blocked matches and private media remain accessible | Server-enforced access policy |
| P0 | Media | View-once, moderation, and media fetch paths are unsafe | Atomic media lifecycle and scanning |
| P0 | Core UX | Swipe, voice, report, and location flows are broken | Complete primary loop |
| P0 | Route truth | Static and orphan routes are exposed | Route manifest or removal |
| P0 | Data rights | Export/delete/memory deletion incomplete | Server lifecycle and durable cleanup |
| P0 | Release artifacts | APK missing, admin payment broken | Real signed build and working billing boundary |
| P1 | Dating core | GPS, galleries, filters, and recovery are incomplete | Complete profile/discovery/match journey |
| P1 | Chat | Media contract and delivery states incomplete | Contract-tested text/image/voice chat |
| P1 | Saathi | Strong backend, weak user control and truth | Practice-first control center |
| P1 | Themes | Global Studio absent, tokens diverge | Shared theme contract and real editor |
| P1 | Accessibility | Selected checks only | Full mobile/web acceptance coverage |
| P1 | Localization | Foundations exist, coverage is incomplete | Primary journeys localized and tested |
| P1 | Operations | Admin capabilities are incomplete | RBAC, MFA, audit, moderation queue |
| P2 | Passport | Not implemented | Research and launch privacy-safe Passport |
| P2 | Retention | Many loops disconnected | Honest Pulse, recap, and Match Bridge |
| P2 | Groups | Mostly static shells | Asynchronous Circles before live audio |
| P2 | Payment | Manual/partial flows | Server-authoritative entitlements and restore |
| P3 | Packaging | Caches, generated files, unused assets | Clean reproducible source package |

---

## 15. Zero-known-bug quality program

### 15.1 Definition of zero-known-bug release

Milan is “zero-known-bug ready” when:

- There are zero open P0 or P1 defects.
- Every primary user action has a passing E2E test.
- No privacy or authorization regression exists.
- No secret or sensitive log is present.
- No public claim lacks an implemented path.
- No primary route is a static shell or no-op.
- The full build, migration, and release pipeline is reproducible.
- Accessibility, localization, low-bandwidth, and error states are tested.
- Known limitations are documented and feature-flagged rather than hidden.

This is a release definition, not a claim that undiscovered defects are impossible.

### 15.2 Test layers

#### Backend

- Unit tests for validation, policy, token derivation, and privacy transforms
- Integration tests for database transactions and migrations
- Authorization tests for every match, block, report, media, and account route
- Contract tests for mobile/web response shapes
- Adversarial tests for prompt injection, scam classification, moderation, and AI memory deletion
- Media tests for MIME, size, SSRF, signed URLs, expiry, and object deletion
- Payment tests for receipt validation, restore, expiry, refund, and downgrade
- Load tests for discovery, chat, notifications, and media

Do not globally stub all safety behavior in the release test environment. Use deterministic fakes only in isolated unit tests, and run real integration tests against controlled services.

#### Flutter mobile

- Unit tests for providers, parsers, theme derivation, and policy
- Widget tests for every primary screen and state
- Golden tests for Milan Sky and high-contrast themes
- Accessibility tests for semantics, text scaling, focus, and touch targets
- Integration tests for onboarding, swipe, match, chat, media, report, block, delete, and Saathi controls
- Offline and low-bandwidth tests
- Android/iOS build and signing checks
- Release smoke test on physical devices

#### Web

Add a real test command to `web/package.json` and cover:

- Component behavior
- Route and deep-link behavior
- Admin RBAC
- Payment form/JSON handling
- Theme persistence and contrast
- Accessibility and keyboard navigation
- Browser E2E for marketing, login, admin, and consumer surfaces

#### CI and supply chain

- Secret scanning
- Dependency scanning
- License scanning
- Static analysis
- Format checks
- Migration checks
- Route-manifest checks
- No-op-control detection
- Accessibility linting
- Visual regression
- Localization string coverage
- Archive checksum verification for reference packages
- Signed build provenance

### 15.3 Release gates

| Gate | Required result |
|---|---|
| Security | Zero known P0/P1 security defects; no exposed secrets |
| Auth | All registration paths enforce age and session policy |
| Privacy | Zero blocked-user access; zero private-media URL leakage |
| Media | Zero view-once replay; zero unscanned public media |
| AI | Memory deletion is complete; no unapproved auto-send |
| UX | Zero dead primary controls; all states recoverable |
| Accessibility | WCAG 2.2 AA acceptance for primary journeys |
| Localization | Primary mobile journeys complete in English and Nepali |
| Performance | agreed p95 latency and media budgets pass |
| Payments | Server-authoritative entitlement and restore tests pass |
| Release | Signed mobile/web artifacts build from a clean environment |
| Claims | Every public claim maps to a passing E2E scenario |

### 15.4 Defect policy

- P0: security, privacy, data loss, age bypass, or complete primary-loop failure. Release blocker.
- P1: major broken feature, incorrect state, inaccessible critical action, or misleading trust/payment behavior. Release blocker.
- P2: degraded feature, non-critical defect, or meaningful UX inconsistency. Must be triaged before general availability.
- P3: polish, copy, or low-impact edge case. May be scheduled.

No P0/P1 defect is waived without a written risk owner, expiry date, user impact analysis, and explicit release decision.

---

## 16. Phased implementation roadmap

### Phase 0 — Product truth, security, and release gate

**Objective:** Make the current product safe to beta test.

- Choose the Saathi policy.
- Create a capability ledger with route/endpoint/evidence/owner.
- Remove or feature-flag no-op and orphan routes.
- Rotate and remove secrets, logs, and signing artifacts.
- Fix production configuration and refresh/session controls.
- Enforce age and consent on all registration paths.
- Fix block, privacy, view-once, media moderation, and SSRF behavior.
- Fix swipe, voice, report IDs, location, and account lifecycle.
- Ship a real signed APK.
- Fix admin payment serialization.
- Add route-manifest and no-op-control tests.

**Exit criteria:** All P0 gates pass; no public claim depends on an unimplemented path.

### Phase 1 — Shared Milan Sky design system

**Objective:** Establish one cross-platform visual and interaction contract.

- Create versioned design tokens.
- Replace hardcoded web and Flutter colors.
- Implement Milan Sky, Cloud High Contrast, and optional dark presets.
- Implement real global Theme Studio.
- Derive accessible foregrounds and borders.
- Add theme persistence, sync, preview, and reset.
- Add text scale, density, and motion controls.
- Add visual regression and accessibility gates.

**Exit criteria:** Web and mobile render the same core screens from the same contract; custom themes cannot create unreadable controls.

### Phase 2 — Complete the dating core

**Objective:** Deliver a truthful primary journey.

- Adaptive onboarding
- Independent identity and intent fields
- Current/home/Passport location
- Profile media manager
- Four-to-six explainable recommendations
- Calibration and preference confirmation
- Passed/rewind flow
- Match transaction
- First conversation
- Profile insights with privacy controls
- Report/block everywhere

**Exit criteria:** A new adult user can complete the full primary loop with no dead control or privacy leak.

### Phase 3 — Trust, chat, payments, and operations

**Objective:** Make core communication and monetization reliable.

- Complete text/image/voice media contract.
- Add delivery and retry states.
- Implement or remove Share Date.
- Hide calls until real RTC/signaling exists.
- Add server-authoritative payment entitlements and restore.
- Add admin RBAC, MFA, moderation queue, and audit logs.
- Add app lock, discreet notifications, and low-data behavior.

**Exit criteria:** Chat, payment, and operations pass contract, security, and recovery tests.

### Phase 4 — Differentiated retention and social features

**Objective:** Add only innovations that reinforce Milan’s position.

- Milan Passport research and beta
- Saathi Match Bridge
- Post-date debrief
- Visible/editable memory
- Milan Pulse
- Asynchronous Circles
- Private weekly recap
- Date ideas and low-pressure rituals

**Exit criteria:** Each feature has measurable user value, privacy review, moderation plan, and rollback path.

### Phase 5 — Hardening and staged rollout

- Accessibility audit
- Localization review
- Low-bandwidth testing
- Load and soak testing
- Security review
- Media failure testing
- Analytics validation
- Support and moderation staffing
- Staged beta rollout
- Public-claims review

---

## 17. Metrics and research backlog

### 17.1 Product metrics

Do not use raw swipes, message count, or AI session time as the north-star metric.

Track:

- Onboarding completion
- Complete and approved profile rate
- Time to first relevant match
- First human message within 24 hours
- Seven-day return after a meaningful conversation
- Date-plan or continued-connection rate
- Report/block and scam-warning rates
- Safety response time and false-positive rate
- Payment verification, restore, refund, and support rate
- Passport adoption and return-home usage
- Saathi-to-real-dating progression
- Theme save and accessibility success
- Mobile/web parity for Tier A journeys
- Localization and accessibility coverage

### 17.2 Research agenda

Research before committing to major features:

1. Serious relationship versus friendship versus community intent
2. Marriage-oriented users and cultural expectations
3. Diaspora use in Gulf, Malaysia, Europe, and return-home journeys
4. Saathi practice-only versus warm-companion comprehension
5. Discreet mode, hidden fields, app lock, and notification privacy
6. Share Date and trusted-contact expectations
7. Scam-warning comprehension and false-positive tolerance
8. NPR 299/699/1,299 willingness to pay and 30-day pass preference
9. Local-wallet checkout and restore behavior
10. Low-bandwidth image, voice, and offline expectations
11. Screen-reader, low-vision, older-user, and motor-access needs
12. Asynchronous Circles versus live-room demand
13. Match quality and conversation-to-date conversion
14. Cultural localization by native Nepali speakers

### 17.3 Experiment backlog

- Four-to-six explainable recommendations versus larger deck
- Prompt-first profile versus photo-first profile
- Blind First session length and reveal timing
- Passport banner and return-home placement
- Saathi Match Bridge opt-in language
- Milan Pulse delayed versus immediate reveal
- Asynchronous Circle topic formats
- Theme presets and custom accent editor usability

Every experiment must have a hypothesis, primary metric, guardrail metric, stop condition, and privacy review.

---

## 18. Decision log and open questions

### Decisions already recommended

- Preserve Milan’s backend and design architecture.
- Do not merge the archive’s Firebase implementation.
- Adapt Passport as an expiring discovery location.
- Reimplement remote configuration behind the backend.
- Make safety controls free and server-authoritative.
- Separate payment entitlement from identity verification.
- Make Saathi disclosure and memory control persistent.
- Start with asynchronous Circles, not live rooms.
- Use a measurable zero-known-bug release gate.

### Decisions requiring product approval

- Saathi practice-only versus warm-companion scope
- Whether Passport is free, paid, or limited by tier
- Whether Milan supports friendship and community in the first release
- Exact premium tier matrix and local-wallet checkout
- Whether to support calls in the first public release
- Whether to include a public Milan Pulse or keep it opt-in/private by default
- Whether to build authenticated consumer web parity or keep the first consumer experience mobile-only

### Questions to resolve through research

- Which segments produce the highest meaningful-conversation and date-conversion rates?
- Which privacy fields do diaspora users most want to hide?
- What level of AI assistance increases real-world confidence without reducing human initiation?
- What group format creates value without increasing harassment risk?
- Which theme customization dimensions are useful beyond accent color?
- What low-bandwidth behavior do users expect on Nepalese mobile networks?

---

## 19. Deprecation and cleanup list

The following should be removed, hidden, or feature-flagged until complete:

- Static call screens
- Unlinked Jhalak stories/camera/viewer
- Unverified live rooms
- Fake or disconnected boosts
- Dead export/delete controls
- Missing APK links
- Broken recap routes
- No-op Theme Studio controls
- Unreachable Kundali route
- Orphan Saathi debrief/voice screens
- Inactive ad hooks with test IDs
- Unused Firebase/Agora/social-login scaffolding
- Client-only purchase verification
- Client-only report/block state
- Public claims for features without passing E2E tests

---

## 20. Appendix: source paths

### Current Milan planning documents

- `00_milan_master_prompt.md`
- `01_milan_vision_and_market_research.md`
- `02_milan_design_system_and_screens.md`
- `03_milan_flutter_app_build_prompt.md`
- `04_milan_backend_flask_build_prompt.md`
- `05_milan_ai_companion_and_matching_groq_prompt.md`
- `06_milan_web_nextjs_prompt.md`
- `07_milan_ai_girlfriend_realism_and_innovation_masterplan.md`
- `08_companion_realism_transformation_plan.md`

### Current Milan implementation paths

- `mobile/lib/app/router.dart`
- `mobile/lib/features/onboarding/presentation/screens/onboarding_screens.dart`
- `mobile/lib/features/discovery/presentation/screens/discover_screen.dart`
- `mobile/lib/features/chat/presentation/screens/chat_thread_screen.dart`
- `mobile/lib/features/safety/presentation/screens/safety_screens.dart`
- `mobile/lib/features/saathi/presentation/screens/saathi_extra_screens.dart`
- `mobile/lib/shared/widgets/swipe_card.dart`
- `mobile/lib/app/theme/color_tokens.dart`
- `mobile/lib/features/personalization/presentation/screens/chat_theme_studio_screen.dart`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/blueprints/auth/__init__.py`
- `backend/app/blueprints/profile/__init__.py`
- `backend/app/blueprints/safety/__init__.py`
- `backend/app/blueprints/chat/__init__.py`
- `backend/app/blueprints/jhalak/__init__.py`
- `backend/app/blueprints/media/__init__.py`
- `backend/app/services/moderation_service.py`
- `backend/app/services/media_service.py`
- `backend/app/services/matching_service.py`
- `backend/app/blueprints/saathi/__init__.py`
- `backend/app/services/context_engine.py`
- `backend/app/services/companion_prompt.py`
- `backend/app/tasks/matching_tasks.py`
- `backend/app/tasks/media_tasks.py`
- `backend/tests/conftest.py`
- `web/package.json`
- `web/src/app/globals.css`
- `web/src/lib/admin-api.ts`
- `web/src/app/(site)/features/page.tsx`
- `web/src/app/(site)/privacy/page.tsx`
- `web/src/app/(site)/saathi/page.tsx`
- `web/src/app/(site)/page.tsx`

### Archive paths most relevant to adaptation

- `M/Dating-App/lib/screens/passport_screen.dart`
- `M/Dating-App/lib/screens/settings_screen.dart`
- `M/Dating-App/lib/screens/update_location_sceen.dart`
- `M/Dating-App/lib/screens/profile_screen.dart`
- `M/Dating-App/lib/screens/profile_likes_screen.dart`
- `M/Dating-App/lib/screens/profile_visits_screen.dart`
- `M/Dating-App/lib/screens/disliked_profile_screen.dart`
- `M/Dating-App/lib/screens/chat_screen.dart`
- `M/Dating-App/lib/screens/home_screen.dart`
- `M/Dating-App/lib/tabs/discover_tab.dart`
- `M/Dating-App/lib/tabs/matches_tab.dart`
- `M/Dating-App/lib/tabs/conversations_tab.dart`
- `M/Dating-App/lib/tabs/profile_tab.dart`
- `M/Dating-App/lib/widgets/profile_card.dart`
- `M/Dating-App/lib/widgets/store_products.dart`
- `M/Web-Admin-Panel/lib/screens/dashboard.dart`
- `M/Web-Admin-Panel/lib/widgets/my_navigation_drawer.dart`
- `M/Cloud Functions/index.js`
- `M/Documentation-README-FIRST/index.html`

### External research

- [W3C WCAG 2.2 contrast minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
- [W3C WCAG 2.2 target size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [Hinge Dating Forward](https://hinge.co/newsroom/dating-forward)
- [Hinge product evolution](https://hinge.co/newsroom/hinge-2025-product-evolution)
- [Bumble features](https://bumble.com/the-buzz/bumble-dating-features)
- [Bumble safety](https://bumble.com/en-us/the-buzz/safety)
- [FTC romance scams 2025](https://consumer.ftc.gov/consumer-alerts/2025/02/looking-love-watch-out-scammers)
- [FTC romance scams 2026](https://consumer.ftc.gov/consumer-alerts/2026/02/why-cant-new-love-interest-meet-person)
- [FTC AI companion inquiry](https://www.ftc.gov/news-events/news/press-releases/2025/09/ftc-launches-inquiry-ai-chatbots-acting-companions)
- [Common Sense Media AI companions](https://www.commonsensemedia.org/research/talk-trust-and-trade-offs-how-and-why-teens-use-ai-companions)
- [RevenueCat State of Subscription Apps](https://www.revenuecat.com/state-of-subscription-apps/)
- [EU AI Act](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)
- [EU DSA impact](https://digital-strategy.ec.europa.eu/en/policies/dsa-impact-platforms)

---

## 21. Final implementation order

The next implementation sequence should be:

1. Establish the capability ledger and Saathi policy.
2. Fix P0 security, privacy, auth, blocking, media, swipe, voice, report, and release blockers.
3. Create the shared Milan Sky token contract.
4. Build the real global Theme Studio and cross-platform theme persistence.
5. Complete profile media, location/Passport, discovery, calibration, passed/rewind, match, and first-conversation flows.
6. Complete chat media/delivery states, safety, privacy, export/delete, and payments.
7. Add accessibility, localization, low-bandwidth, load, and release gates.
8. Only then launch Passport, Saathi Match Bridge, Milan Pulse, asynchronous Circles, and further experiments.

**The archive is a useful product checklist and source of design questions. It is not a safe codebase to merge.**
