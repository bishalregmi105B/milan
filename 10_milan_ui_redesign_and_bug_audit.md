# Milan — UI Redesign & Bug Audit (2026-09-25)

This is the actionable output of a full pass: study of the CodeCanyon "Flutter
Complete Dating App v1.1.9" reference, 2025-26 dating-app UX research, and a
line-level audit of Milan's widgets, screens, Riverpod controllers, and the
app↔backend API contract. It complements `09_milan_archive_comparison_and_product_redesign_plan.md`.

"Zero bugs" is a direction, not a claim — this document tracks defects with
status so the bar is measurable.

---

## 1. Fixed this session (verified: `flutter analyze` 0 errors, backend 99 tests pass)

Realtime AI companion (prior turn):
- AI companion reply is now generated synchronously and returned in the HTTP
  body (no more socket-only delivery that stranded the user on a "typing…"
  bubble). Reactive replies never defer. Deployed to VPS.

Design system — dark mode + token cleanup (this turn):
- `app/theme/color_tokens.dart`: dark palette was still MAROON/rose while light
  was "Milan Sky" — rebuilt dark to bright-sky (`#38BDF8`) accent on near-black
  sky-tinted surfaces. Default accent now follows brightness (deep sky on light,
  bright sky on dark). `ColorScheme` now derives from `fromSeed(...).copyWith()`
  so every Material role (containers, `surfaceContainer*`, `onSurfaceVariant`,
  nav bar, chips) is coherent instead of falling back to off-brand defaults.
- `app/theme/spacing_tokens.dart`: ambient `shadowTint` rose→deep-sky.
- `shared/widgets/typing_indicator.dart`: hardcoded maroon default → theme
  primary.
- `shared/widgets/common.dart`: `StoryRing` and `CompatibilityMeter` arc
  gradients were hardcoded marigold→maroon → now Milan Sky tokens.

Bugs fixed (this turn):
- P0 `chat_providers.dart`: `chatThreadProvider` / `chatTypingProvider` /
  `companionPendingProvider` are now `autoDispose` (were leaking a socket-stream
  subscription + message list per opened thread for the whole session).
- P0 `app/router.dart`: added an auth-guard `redirect` + `refreshListenable` on
  `authProvider` — a session that dies mid-use now routes to onboarding instead
  of stranding the user on a dead authenticated screen.
- P1 `chat_theme_tokens.dart`: bubble hex was sent WITHOUT `#`, so every chat
  theme save 422'd and never persisted → now prefixed; `wallpaper_type` enum
  mapped camelCase↔snake_case to match the backend allow-list.
- P1 `chat_providers.dart` + `jhalak_snap_provider.dart`: load errors were
  swallowed (returned `[]`), making failures look like an empty inbox with a
  dead Retry button → now propagate to the error+Retry UI.
- P1 `chat_providers.dart`: `ChatMessage.fromJson`/`_fromCacheRow` used
  `DateTime.parse`/unguarded casts → one malformed row killed the whole thread;
  now null-safe `tryParse`. Chat error state got a real Retry button.
- P1 `api_client.dart`: a 401 from a credential-check endpoint (OTP verify /
  Google / add-phone) no longer triggers refresh+sign-out (was burning the OTP
  and spuriously signing users out mid-signup).
- P2 `saathi_chat_screen.dart`: added a `ScrollController` + auto-scroll (chat
  never scrolled to newest); disposed `_composer`; wired the dead theme button.
- P2 `profile_edit_screens.dart`: null-safe profile/user parse — a null profile
  no longer spins forever.

---

## 2. Open bugs (not yet fixed) — prioritized register

P1 — wire dead controls (data collected then discarded / buttons that no-op):
- Profile → Bio Assistant "Use this" is `onPressed: () {}` (`profile_edit_screens.dart`).
- Account settings: "Change email", "Change phone", "Export my data" are no-ops;
  the **Delete-account dialog has no delete action** (`settings_screens.dart`).
- Notifications "Mark all read" no-op (`settings_screens.dart`).
- Saathi Date Debrief "Done" never POSTs; its consent switch is stuck on
  (`saathi_extra_screens.dart`).
- Verification "Re-verify" no-op and hardcodes "Verified" regardless of status.
- Boost tiles + "Pay" no-op (`discovery_extra_screens.dart`).

P2 — correctness / robustness:
- Discovery deck REPLACES instead of appends at ≤3 remaining → unseen cards
  discarded (`discovery_provider.dart`).
- Distance filter is decorative — never sent to the API (`discovery_provider.dart`).
- Pagination envelope (`page`/`per_page`/`pages`) is produced by the backend but
  never sent/read → inbox capped at 20 matches, thread at 50 messages, no
  "load older" (`chat_providers.dart`, `matching/__init__.py`, `chat/__init__.py`).
- Duplicate `onSessionExpired` listeners accumulate across sign-in cycles
  (`api_client.dart` never clears listener lists).
- Composer `onChanged` callback never nulled on dispose (`chat_thread_screen.dart`).
- Uncached `NetworkImage`/`Image.network` in ~7 places (snap bubble/viewer, self
  gallery, QR, wallpapers) — no placeholder/error, re-downloads, unbounded memory.
- `ShareDateScreen` submit has no try/catch, loading, or double-tap guard.
- `NotificationCenterScreen` builds its future inside `build()` → refetch on every
  rebuild, no error state.
- Onboarding language cards are a no-op (locale switch only lives in Settings).
- `photoSet` chat wallpaper has no backend column (degrades to custom_upload).
- Audio-room socket handlers read the token from the query string only, but the
  app sends it via handshake auth → will break when audio rooms are wired
  (`sockets/audio_room_events.py`). Currently unused.

P2 — visual defects:
- `TypingDots` middle-dot opacity is dead (binary on/off), `chat_bubble.dart`.
- Jhalak tray re-sorts the whole list inside `itemBuilder` (O(n²·log n)/frame).
- Jhalak snap "drain" progress bar is static at 1.0, never animates.
- `MatchDetailScreen` celebration shows a generic person icon, not the match photo.
- `CallScreen`/`SaathiVoiceCallScreen` are visual stubs (mic/cam/report inert).

---

## 3. Reference-app design intelligence (adopt / beat)

The CodeCanyon template is feature/monetization-rich but visually dated
(pink, light-only, almost no motion). Strongest reusable ideas, ranked:
1. VIP-gated "who liked/visited you" grids with blurred lock cards — top
   monetization surface. (Milan has who-liked-you; add who-visited + blur lock.)
2. One polymorphic profile card serving swipe / grid / match / locked states.
3. A signature card-shape motif reused across cards, sheets, dialogs.
4. Benefit-list paywall with per-item icons + restore-purchases.
5. Physics swipe with grab-point-aware rotation + scaled peeking cards.
6. Rotated LIKE/NOPE stamps driven by drag progress.
7. Consistent state widgets (shimmer skeleton, icon empty state, spinner).
8. Unified colored-icon dialog factory (success/error/confirm/info).
9. Platform-adaptive report/block sheet (Cupertino vs Material).
10. Passport / location-change as a headline premium feature.

Reference GAPS Milan should beat (mostly missing there): match-celebration
animation, haptics, hero transitions, pull-to-refresh, multi-photo swipe card,
in-stack rewind, typing/receipts/reactions/voice in chat, dark mode,
profile-completion meter, boosts, superlike, prompts/interests, gifts.

---

## 4. 2025-26 trend brief (research)

- Translucency/"liquid glass" is being walked BACK for text-bearing chrome
  (legibility) — keep Milan's flat surfaces; use blur only for transient scrims
  and paywall previews. (NNGroup, iOS 26 Liquid Glass teardown.)
- Material 3 Expressive (May 2025) is the Android direction: bolder color,
  physics motion, larger emphasized type, shape as a token.
- Depth via tonal surface tiers + one soft ambient shadow (done in §1's scheme).
- Corner radii 16-28px cards, pill CTAs — Milan's scale already matches.
- Dark mode is table-stakes (fixed in §1). Accent lightens on dark (done).
- Motion table-stakes: spring swipe, like/super burst, match confetti (≤~900ms,
  skippable), skeleton shimmer, pull-to-refresh, typing indicator, HAPTICS on
  commit actions (like/superlike/match/send) — Milan only haptics in settings.
- Bottom sheets need a visible Close + back-dismiss, not just a grab handle.
- Buttons need explicit loading/pressed/disabled states; feedback <200ms.
- Skeletons: <1s show nothing, 2-10s spinner/skeleton, >10s determinate bar.
- Accessibility: WCAG AA 4.5:1 text; don't rely on color alone for state; honor
  OS text scale; reduced-motion = opacity-only fallback (keep the gesture).
Sources: nngroup.com (liquid-glass, bottom-sheet, button-states, skeleton-screens),
Wikipedia Material Design / Tinder / Hinge.

---

## 5. Redesign roadmap (widgets / components / screens)

Phase 1 — foundation (DONE this session): dark-mode Milan Sky parity, seeded
ColorScheme, sky shadow/gradient token cleanup across shared widgets.

Phase 2 — motion & feedback (next, high impact / low risk):
- Route like / superlike / match / message-send through `core/feedback/sfx.dart`
  for haptics (currently haptics only in settings).
- Match celebration: animate `MatchDetailScreen` (scale-in avatars + confetti,
  ≤900ms, skippable) and show the real match photo, not a generic icon.
- Hero transitions: swipe card photo → full profile; matched avatar → celebration.
- Pull-to-refresh on discovery and Jhalak (inbox already has it).
- Button loading/pressed states in `FilledButtonThemeData`/`OutlinedButtonThemeData`.

Phase 3 — discovery card (premium feel):
- Multi-photo swipe card: extend `CandidateProfile` to carry a photo list; add
  segmented top progress bars + tap-edges to page + a bottom gradient scrim
  behind name/age (white text currently sits directly on the photo).
- Render a 2-card peeking stack (scale/translate behind the top card).
- Wire in-stack rewind (undo the last card) to the server, not a list screen.
- Append-not-replace the deck when running low; send the distance filter.

Phase 4 — chat richness:
- Day separators + message grouping; send↔mic morph; delivered vs read.
- Standardize a `MilanSheet` (grab handle + visible Close + back-dismiss) and
  route the long-press timestamp + all bottom sheets through it.
- Cached images everywhere (replace raw `NetworkImage`/`Image.network`).

Phase 5 — growth / trust surfaces:
- Profile-completion meter tied to reach; verification badge on card + profile +
  match screen with a tappable explainer.
- Who-visited-you grid with blurred lock (mirror who-liked-you).
- Prompt/photo-level liking (Hinge pattern) feeding "why we matched".
- Reciprocal read-receipt / last-seen privacy toggle.

Phase 6 — consistency library:
- Extract shared state widgets (skeleton, empty, error+retry) and a colored-icon
  dialog factory so every screen uses one set; apply skeletons to discovery deck
  and profile view (only chat/inbox/search have them today).

---

## 6. Correctly-wired (no action needed)

Auth, profile, verification, media upload, discovery/swipe, matches/chat CRUD,
presence, saathi, jhalak, billing, safety, notifications endpoints are all
contract-correct (paths, methods, bodies, response keys, error shape, socket
events). The only broken integration was chat-theme persistence (§1, fixed).

---

## 7. Verification

- `flutter analyze lib`: 0 errors (pre-existing info lints + 3 pre-existing
  warnings unrelated to these changes).
- Backend `pytest tests/`: 99 passed.
- Reference archive studied read-only under /tmp (never added to the repo).
