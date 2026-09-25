# Doc 8 — Milan Full-System Transformation Plan

Two goals, one program of work:

1. **Companions become people.** Own history, own voice, own day, own initiative, adapting automatically to how each user writes.
2. **The app becomes premium.** Messenger-grade chat, a real design system, working media/voice/GIF, real presence, real algorithms, no mock surfaces.

Supersedes the practice-coach model in doc 5. Absorbs doc 7 §4/§13/§14 and the dobato feature audit.

---

## PART A — Verified current state

Everything below was read in source. Line references are clickable.

### A1. Why every character replies in English

The screenshot ("I'm Priya, your conversation-practice companion") is architecture, not a prompt slip.

| # | Defect | Evidence |
|---|---|---|
| A1.1 | Two prompt paths. `asha`/`bibek`/`priya`/`sagar` use the **coach** template opening with "help the user practice conversation, build dating confidence" | [groq_service.py#L77-L112](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L77-L112) |
| A1.2 | Coach path is `companion_enabled=False`, so it skips the language block, persona block **and** lorebook | [groq_service.py#L950-L954](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L950-L954) |
| A1.3 | Free tier gets **0** companions and **0** auto-texts → free users are funnelled to a coach | [subscription_service.py#L26-L41](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/subscription_service.py#L26-L41) |
| A1.4 | Nothing detects the user's script or register. `timro name k ho` (roman Nepali, informal) → English, then formal Devanagari `तपाईंलाई` | no code path exists |
| A1.5 | Presence is computed for the UI but never reaches timing — `reply_timing(reply, "free")` is hardcoded | [groq_service.py#L1006](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L1006) |
| A1.6 | Burst splitting is a flat 30% coin flip gated on `burst_pref > 1` → replies arrive as one block | [groq_service.py#L830-L834](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L830-L834) |
| A1.7 | Context = fixed 10 turns + **every** memory item dumped raw. No budget, no ranking, no compaction | [groq_service.py#L1022-L1033](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L1022-L1033) |
| A1.8 | Auto-texts write only to `SaathiMessage`, never the unified `Message` thread → invisible in the inbox | [notification_tasks.py#L158-L161](file:///home/bishal-regmi/Desktop/Milan/backend/app/tasks/notification_tasks.py#L158-L161) |
| A1.9 | `· AI` appended to every display name in every payload | [serializers.py#L87-L93](file:///home/bishal-regmi/Desktop/Milan/backend/app/utils/serializers.py#L87-L93) |
| A1.10 | Offline twin returns coaching copy ("What are we practising today?") | [groq_mock.py#L291-L329](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_mock.py#L291-L329) |
| A1.11 | Companions have **no** profile images. `avatar_urls` is never populated; `COMPANION_FACE_PROMPTS` exists but is only used for on-demand selfies | [groq_service.py#L1779-L1835](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L1779-L1835) |

### A2. Chat surface bugs

| # | Bug | Evidence |
|---|---|---|
| A2.1 | **Typing never relays for humans.** `Match.query` with no `Match` in scope → `NameError` on every typing event | [chat_events.py#L47](file:///home/bishal-regmi/Desktop/Milan/backend/app/sockets/chat_events.py#L47) |
| A2.2 | **Typing bubble sticks forever.** No expiry timer; a missed `typing:false` leaves it up. This is the "always appears in AI chat" symptom | [chat_providers.dart#L270-L286](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/application/chat_providers.dart#L270-L286) |
| A2.3 | Client sends the socket token via handshake `auth`; server reads `request.args['token']` or `data['token']` → typing/presence unauthenticated even after A2.1 | [websocket_client.dart#L110-L114](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/core/network/websocket_client.dart#L110-L114) |
| A2.4 | **`last_message` never parsed** → every inbox row reads "Say namaste 👋" | [chat_providers.dart#L71-L83](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/application/chat_providers.dart#L71-L83) |
| A2.5 | Thread hydrates from sqflite and **never refetches** → auto-texts received while offline never appear | [chat_providers.dart#L132-L142](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/application/chat_providers.dart#L132-L142) |
| A2.6 | Socket messages drop `media_url` and `is_ai_suggested` → an inbound image renders as an empty bubble | [chat_providers.dart#L119-L125](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/application/chat_providers.dart#L119-L125) |
| A2.7 | Suggestion chips write into a `ComposerRegistry` list; the screen's send button state never rebuilds, and the Saathi composer isn't registered at all | [chat_thread_screen.dart#L447](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/presentation/screens/chat_thread_screen.dart#L447) |
| A2.8 | Header shows `peer?.otherName ?? ''` from a linear scan of the matches list — blank on cold open, no presence line | [chat_thread_screen.dart#L137-L160](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/presentation/screens/chat_thread_screen.dart#L137-L160) |
| A2.9 | Voice note posts `body: '[voice note]'` with no `media_type`; there is no player in the thread — recording works, playback does not exist | [chat_extra_screens.dart#L54-L67](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/presentation/screens/chat_extra_screens.dart#L54-L67) |
| A2.10 | `read_delay_seconds`, `delayed_reply`, `degraded`, per-message `segments` are returned by the server and ignored by the client | [chat_providers.dart#L184-L202](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/application/chat_providers.dart#L184-L202) |
| A2.11 | Media messages render as a bare `Image.network` — no bubble, no timestamp, no cache, no progress | [chat_thread_screen.dart#L202-L217](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/presentation/screens/chat_thread_screen.dart#L202-L217) |
| A2.12 | `Message` has no `media_type` column → server cannot distinguish image / gif / audio | [chat.py#L10-L21](file:///home/bishal-regmi/Desktop/Milan/backend/app/models/chat.py#L10-L21) |

### A3. Theme / design-system defects

| # | Defect | Evidence |
|---|---|---|
| A3.1 | **Text scales twice.** `_t()` pre-multiplies by the text scaler while `app.dart` also installs a `TextScaler` → 1.4 setting yields 1.96× | [type_tokens.dart#L93](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/type_tokens.dart#L93) |
| A3.2 | **No theme-mode control.** `themeMode: ThemeMode.system` is hardcoded; the comment claims a Settings override that does not exist | [app.dart#L38-L41](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/app/app.dart#L38-L41) |
| A3.3 | **Appearance screen is unreachable.** `my_profile_screen` pushes `/settings/appearance`; no route exists and the router has no `errorBuilder` | [router.dart](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/app/router.dart) |
| A3.4 | Chat surfaces bypass tokens entirely — `0xFFF1F3F6`, `0xFF8A919C`, `Colors.white`, `0xFF0B84FE` hardcoded across inbox/thread/bubble | inbox L33-L55, thread L269-L284, bubble L41-L42 |
| A3.5 | No `ThemeData.textTheme` → any bare `Text` falls back to the platform font, not Manrope | [color_tokens.dart#L154-L203](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/color_tokens.dart#L154-L203) |
| A3.6 | Accent is device-local only, 5 fixed choices, never custom, never synced | [accent_theme.dart#L45-L51](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/accent_theme.dart#L45-L51) |
| A3.7 | Sound/haptics toggles are persisted but have **no UI**; `messageReceived` and `keyboardish` are never played | [sfx.dart#L51-L79](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/core/feedback/sfx.dart#L51-L79) |
| A3.8 | `shimmer` is a declared dependency, never imported. One pulse skeleton exists (inbox); 20+ screens use a bare spinner | pubspec L51 |
| A3.9 | Unused motion tokens: `swipeSpring`, `matchCelebration`, `storyTransition`, `springOut`, `standard`. Swipe card snaps back with no animation | [swipe_card.dart#L54](file:///home/bishal-regmi/Desktop/Milan/mobile/lib/shared/widgets/swipe_card.dart#L54) |
| A3.10 | Orphaned screens: `ChatThemeStudioScreen` (all callbacks no-op), `SnapViewerScreen`, `SaathiCharacterGalleryScreen` (hardcoded "practice companion" grid) | router |

### A4. Discovery / matching / profile defects

| # | Defect | Evidence |
|---|---|---|
| A4.1 | **"Milan user" on cards.** `user_brief` returns `display_name: null` when a profile row is missing; deck does not require a profile or a photo | [serializers.py#L87-L93](file:///home/bishal-regmi/Desktop/Milan/backend/app/utils/serializers.py#L87-L93), [discovery/__init__.py#L47-L61](file:///home/bishal-regmi/Desktop/Milan/backend/app/blueprints/discovery/__init__.py#L47-L61) |
| A4.2 | Ranking uses 3 signals only (interests ∩, intent ==, style complement) from a base of 40. **Distance is computed but never scored.** No activity recency, no reciprocity, no boost multiplier in the deck | [matching_service.py#L29-L56](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/matching_service.py#L29-L56) |
| A4.3 | Deck ignores `latitude`/`longitude` entirely; the `distance_km` field the client reads is never sent by `/candidates` | discovery L77-L90 vs `CandidateProfile.fromJson` L32 |
| A4.4 | Interview answers **are** stored (`relationship_intent`, `conversation_style`, `lifestyle_tags`, `values_tags`, `dealbreakers`) but `lifestyle_tags`/`values_tags`/`dealbreakers` are **never read by ranking** | [profile/__init__.py#L237-L249](file:///home/bishal-regmi/Desktop/Milan/backend/app/blueprints/profile/__init__.py#L237-L249) vs matching_service |
| A4.5 | Interests are a free-text JSON array with no catalog → `_shared_interests` compares raw strings, typos never match | [user.py#L58](file:///home/bishal-regmi/Desktop/Milan/backend/app/models/user.py#L58) |
| A4.6 | No `ProfileView` model → "who viewed me" cannot exist | models |
| A4.7 | No match expiry — `Match.is_active` is never aged out | matching.py |
| A4.8 | Location: `permission_service` exists and onboarding explains why location is needed, but `latitude`/`longitude` are never captured or sent | permission_service.dart |
| A4.9 | No user-search screen; discovery filters exist server-side but there is no name/interest search endpoint | discovery |
| A4.10 | No profanity filter anywhere; `moderation_service` only calls Llama Guard, which needs network | moderation_service.py |

### A5. Worth importing from dobato

Verified present there, absent here:

- **Interests catalog** (`Interest` + `UserInterest`, icon + category, seeded taxonomy, `PUT /interests/me` with dedup/limit validation) → fixes A4.5.
- **Trust score** as a single persisted scalar. Milan has far richer signals (`LivenessCheck`, `FaceEmbedding`, `ScamFlag`, `ModerationEvent`) but never rolls them into one number.
- **Redis-backed socket presence** with multi-socket-per-user sets and TTL. Milan's presence is per-process and dies with >1 worker.
- **Soft delete** (`deletedAt` filtered in every read) → "delete account" currently has no reversible implementation.
- **Uniform response envelope** + declarative validation.

Explicitly **not** importing: dobato's wallet top-up mints coins with zero payment verification, and its `join-room` lets any authenticated socket subscribe to any conversation. Milan's Celery beat, swipe economy, block table, notification caps and payment-submission audit trail are all ahead of dobato — do not port backwards.

---

## PART B — Design system

Direction: **Messenger clarity + Nepali warmth.** White canvas, blue action, marigold reserved for identity moments (match, streak, festival). Not a marigold-tinted app with blue accents — a white app whose *warmth* comes from imagery and moments, not chrome.

**Domain:** the chautari (village gathering tree), tika, momo steam, monsoon light, Dashain marigold garland, Patan brick.
**Color world:** rice-paper white, monsoon-cloud grey, dhaka-weave crimson, marigold, pine terrace, Patan brick dust.
**Signature:** the *presence dot* — a small living indicator that carries her simulated day (awake / at class / asleep), used on the avatar in inbox, header and profile. Nothing else in the category shows a companion's day this way.
**Defaults rejected:** (1) tinted chat wallpaper by default → white canvas, wallpaper opt-in; (2) grey-on-grey card stacks → borders-only depth; (3) purple/gradient SaaS accent → single blue action colour, user-editable.

Token layers:

```
surface.canvas       #FFFFFF     surface.raised   #FFFFFF + border
surface.sunken       #F1F3F6     surface.overlay  #FFFFFF + shadow.sm
content.primary      #0B1520     content.secondary #5A6472
content.tertiary     #8A919C     content.inverse   #FFFFFF
line.hairline        #E6E9EE     line.strong      #D2D7DE
action.default       #0B84FE  (user-editable, any colour)
action.pressed       computed −8% L    action.subtle  computed 12% α
identity.marigold    #F5A623     identity.dhaka   #7B1E3A     identity.pine #1F6F54
status.online        #31C48D     status.away      #F5A623     status.asleep #8A919C
feedback.error       #E0384C     feedback.warning #B8791A     feedback.success #1F8F62
```

Depth: **borders-only**, one shadow level for overlays. No mixed strategy.
Spacing: 4px base — 4 / 8 / 12 / 16 / 24 / 32 / 48.
Radius: 8 control / 12 card / 18 bubble / 999 pill.
Type: Sora display, Manrope UI, Noto Sans Devanagari auto-swapped per run. Scale 32/28/24/20/17/15/13/11 — chat body 15.5/1.35 matching Messenger.
Motion: 120ms micro, 180ms standard, 260ms overlay, `easeOutCubic`; spring only on the swipe card.

Theme control: `ThemeMode` (system/light/dark) + **custom accent picker** (any colour, contrast-gated) + text scale + reduce motion + sound + haptics, all persisted and applied globally. Default light, white, blue.

---

## PART C — Backend work

### C1. Migration `f1a2b3c4d5e6` (on `e9f2a3b4c5d6`)

```
saathi_characters   + persona_bible JSON, age INT, birthday VARCHAR(5), hometown
saathi_sessions     + user_style JSON, rolling_summary TEXT, summary_upto_message_at,
                      awaiting_user_reply BOOL, deferred_reply_at, last_initiative_at
saathi_memory_items + last_recalled_at
messages            + media_type VARCHAR(16)          -- image | gif | audio
profiles            + last_active_at, interests_catalog JSON
users               + deleted_at, trust_score INT DEFAULT 50
matches             + expires_at, last_activity_at
NEW interests            (key, label, icon, category)
NEW profile_views        (viewer_id, viewed_id, created_at)
DATA  companion_mode 'practice' -> 'dating'; companion_enabled = true for all
```

### C2. New services

| Service | Responsibility |
|---|---|
| `persona_bible.py` | 11 full human dossiers (family, history, loves, hates, insecurities, quirks, boundaries, weekly life) + `render()` |
| `language_engine.py` | `analyze()` → script / language / register / romanization / verbosity / emoji / slang; `update_style()` EWMA α=0.3; `directives()`; `enforce()` re-roll when the draft violates an ≥80%-consistent script |
| `context_engine.py` | Devanagari-aware token estimate, 6-layer budgeted assembly, rolling-summary compaction |
| `companion_prompt.py` | Layered builder; `sincere_ai_inquiry()` classifier; deletes the coach template |
| `realism_engine.py` | `day_context()` (deterministic per day), presence-aware `reply_plan()`, `should_defer()`, `segment()` |
| `initiative_engine.py` | Scored autonomous texting; plan extraction ("visiting Pashupati, talk tonight") → mid-day trigger |
| `text_filter.py` | Nepali + English profanity/rough-word filter, no network |
| `trust_service.py` | Rolls liveness + face-embedding + reports + completeness into `trust_score` |

### C3. Model routing (cheap where cheap is fine)

| Task | Model | Why |
|---|---|---|
| companion chat | `llama-3.3-70b-versatile` | voice quality is the product |
| status post, open loops, mirror, quest, icebreaker | `llama-3.1-8b-instant` | short, structured |
| rolling summary, style digest | `llama-3.1-8b-instant` | bulk, offline |
| moderation | `llama-guard-4-12b` | purpose-built |
| injection | `llama-prompt-guard-2-86m` | 86M params |
| transcription | `whisper-large-v3-turbo` | cheapest ASR |

### C4. Language mirroring — the direct fix for the screenshot

`analyze()` runs on every inbound message; signals accumulate on `saathi_sessions.user_style` as an EWMA so one odd message can't flip her voice but a genuine switch converges in ~3 turns. Rendered as hard prompt directives, then **post-enforced**: ≥80% script consistency over the last 5 messages + a violating draft → one re-roll with a stricter directive. `timro name k ho` now gets roman-Nepali informal back, every time.

### C5. Initiative engine

```
score = w_loop·loop_due + w_plan·stated_plan_elapsed + w_gap·silence_curve
      + w_hour·user_online_prior + w_mood·mood_pull + w_event·(festival|milestone)
      - penalty_recent_send - penalty_awaiting_user_reply
```

Gates: her presence awake · user quiet hours · tier cap · notification cap · dedupe vs last 20 (keyword + opening-phrase blacklist). `user_online_prior` is learned from the hours the user actually sends.

**Delivery** writes to the unified `Message` table under `session.match_id`, broadcasts `chat:message`, mirrors to `SaathiMessage` for memory, and pushes — so it appears in the inbox like any human text (fixes A1.8).

Plan tracking answers the user's scenario directly: "going to Pashupati, talk tonight" → `SaathiOpenLoop` with `followup_after_hours` derived from the stated time; mid-day she may check in once ("pashupati kasto thiyo?"), and at night the promised conversation opens with full context.

### C6. Companion profile images

Every character gets a locked face prompt (already authored) used to pre-generate **4 gallery images** at seed: portrait, candid, activity-from-her-life, mirror-selfie. Written to `avatar_urls` + `Photo` rows so companions look identical to human profiles in deck, inbox, header and profile. In-chat requests ("send a pic") route through the same locked face so it is always the same person, delivered with human latency, never instantly.

### C7. Tier access

| | free | basic | plus | premium |
|---|---|---|---|---|
| companions | **1** | 2 | 4 | 8 |
| auto-texts/day | **2** | 4 | 6 | 10 |
| status posts/day | **1** | 2 | 3 | 3 |
| intimacy cap | **40** | 65 | 85 | 100 |
| voice notes | – | – | ✓ | ✓ |

### C8. Discovery ranking v2

```
score = 22·interest_jaccard + 14·intent_match + 10·values_overlap
      + 12·distance_decay(km) + 10·activity_recency + 8·style_complement
      + 8·reciprocal_like + 6·photo_completeness + 5·verified
      + 5·prompt_depth − 20·dealbreaker_hit
      × boost_multiplier
```

Every term draws on data already collected in onboarding (A4.4 finally consumed). Candidates now require a display name **and** at least one approved photo — killing "Milan user" at the source.

### C9. Also fixed

- `chat_events.py` `Match` import + `db.session.get` + token accepted from handshake auth.
- Redis presence adapter so `last_seen`/online survives multiple gunicorn workers.
- `Message.media_type` so image / gif / audio round-trip.
- Interests catalog seeded with a Nepali taxonomy.
- `ProfileView` + `/discovery/viewed-me`.
- Match expiry sweep (72h no-message → expired, warned at 48h).
- `/discovery/search` by name, interest, city.
- Profanity filter on messages, bios, prompts, display names.
- Demo QR rows for all four wallets so checkout is testable end-to-end.

---

## PART D — Flutter work

1. **Design system** — token file, `ThemeData.textTheme`, fix double text-scaling, `ThemeMode` controller, custom accent picker, route the Appearance screen.
2. **Chat rebuild** — Messenger layout; presence header with the signature presence dot; bubble groups with tail-only radius; delivered/read ticks; per-segment reveal honouring `read_delay` → typing → gaps; typing bubble with a 6s expiry; suggestion chips that actually fill the composer; image + GIF + voice with inline player and cached thumbnails; "delivering…" state; message sounds.
3. **Inbox** — parse `last_message`, presence dots, unread pill, shimmer skeleton, swipe actions.
4. **Companion roster** — vertical list with full text (not the clipped grid), tapping opens a **real profile screen** identical in shape to a human profile.
5. **Discovery** — spring-back swipe, skeletons, cached images, search screen, who-viewed-me, filters wired to the new ranking.
6. **Onboarding** — capture location for real, persist every interview answer, show what was learned.
7. **Profile** — self view vs public view (`/profile/<id>/public`), completeness meter, trust badge.
8. **Settings** — theme mode, accent, text size (fixed), reduce motion, sound, haptics, language; notification prefs already work server-side; payments show "Coming soon" + demo QR.
9. **Feedback** — sounds and haptics on send/receive/match/swipe/refresh/error/success, respecting the new toggles.
10. **Performance** — `CachedNetworkImage` everywhere with shimmer placeholders, `cacheWidth` decode hints, shimmer skeletons on every async surface.

---

## PART E — Boundaries kept

Persona immersion is total; five rails stay, enforced in code:

1. **Sincere-inquiry honesty** — a direct, sincere "are you a real person / a bot" gets the truth, via a classifier pass, not model discretion. Flavour questions ("kaha chau?") stay in character.
2. **No sexual content** — `moderate_content()` on every output.
3. **No minors** — age gate + Llama Guard minor-safety.
4. **No money, ever** — heuristics on input and output.
5. **Crisis protocol** — keyword + classifier → crisis card at every stage.

Removed: the blanket romance ban, "never role-play being human", "your purpose is to help the user practice", the `· AI` suffix, and every in-chat AI badge. Disclosure lives on the profile screen and in the ToS.

---

## PART F — Verification

`pytest` (new `test_companion_realism.py`, `test_discovery_ranking.py`, `test_text_filter.py`) · `flutter analyze` · `flutter test` (repair `chat_theme_test.dart` which asserts removed `'AI'`/`'SUGGESTED'` text).
