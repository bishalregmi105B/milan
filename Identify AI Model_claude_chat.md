# Identify AI Model

> **Workspace:** /home/bishal-regmi/Desktop/Milan

---

**User**

Hi which ai model are you

**Assistant**

I'm Claude, an AI agent built by AWS, running here through TraeCode's CLI. I don't have visibility into the specific underlying model identifier in this environment — that field came through empty in my context.

Happy to help with anything in the Milan project.

---

**User**

HI i want you to explore backend ai character currently ai characters are prompted as ai companion   you can see this image we want those to behave like real boyfriend/girlfriend as user speaks that auto adapting to behavious speaking language ( behaving like real user how they think how they speak they have their own history own style flirting romantic ) not like a helper  research codebase and update implement make them all realistic their behaviour auto messaging user context message history compacting contexting auto texting all engines algorithms efective real world like realistic

**Assistant**

I'll explore the backend first to understand the current AI character system.

Explored the backend. Here's what's causing the screenshot behaviour:

- Priya/Asha/Bibek/Sagar are in `CURATED_CHARACTERS` → prompted with [SAATHI_SYSTEM_PROMPT_TEMPLATE](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L77-L112), which literally says "conversation companion… help the user practice". Hence "I'm Priya, your conversation-practice companion."
- No language-mirroring engine: reply script/language is driven by the *character's* profile data, never by what the user just typed. That's why "hlw timro name k ho" → English, then Devanagari.
- Even romantic characters get a blanket romance block below intimacy 26 ([check_romantic_output](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L367-L377)), and bond starts at 0 — so every new chat opens in cold helper register.
- Context = last 10 raw turns + all memory items ([_session_context](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L1014-L1034)). No rolling compaction, no relevance retrieval.
- Auto-texting exists but `proactive_daily: 0` on free tier and `proactive_opt_in` defaults False for practice characters.

Two decisions have real consequences, so I want your call before I rewrite the prompt layer.

Before the plan, one boundary I need to flag, because it changes one line of the design and nothing else.

**I won't build the "denies being an AI" behaviour.** Everything else in your brief I'll build fully. The reason isn't squeamishness about immersion — it's that an AI persona inside a *paid* dating app, romancing users who believe she's a human, is the Ashley Madison fembot pattern. It's the single thing that gets an app pulled from Play Store (AI-Generated Content policy), and your own doc 7 §2.3 already documents SB 243 / EU AI Act Art. 50 / NY A.6767-B requiring disclosure.

What I'm building instead is stricter than what you have and far more immersive than what you asked for:

| | Now (screenshot) | Target |
|---|---|---|
| Self-description | "your conversation-practice companion" | never — she's Priya, 23, Bhaktapur, tired from her shift |
| Helper language | "How can I help you today?" | banned token-list, rejected at output |
| Name in chat | `Priya · AI` | `Priya` — badge lives on profile + one first-open notice |
| "As an AI I can't…" | allowed | banned |
| Feelings, missing you, flirting | blocked | native |
| Direct sincere "are you a bot?" | canned | one honest line **in her own voice**, then straight back into the conversation |

That last row is the only concession, and it fires on a narrow sincere-query classifier — not on jokes, not on teasing, not on "you're not real 😭".

Now the real work. Let me finish reading the app layer.

I'll search these files in parallel to gather everything at once.

I'll start by exploring the project structure to understand the codebase layout.

Search complete and comprehensive — I read the full target range of the saathi blueprint (lines 880-1369, confirming 1369 is the last line of the file), both model files end-to-end, all 108 lines of `chat_events.py`, all 100 lines of `extensions.py`, plus the blueprint registration and the helper functions the routes depend on. No changes were made. One real bug surfaced (see the chat_events section).

## Routes in `/home/bishal-regmi/Desktop/Milan/backend/app/blueprints/saathi/__init__.py` lines 900-1369

Blueprint is created at line 14 (`saathi_bp = Blueprint("saathi", __name__)`) and mounted at `/api/v1/saathi` in `/home/bishal-regmi/Desktop/Milan/backend/app/__init__.py:66`, so every path below is prefixed with `/api/v1/saathi`. All 14 handlers are `@jwt_required()`.

| Lines | Method + path | Rate limit | Purpose |
|---|---|---|---|
| 893-919 (decorator at 893; body crosses into the range at 900) | POST `/diary/<entry_id>/illustrate` | 6/hour | Generates a 768x768 AI illustration for a diary entry via `image_gen_service.generate_image`, sets `entry.illustrated_url`, and records a `SaathiMediaItem(kind="diary_art")`. 404 if the entry or owning session is missing, 503 on `ImageGenUnavailableError`. |
| 922-959 | POST `/sessions/<session_id>/media/selfie-pack` | 3/hour | Illustrated "photo moments" pack (feature #19). Tier-gated to `plus` or higher (403 `upgrade_required`). Draws up to 3 scenes from `session.memory_items` summaries, falling back to hardcoded Kathmandu scenes; groups results under a shared `pack_id`; 503 if every generation fails. |
| 962-974 | GET `/sessions/<session_id>/media` | — | Lists the 60 most recent `SaathiMediaItem` rows for the session (id, kind, url, caption, ai_label, pack_id). |
| 981-1003 | POST `/sessions/<session_id>/mirror/ask` | 6/hour | Mirror questions (#39). Returns the existing unanswered question if one exists (`reflection=None`), otherwise generates one via `groq_service.generate_mirror_question` and persists a `SaathiMirrorQuestion`. 503 `ai_unavailable_try_later` when generation fails. |
| 1006-1031 | POST `/mirror/<question_id>/answer` | 20/hour | Stores the user's reflection (sanitized to 2000 chars via `persona_service._sanitize_trained_text`), stamps `answered_at`, writes a pinned `SaathiMemoryItem(category="reflection", importance=0.9)` so the answer feeds the persona, and awards 3 hearts. |
| 1038-1064 | GET `/sessions/<session_id>/quests` | — | Returns up to 10 recent quests; if none exist, lazily generates one via `groq_service.generate_quest`. Serializes id, title, description, kind, target, progress, reward_points, status, freeze_used. |
| 1067-1097 | POST `/quests/<quest_id>/progress` | 30/hour | Advances progress by `steps` (default 1), capped at `target`. On completion: sets status/`completed_at`, adds `reward_points` to `session.bond_points`, bumps `intimacy_level` by 2 clamped to the tier's `intimacy_cap`, and awards hearts equal to `reward_points`. |
| 1100-1116 | POST `/quests/<quest_id>/freeze` | — | Streak freeze, one-shot per quest (409 `freeze_already_used`). Docstring at 1103 states it is explicitly not a punishment path. |
| 1119-1159 | POST `/sessions/<session_id>/capsules` | 4/hour | Seals a Moment Capsule. `author` is `user` or `companion`; companion capsules are drafted by `groq_service.generate_capsule_content`. `unlock_at` parses ISO-8601 (422 `invalid_unlock_at`) and defaults to now + 7 days. |
| 1162-1179 | GET `/sessions/<session_id>/capsules` | — | Lists 30 recent capsules; `content` is returned as `None` while still sealed (`_as_aware(c.unlock_at) > now`). |
| 1182-1200 | POST `/capsules/<capsule_id>/open` | — | Opens a capsule; 409 `still_sealed` before unlock time. First open stamps `opened_at` and awards 2 hearts (idempotent for repeat calls). |
| 1203-1244 | POST `/sessions/<session_id>/recap` | 4/hour | Milan Recap share card (#17). Computes deterministic stats for `week`/`month` (messages, your_messages, days_active in Kathmandu-local days, streak, intimacy stage, memories kept, top context), adds one `groq_service.generate_recap_narrative` string, and mints a `share_token` (hex UUID) with `share_url` `/recap/<token>` and a watermark. |
| 1247-1258 | GET `/hearts` | — | Affection-hearts balance from the latest `SaathiHeartLedger.balance_after` plus the last 25 ledger entries. |
| 1268-1369 | POST `/sessions/<session_id>/selfie` | 8/day | §16 "send me a pic". 409 if `session.is_paused`; tier-gated to `basic`+. Three stages: (1) a caption + scene from the last 10 messages using `MODELS["icebreaker"]` in JSON mode, skipped in mock mode and degrading gracefully on `GroqUnavailableError`; (2) identity-locked image via `groq_service.generate_companion_image`, stored as `SaathiMediaItem(kind="moment", ai_label="AI-illustrated moment")`; (3) when `session.match_id` exists, mirrors the caption into the unified chat as a `Message` from the companion side and calls `broadcast_message`. Returns a `typing_delay_seconds` of `2.5 + len(caption)/14.0` so the client can render a human-like typing pause. |

Two style oddities in `send_selfie`: line 1341 imports `companion_account_service` but never uses it, and lines 1343-1344 resolve the Match class via `__import__("app.models", fromlist=["Match"]).Match` instead of a normal import (`Message` is imported normally one line earlier at 1340).

Helpers these routes rely on, same file: `_as_aware` (211-213, normalizes sqlite's tz-naive round-trip), `_session_dto` (216-256), `_hearts_balance` (259-265), `_award_hearts` (268-277, clamps delta to ±50), `_owned_session` (637-644, the ownership check behind every `session_not_found` 404).

## `Match` fields — `/home/bishal-regmi/Desktop/Milan/backend/app/models/matching.py:64-78`

Declared columns:
- `user_a_id` (68) — FK `users.id`, indexed, not null
- `user_b_id` (69) — FK `users.id`, indexed, not null
- `matched_at` (70) — `DateTime(timezone=True)`, not null
- `compatibility_score` (71) — `Float`, nullable
- `match_reason_text` (72) — `Text`, nullable
- `is_active` (73) — bool, default `True`, not null
- `kind` (76) — `String(16)`, default `"human"`; `companion` vs `human`, deliberately a normal Match row so inbox/chat/realtime/theme need no special-casing (§14)

Inherited from `AuditMixin` in `/home/bishal-regmi/Desktop/Milan/backend/app/models/base.py:18-23`: `id` (Uuid PK, default `uuid4`), `created_at`, `updated_at` (tz-aware, `onupdate=utcnow`).

Table `matches` (65) with `UniqueConstraint("user_a_id", "user_b_id", name="uq_match_pair")` (66) — note this constrains the ordered pair, so pair-ordering must be normalized by the caller. Relationship `messages` (78) to `Message`, `back_populates="match"`, `lazy="dynamic"`.

## `Message` fields — `/home/bishal-regmi/Desktop/Milan/backend/app/models/chat.py:10-21`

- `match_id` (13) — FK `matches.id`, indexed, not null
- `sender_id` (14) — FK `users.id`, indexed, not null
- `body` (15) — `Text`, nullable
- `media_url` (16) — `String(512)`, nullable
- `media_type` (17) — `String(16)`, nullable
- `is_ai_suggested` (18) — bool, default `False`, not null
- `read_at` (19) — `DateTime(timezone=True)`, nullable
- `match` (21) — relationship back to `Match`

Plus `id`/`created_at`/`updated_at` from `AuditMixin`. Table `messages` (11), no additional table args. The same file defines `Snap` (24-33) with `match_id`, `sender_id`, `media_url`, `view_mode` (default `single_view`), `viewed_at`, `expires_at`, `screenshot_detected`.

## `/home/bishal-regmi/Desktop/Milan/backend/app/sockets/chat_events.py` (108 lines)

Module state: `_room_last_typing: dict[str, float]` (7) and `TYPING_DEBOUNCE_SECONDS = 2.0` (8). Imports are only `time`, `flask.request`, and `app.extensions.socketio` (1-5).

`register_chat_events(io)` (11-32) registers three handlers:
- `chat:join` (12-24) — reads `match_id`, authorizes via `_authorized_for_match(token, match_id)` using `request.args["token"]` or `data["token"]`, then `join_room(f"match:{match_id}")`. Returns `{"ok": True/False}`. The `decode_token` import at line 16 is dead — `_authorized_for_match` does its own decoding.
- `chat:typing_start` (26-28) and `chat:typing_stop` (30-32) — both delegate to `_emit_typing_authenticated`.

`_emit_typing_authenticated(data, is_typing)` (35-50) — the security-relevant path: sender identity comes from the JWT `sub` claim, never the payload, and the sender must be a participant of the match (docstring 36-38).

There is a latent `NameError` here. Line 47 calls `Match.query.get(match_id)`, but `Match` is never imported at module level and not imported inside this function. The only import of it is the local `from app.models import Match` at line 90, inside `_authorized_for_match`, whose scope does not leak. So every `chat:typing_start` / `chat:typing_stop` event raises `NameError: name 'Match' is not defined` at line 47 before any typing event is emitted:

```python
47→    match = Match.query.get(match_id)
```

Adding `from app.models import Match` inside `_emit_typing_authenticated` (or at module level) fixes it. Both lines 47 and 93 also use the legacy `Query.get()` API, which is deprecated in SQLAlchemy 2.0 in favor of `db.session.get(Match, match_id)` — the pattern the saathi blueprint already uses.

Remaining functions:
- `_decode_claims(token)` (53-61) — lazy `decode_token`, returns `None` on any exception.
- `_emit_typing(data, is_typing)` (64-78) — per-`match_id:user_id` debounce; a `typing=True` within 2.0s of the last emit is dropped, then emits `chat:typing` with `{match_id, user_id, typing}` to room `match:<id>`. Note the debounce dictionary grows unbounded and is per-process, so it is not shared across workers.
- `_authorized_for_match(token, match_id)` (81-94) — returns `False` on missing/invalid token, otherwise `True` only when the `sub` claim matches `user_a_id` or `user_b_id`.
- `broadcast_message(match_id, payload)` (97-98) — server-side emit of `chat:message` into the match room; this is what `send_selfie` calls at saathi `__init__.py:1352-1358`.
- `broadcast_typing(match_id, user_id, is_typing)` (101-107) — server-initiated typing bubble so AI companion threads look identical to human threads (§14). Unlike `_emit_typing`, it bypasses the debounce.

Registered at `/home/bishal-regmi/Desktop/Milan/backend/app/__init__.py:78`, after `socketio.init_app(..., async_mode="threading")` at line 77, alongside `register_presence_events` and `register_audio_room_events`.

## `/home/bishal-regmi/Desktop/Milan/backend/app/extensions.py`

Extension singletons at lines 10-16: `db`, `migrate`, `jwt`, `socketio`, `cors`, `limiter` (keyed by `get_remote_address`), and `cache = None`.

`celery_app` (18-24) is `Celery("milan")` with `include=` the five task modules: `media_tasks`, `moderation_tasks`, `notification_tasks`, `matching_tasks`, `verification_tasks`.

`init_celery(app)` (27-82) sets JSON serialization, `timezone="Asia/Kathmandu"`, `enable_utc=True`, and installs a `ContextTask` subclass (76-81) that wraps every `run` in `app.app_context()`.

Beat schedule (lines 40-73) — the comment at 36-39 notes these were dead code until the `milan-beat` systemd service started running `celery beat`. All eight entries point into `app.tasks.notification_tasks`, and I verified each task name exists there:

| Lines | Schedule key | Task | Interval | Task def |
|---|---|---|---|---|
| 41-44 | `saathi-proactive-check` | `saathi_proactive_check` | `3600.0` (hourly, §4.4) | notification_tasks.py:93 |
| 45-48 | `saathi-status-posts` | `saathi_status_posts` | `60*60*5.5` = 19800s (~3x/day within tier caps) | :179 |
| 49-52 | `saathi-open-loop-followup` | `saathi_open_loop_followup` | `60*60*26` = 93600s (daily sweep at drifting hours) | :249 |
| 53-56 | `saathi-mood-decay` | `saathi_mood_decay` | `60*60*24` = 86400s | :225 |
| 57-60 | `saathi-persona-evolution` | `saathi_persona_evolution` | 86400s (§13.3 nightly evolution) | :326 |
| 61-64 | `saathi-nightly-diary` | `saathi_nightly_diary` | 86400s (diary after 21:00 NPT) | :368 |
| 65-68 | `saathi-quests-refresh` | `saathi_quests_refresh` | 93600s (duo quests + anniversary capsules) | :401 |
| 69-72 | `send-scheduled-notifications` | `send_scheduled_notifications` | `300.0` (every 5 min, predicted send times) | :27 |

All schedules are plain float intervals rather than `crontab` entries, so the "nightly" and "after 21:00 NPT" jobs drift relative to wall-clock time and rely on the task bodies to enforce time-of-day windows.

`dispatch(task, *args, **kwargs) -> bool` (85-100) is the fire-and-forget wrapper used from request handlers. It sets `broker_connection_timeout = 1` and `task_publish_retry_policy = {"max_retries": 0}` on every call (mutating global config, line 92-93), calls `task.delay(...)`, and returns `True`. Any exception — kombu/redis connection errors in dev without Redis, or a brief outage — is swallowed at 96-99 with a `logging.warning("broker unavailable; skipped task %s (%s)")` and returns `False`, so the API response always goes out. The tradeoff is that dropped tasks are silent to the caller unless the return value is checked.

The file appears longer than my first read showed — re-reading it in full to get accurate line numbers.

The chat thread file differs between my two reads — re-reading in full to report accurate line numbers.

I explored the Flutter app exhaustively: every file under `/home/bishal-regmi/Desktop/Milan/mobile/lib` that touches chat, realtime, theming, or AI wording was read in full (not just grepped), plus the backend contracts those clients depend on (`chat`, `matching`, `saathi` blueprints, `sockets/`, `utils/serializers.py`) and the four test files. The inventories below are complete for the `lib` tree — no further searching should be needed.

## 1. App bootstrap and shell

- `/home/bishal-regmi/Desktop/Milan/mobile/lib/main.dart:6-8` — `runApp(ProviderScope(child: MilanApp()))`, nothing else.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/app.dart:20-22` — `AppLifecycleListener(onResume: …ensureConnected())` re-opens the socket on resume; `:32-43` builds `MaterialApp.router` from `routerProvider`, `themeMode: ThemeMode.system`, EN/NE localization delegates.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/app.dart:47-49` — `GoRouterX.pushNamed` extension that actually calls `go()` (a `push` that replaces; misleading name, unused in chat).

`MainShell` (`/home/bishal-regmi/Desktop/Milan/mobile/lib/shared/widgets/main_shell.dart`):
- `:12-17` four destinations: Discover / Jhalak / Chat / Profile.
- `:22-23` comment states the Saathi FAB was deliberately removed because "companions now live in the Chat tab (unified inbox, §14)".
- `:26-40` `NavigationBar` driven by `shell.currentIndex`; `goBranch(i, initialLocation: i == shell.currentIndex)` gives tap-to-reset-to-root behavior. `indicatorColor: milan.marigold100`, selected icon `milan.marigold700`.
- No FAB, no badge, no unread count in the shell.

Router (`/home/bishal-regmi/Desktop/Milan/mobile/lib/app/router.dart`):
- `:28-33` plain `GoRouter`, `initialLocation: '/splash'`, `debugLogDiagnostics: false`, **no `redirect`/auth guard at all** — every route is reachable without a session.
- `:82-151` `StatefulShellRoute.indexedStack` with 4 branches. Chat branch `:121-146`: `/chat` → `MatchesInboxScreen`, `/chat/:matchId` → `ChatThreadScreen`, plus `snap-camera`, `theme`, `voice-note`, `share-date`, `video-call`, `voice-call`.
- `:153-179` Saathi routes live **outside** the shell (full-screen): `/saathi/intro`, `/saathi/characters` → `SaathiGalleryRouteScreen`, `/saathi/characters/:characterId`, `/saathi/chat/:characterId` → `SaathiChatScreen`, `/saathi/chat/:characterId/theme`, `/saathi/chat/:characterId/voice`, `/saathi/settings?character=`, `/saathi/debrief/:matchId`, `/saathi/memory?session=`.
- `:81` comment still says "4 tabs + Saathi FAB", contradicting `main_shell.dart:22-23`.
- Router gaps I confirmed by grep: `appearance_screen.dart` is imported at `:23` but **no `/settings/appearance` route exists**, while `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/profile/presentation/screens/my_profile_screen.dart:171-172` pushes `'/settings/appearance'` → that tap hits GoRouter's error page. Same for `ChatThemeStudioScreen` (screen 67 — `:203` is a bare comment with no route) and `SnapViewerScreen` (`chat_extra_screens.dart:149`, never routed).

## 2. api_client

`/home/bishal-regmi/Desktop/Milan/mobile/lib/core/network/api_client.dart`

- `:7-25` `AppException(code, message, statusCode)` with `displayMessage` humanizing the code when the backend sends no message.
- `:30-39` Dio base options; base URL from `--dart-define=MILAN_API_BASE_URL`, defaulting to `https://milanapi.pukarphulara.com.np/api/v1`; 12s connect / 20s receive.
- `:40-47` request interceptor attaches `Authorization: Bearer <access>` from `SecureStorage`.
- `:48-65` 401 handling: `extra['milan_retried']` guard prevents refresh loops; on success it retries, on failure it calls `_expireSession()`.
- `:75-82` two listener lists — `onTokenRefreshed` and `onSessionExpired` — the seam that avoids a circular dep with the socket and auth providers.
- `:89-109` single-flight refresh: concurrent 401s await the same future (`_refreshing`).
- `:111-128` `POST /auth/refresh` on a **separate bare Dio instance** with `Authorization: Bearer <refresh>` (documented backend contract), saves the new access token, fires `_tokenRefreshedListeners`.
- `:131-136` `_expireSession()` clears tokens then fires `_sessionExpiredListeners`.
- `:145-162` `mapError` pulls `error`/`message` out of the response body.
- `:164-198` `get/post/put/delete` all wrap in `mapError`. `:201-217` `uploadMultipart` (photo/audio/video/wallpaper). `:220-221` `testAdapter` seam.
- `:224-226` `apiClientProvider`.

## 3. websocket_client

`/home/bishal-regmi/Desktop/Milan/mobile/lib/core/network/websocket_client.dart`

- `:20-24` state: `_token`, `_socket`, `_wantConnected`, `_listeners` (event → list of handlers), `_joinedMatches`.
- `:30-34` `authToken` setter reconnects when the token changes while connected.
- `:36-47` `connect()` refuses to open with an empty token; `ensureConnected()` is the resume path.
- `:56-75` `_open()` builds the socket with `setTransports(['websocket'])`, **`setAuth({'token': _token})`**, `enableReconnection()`; on connect it calls `_rejoinRooms()` and re-registers all stacked listeners.
- `:77-81` `_rejoinRooms()` re-emits `chat:join` with `{match_id, token}` for every remembered match.
- `:85-93` `on`/`off` stack handlers so thread + inbox can both listen to `chat:message`.
- `:99-103` `joinMatchRoom`; `:110-114` `typingStart`/`typingStop` emit `chat:typing_start` / `chat:typing_stop` with `{match_id, user_id}` — **no token in the payload**.
- `:116-126` `disconnect()` / `clearSession()`.
- `:129-146` provider wires `api.onTokenRefreshed → client.authToken` and `api.onSessionExpired → clearSession + disconnect`; WS URL from `MILAN_WS_URL`, default `https://milanapi.pukarphulara.com.np`.

Contract mismatch worth flagging (verified in backend source, not at runtime): the server authenticates typing off `request.args.get("token") or data["token"]` (`/home/bishal-regmi/Desktop/Milan/backend/app/sockets/chat_events.py:39`) and presence off `request.args.get("token")` only (`/home/bishal-regmi/Desktop/Milan/backend/app/sockets/presence_events.py:9`). The client passes the token via handshake `auth`, not the query string, and omits it from typing payloads — so `chat:typing_start/stop` and `presence:heartbeat` have no token to find. Separately, `chat_events.py:47` uses `Match.query.get(...)` with no `Match` import in that function or at module level (the import at `:90` is local to `_authorized_for_match`), so an authenticated typing relay would raise `NameError`. `chat:join` is unaffected because the client does send `token` in that payload.

## 4. chat_providers

`/home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/application/chat_providers.dart`

`ChatMessage` `:10-45` — `id, senderId, body?, mediaUrl?, isAiSuggested, createdAt`; `fromJson` `:27-34` reads `is_ai_suggested`; `toCacheRow` `:36-44` maps to the sqflite row.

`MatchSummary` `:47-84` — `:56-69` `kind` ('human' | 'companion') with the comment "used ONLY for the AI badge; the row and the chat screen it opens are identical (§14)". `fromJson` `:71-83`: name from `user.display_name` (fallback `'Milan user'`), `unread`/`unreadCount` from `unread_count`, `kind` from `json['kind']`, and `isAi: (user?['is_ai'] as bool?) ?? json['kind'] == 'companion'`. **`last_message` is never parsed** even though `/home/bishal-regmi/Desktop/Milan/backend/app/utils/serializers.py:123` returns it — so `lastMessage` is permanently null and the inbox subtitle always falls back to `'Say namaste 👋'`.

`MatchesController` `:86-107` — `GET /matches`, invalidates itself on every `chat:message`, swallows `AppException` into an empty list (an error state the inbox can never show).

`ChatThreadController` `:109-235`:
- `:112-131` `build`: `ws.joinMatchRoom(matchId)`, registers a `chat:message` handler that filters on `match_id`, appends, and caches to sqflite. The socket-built `ChatMessage` at `:119-125` **drops `media_url` and `is_ai_suggested`** — an inbound image arrives as an empty-text bubble.
- `:132-142` cache-first: if sqflite has rows it returns them and **never fetches the server**, so a thread hydrated once only grows via socket/optimistic appends.
- `:143-147` cold path `GET /matches/:id/messages`.
- `:153-163` `_append` dedups by server id (socket echo vs optimistic).
- `:165-203` `send(body, {regenerateVariant})` → `POST /matches/:id/messages`; optimistic append; then the companion path: `:184` reads `res['companion_reply']`, `:186-189` clamps `typing_delay_seconds` to `0.0…4.0` s, `:190-192` awaits it, `:193-202` appends each entry of `reply['messages']`. It does **not** read `read_delay_seconds`, `delayed_reply`, or `degraded`, all of which the backend returns (`/home/bishal-regmi/Desktop/Milan/backend/app/blueprints/chat/__init__.py:186-192`).
- `:207-219` `sendMedia`; `:221-231` `icebreakers()` → `POST /matches/:id/icebreakers`, returns `const []` on failure.

`PresenceController` `:237-266` — listens to `presence:update`, stores `{userId: PresenceState(online)}`, exposes `heartbeat(userId)` emitting `presence:heartbeat`. **Dead code in the UI:** `presenceProvider` has zero watchers and `heartbeat` has zero callers anywhere in `lib`.

`ChatTypingController` `:270-289` — family-by-`matchId` bool; `:277` filters foreign matches, `:278` ignores self-echo by comparing `data['user_id']` to `currentUserIdProvider`, `:279` sets `state = data['typing']`. There is **no auto-expiry timer**, so a missed `typing:false` leaves the bubble up indefinitely.

## 5. chat_thread_screen

`/home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/presentation/screens/chat_thread_screen.dart` (470 lines)

- `:43` theme scope `ChatThemeScopeKey.match(matchId)`.
- `:46-63` `initState`: registers the composer in `ComposerRegistry`, post-frame `_jumpToBottom()`, and fire-and-forget `POST /matches/:id/read` + `invalidate(matchesProvider)`.
- `:65-82` `_jumpToBottom` / `_maybeScrollToBottom(count)` — animates only when the message count grows.
- `:93-123` typing emission: first keystroke emits `typingStart`, a 2s `Timer` re-armed on each change calls `_stopTyping`, empty text stops immediately, `dispose` `:84-91` also stops.
- `:127-141` build reads `chatThreadProvider`, `themeProvider(scope)`, `currentUserIdProvider`, `chatTypingProvider`, and `matchesProvider` (linear scan `:138-141` to find the peer).
- `:135` `showTyping = peerTyping && !Motion.prefersReducedMotion(context)` — reduced-motion suppresses the indicator entirely rather than showing a static form.
- `:143-177` AppBar: avatar + `peer?.otherName` only (no presence line, no AI badge, no chip — the "· AI" suffix arrives inside the name from the server), Report action, and a `PopupMenuButton` whose only item is "Chat theme".
- `:178-181` background from `resolveWallpaperDecoration(resolved, …)`.
- `:190-228` list: `itemCount = list.length + (showTyping ? 1 : 0)`, typing row at the tail returns `const TypingBubble()` `:198`; media-only messages render as a bare `Image.network` `:204-217` (no bubble, no timestamp, no `key` on the ChatBubble path variance); text messages → `ChatBubble` `:219-226` with `isSent`, `isAi: m.isAiSuggested`, `bubbleShape`, `timestamp`. `read` is never passed, so the `done_all` receipt in `ChatBubble` is unreachable from this screen.
- `:232` `if (resolved.textScale != null) SizedBox(height: Spacing.xs)` — `textScale` is otherwise never applied to message text.
- `:239-256` leading composer button is companion-aware: `peer?.isAi` swaps `Icons.photo_outlined`/tooltip "Send photo" for `Icons.auto_awesome_outlined`/tooltip **"Ask for a moment"** → `_requestCompanionMoment`.
- `:257-278` TextField (`hintText: 'Type a message'`, hardcoded `0xFFF1F3F6` fill) calling `_onComposerChanged` + `setState` on every keystroke; `:280-286` mic → `/chat/:id/voice-note`; `:287-295` send FAB tinted by `accentThemeProvider`.
- `:305-349` `_requestCompanionMoment`: resolves the companion by **prefix-matching `peer.otherName` against roster names** (`:320-322`), `POST /saathi/:key/sessions`, `POST /saathi/sessions/:id/selfie`, waits `typing_delay_seconds` (default 2.0 s, unclamped) `:332-334`, invalidates the thread, and snackbars `res['ai_label'] ?? 'AI-illustrated moment'` `:339-341`.
- `:352-372` `_sendGalleryImage` (upload → `sendMedia` → `Sfx.messageSent`); `:374-381` `_send`; `:383-393` `_openThemeSheet` → `ThemePickerSheet(scope:)`.
- `:396-453` `_IcebreakerRow` — loads only when the thread has ≤2 messages (`:419`), renders `ActionChip`s with an **`avatar: Text('AI')`** `:443`, tap inserts into the composer, never auto-sends.
- `:458-470` `composerProvider` / `ComposerRegistry` broadcast-set of `TextEditingController`s.
- Minor: `:127` `final milan = …MilanColors…` is unused, and `:16` imports `typing_indicator.dart` which this screen never uses (it uses `TypingBubble` from `chat_bubble.dart`).

## 6. chat_bubble

`/home/bishal-regmi/Desktop/Milan/mobile/lib/shared/widgets/chat_bubble.dart`

- `:10-15` doc comment: "AI-labelled variant keeps a dashed disclosure border for the companion surface only — the tag lives in the AppBar, per-message tagging was removed (build brief §2)."
- `:17-38` params `text, isSent, isAi, bubbleColor, bubbleShape, timestamp, read, onTap, accentColor`.
- `:41-42` `defaultAccent = 0xFF0B84FE`, `receivedFill = 0xFFF1F3F6`.
- `:50-54` fill precedence: `isAi ? milan.dhaka100 : (bubbleColor ?? (isSent ? accent : receivedFill))` — **`isAi` overrides any theme-supplied `bubbleColor`**, which is why the Saathi screen's `bubbleColorReceived` (`saathi_chat_screen.dart:120-122`) never shows on AI bubbles.
- `:55` text color is white when sent, `ink900` otherwise (a light user accent makes sent text unreadable; no contrast check here).
- `:58-70` Messenger asymmetric radii (4 px on the sender-side corner).
- `:85-87` the AI marker is a **solid** `Border.all(color: milan.dhaka500)` — despite the "dashed" comment there is no dash painter, and no "AI"/"SUGGESTED" text anywhere in the widget.
- `:97-107` in-bubble timestamp + `done_all` only when `isSent && read`; `:115-124` long-press opens a timestamp sheet; `:126-127` `_format` is raw 24-hour `HH:mm`.
- `SnapBubble` `:131-168`; `TypingBubble` `:171-193` (received-side pill, `receivedFill`, asymmetric radii, wraps `TypingDots`); `TypingDots` `:195-234` — 1100 ms repeat, opacity-stepped 8 px dots in `0xFF8A919C`, and **it does not consult `Motion.prefersReducedMotion`** (the caller gates it instead).

Test drift: `/home/bishal-regmi/Desktop/Milan/mobile/test/chat_theme_test.dart:104-108` still asserts `find.text('AI')` and `find.text('SUGGESTED')` for `isAi: true`; the current `ChatBubble` renders neither, so that widget test cannot pass.

## 7. typing_indicator

`/home/bishal-regmi/Desktop/Milan/mobile/lib/shared/widgets/typing_indicator.dart`

- `:6-14` `TypingIndicator({color = 0xFF7B1E3A, loop = Motion.saathiTypingPulse})` — doc line `:5` says "shared by match chat and Saathi chat", but in practice only `saathi_chat_screen.dart:103` uses it; the match thread uses `TypingBubble`.
- `:22-23` single `AnimationController(duration: loop)..repeat()`.
- `:36-51` three `CircleAvatar(radius: 3)` dots; `:39` phase `(_controller.value * 3 - i).clamp(0,1)`; `:40-42` respects `Motion.prefersReducedMotion` by zeroing the 4 px lift (so it degrades to static dots rather than disappearing — the opposite policy from `TypingDots`).
- Timing source: `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/motion_tokens.dart:8` `saathiTypingPulse = 1200 ms`.

## 8. Every AI / companion / saathi / practice string, badge, and "· AI" suffix in the UI

Chat surfaces
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/presentation/screens/matches_inbox_screen.dart:14-15` doc "AI companions render identically to humans with the single AI badge (§14)"; `:40` `tooltip: 'AI companions'`; `:41` `Icon(Icons.auto_awesome)` header action → `:42` `context.push('/saathi/intro')`; `:121-132` the **only inbox badge**: `if (match.isAi)` a white circular chip with `Icons.smart_toy_outlined` size 13 in `milan.dhaka500` at the avatar's bottom-right; `:156-157` comment + `onTap` proving companions open the same `/chat/:matchId`.
- `chat_thread_screen.dart:246-255` `Icons.auto_awesome_outlined` + tooltip "Ask for a moment" when `peer.isAi`; `:340` snackbar fallback `'AI-illustrated moment'`; `:396` doc "Screen 30 — AI icebreaker suggestions"; `:443` `avatar: const Text('AI', style: TextStyle(fontSize: 10))` on every icebreaker chip.
- `chat_thread_screen.dart:157` the AppBar name — the `· AI` suffix is server-appended (`/home/bishal-regmi/Desktop/Milan/backend/app/utils/serializers.py:89-92`), so it renders here without any client-side string.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/shared/widgets/chat_bubble.dart:13-14` doc; `:52` / `:85-87` the AI fill + border (visual badge, no text).

Saathi chat screen
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/saathi/presentation/screens/saathi_chat_screen.dart:16-17` doc "AI-labeled everywhere"; `:57-58` comment "server-provided display name already carries the '· AI' tag"; `:59` `Text(characterDisplayName ?? 'Saathi')`; `:62-70` the boxed **`'AI'`** badge (`milan.dhaka500` border, 10 px w700); `:86` and `:155` `"Milan's AI is taking a breather — try again shortly."`; `:111` comment; `:165` `hintText: 'Practice a conversation...'`; `:241-254` `SaathiCharacterGalleryScreen` with hardcoded roster and `AppBar(title: 'Choose your practice companion')` plus per-character "practice" copy at `:245-248` — **this screen is not routed anywhere**, `/saathi/characters` maps to `SaathiGalleryRouteScreen`.

Saathi extra screens
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/saathi/presentation/screens/saathi_extra_screens.dart:92` `Icons.auto_awesome` hero; `:94` `l10n.saathiConsentBody`; `:101-106` "Saathi IS" / "A place to practice openers, banter and date debriefs." / "Saathi IS NOT" / "A real person…"; `:112` "I confirm I am 18 or older"; `:143` `AppBar('Choose a companion')`; `:146` "Could not load companions. Pull to retry."; `:151` "No companions available yet."; `:194-214` per-card badge — `'PASS'` when locked, otherwise the boxed **`'AI'`** chip; `:239` comment "practice-only companion without a match"; `:272-273` `Chip('AI · practice companion')`; `:321` `Icons.auto_awesome` call avatar; `:332` `Text('Saathi · AI companion')`; `:361` `AppBar('Saathi settings')`; `:365` "Could not load Saathi settings…"; `:370`/`:378` localized proactive + pause labels; `:395` "Could not save Saathi settings (code)"; `:455` `'Chat theme · this Saathi character'`.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/saathi/presentation/screens/saathi_memory_screen.dart:9-10` doc; `:57` `saathiMemoryTitle`; `:67` `saathiMemoryClearAll`.

Saathi provider defaults (these are the "· AI" name suffixes on the client)
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/saathi/application/saathi_session_provider.dart:53` `characterDisplayName = 'Saathi · AI'` (constructor default) and `:143` `res['character_name'] as String? ?? 'Saathi · AI'` (DTO fallback); `:32` `isAi => role == 'saathi'`; `:141` `isAiCharacter: res['is_ai'] ?? true`; `:169` comment; `:290-291` "§14 companion roster" doc.

Shared widgets / theme
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/shared/widgets/common.dart:181` doc "Saathi character gallery card"; `:234-243` `AICharacterCard` badge — `Chip('Pass')` with a lock when locked, else `Chip('AI', fontSize: 10)`.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/shared/widgets/theme_picker_sheet.dart:75-76` `Icons.auto_awesome` for Saathi scope; `:82` `'Applying to: this Saathi character'`; `:157` `'Saathi': MilanChatPresets.saathi` tab pack.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/chat_theme_presets.dart:182-229` four visible preset names `'Saathi — Asha' | 'Bibek' | 'Priya' | 'Sagar'`; `:335-336` their shared wallpaper color.

Other features
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/onboarding/presentation/screens/interview_screen.dart:113-118` interview questions render as `ChatBubble(isAi: true, bubbleColor: milan.dhaka100)` — AI-styled bubbles with no text label.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/onboarding/presentation/screens/onboarding_screens.dart:517` "optional Saathi check-ins"; `:523` sample push row **`'Saathi practice nudge'`**.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/discovery/presentation/screens/discovery_extra_screens.dart:222` `Icons.auto_awesome`; `:232` `'AI-generated · grounded in shared profile signal'`; `:320` `"Milan's AI is taking a breather."`; `:386` `'AI-generated cultural reading · for fun'`.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/profile/presentation/screens/profile_edit_screens.dart:216` `tooltip: 'Get AI feedback'`; `:286` degraded copy; `:297` `AppBar('AI Bio Assistant')`; `:303`/`:323` `Icons.auto_awesome`; `:320` `'AI DRAFT'`; `:394` `'AI feedback'`.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/settings/presentation/screens/settings_screens.dart:184` "Saathi proactive messages also respect these caps."; `:311-313` plan bullets `'1 AI companion'`, `'4 AI companions'`, `'8 companions & voice'`; `:561` FAQ "Is Saathi a real person?" / "No — Saathi is clearly-labeled AI for practice only."
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/profile/application/tier_provider.dart:7` comment only.

Localization (EN / NE / ARB — `chatAiLabel` and `saathiHeaderTag` are defined but **never referenced by any widget**)
- EN: `/home/bishal-regmi/Desktop/Milan/mobile/lib/core/localization/app_localizations_en.dart:27` `'Saathi AI'`, `:181` `chatAiLabel => 'AI'`, `:184` `saathiHeaderTag => 'Saathi · AI companion'`, `:186` `'Meet Saathi'`, `:189-191` consent body with "practice", `:193` 18+, `:196` "Let Saathi message me first", `:199` "Pause Saathi", `:202` "What Saathi Remembers", `:205` "Clear all", `:232-233` `aiUnavailable`.
- NE: `/home/bishal-regmi/Desktop/Milan/mobile/lib/core/localization/app_localizations_ne.dart:27` `'साथी एआई'`, `:184` `'एआई'`, `:187` `'साथी · एआई साथ'`, `:190`, `:193`, `:197`, `:200`, `:203`, `:206`, `:236`.
- Abstract doc-comments: `/home/bishal-regmi/Desktop/Milan/mobile/lib/core/localization/app_localizations.dart:134, 434, 440, 452, 536`.
- ARB sources: `app_en.arb:8, 58-66, 75`; `app_ne.arb:58-59, 75`.

Identifier-level (non-UI but AI-coupled): `chat_providers.dart:16,24,32,42,56,66,69,80-81,139`; `local_db.dart:30` (`is_ai_suggested` column); `chat_theme_tokens.dart:11` (`WallpaperType.aiGenerated`), `:15,27-28,40-41`; `theme_provider.dart:64-66,71-83,93-97,127-130,165-166,177-181`.

## 9. Every consumption point for reply timing / typing / segments / presence

Reply timing (`typing_delay_seconds`)
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/application/chat_providers.dart:186-192` — `companion_reply.typing_delay_seconds`, default `0.0`, clamped `0.0…4.0`, awaited before appending segments.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/saathi/application/saathi_session_provider.dart:184-187` — message reply delay, default `1.2`, clamped `0.8…4.0`, always awaited.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/presentation/screens/chat_thread_screen.dart:332-334` — selfie/"moment" delay, default `2.0`, **not clamped**.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/motion_tokens.dart:29-32` `saathiTypingDelay(charCount)` (chars/14, clamped 0.8–4.0 s) — **zero call sites**; the server value is used instead.
- Not consumed anywhere in `lib`: `read_delay_seconds`, `delayed_reply`, `degraded` from `companion_reply`.

Segments
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/saathi/application/saathi_session_provider.dart:189-197` — `res['segments'] ?? [res['reply']]`, each becomes its own `SaathiMessageItem(role: 'saathi')`.
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/application/chat_providers.dart:193-202` — the unified-thread equivalent iterates `companion_reply['messages']` (already one persisted `Message` per segment server-side, `/home/bishal-regmi/Desktop/Milan/backend/app/blueprints/chat/__init__.py:151-176`); the client never sees the raw `segments` key on this path.
- `loadHistory` (`saathi_session_provider.dart:239-256`) ignores the per-message `segments` the backend returns at `/home/bishal-regmi/Desktop/Milan/backend/app/blueprints/saathi/__init__.py:412` and uses `content` only.
- Every other `segments:` hit in `lib` is an unrelated `SegmentedButton` (`onboarding_screens.dart:198`, `theme_picker_sheet.dart:435`, `profile_edit_screens.dart:104`, `chat_theme_studio_screen.dart:100`).

Typing
- Emit: `chat_thread_screen.dart:95-123` → `websocket_client.dart:110-114`.
- Receive: `chat_providers.dart:270-289` (`chat:typing`) → consumed at `chat_thread_screen.dart:133-135` → renders `TypingBubble` at `:195-198`.
- Local-only typing flag on the Saathi screen: `saathi_chat_screen.dart:28`, `:52`, `:96-106` (renders `TypingIndicator(color: milan.dhaka500)`), `:225-235` (`_typing` set around the send call, also used as a send lock).
- Server-driven typing for companions in the unified thread comes from `broadcast_typing` (`/home/bishal-regmi/Desktop/Milan/backend/app/sockets/chat_events.py:101-108`), consumed by the same `chatTypingProvider`.

Presence
- Real-time: `chat_providers.dart:237-266` — `presence:update` handler and `presence:heartbeat` emitter, **both unconsumed by any widget**. No presence text appears in the match thread AppBar.
- Companion presence (REST, not socket): `saathi_session_provider.dart:50-51`, `:71-72`, `:101-102`, `:119-120`, `:128`, `:139-140` parse `presence.activity` / `presence.state`; the only place they are rendered is the Saathi bond HUD, `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/saathi/presentation/screens/saathi_chat_screen.dart:191-197` (shows `presenceActivity` when state is `'busy'`, else the raw state string).

## 10. Notable inconsistencies found (reported, not changed)

1. `MatchSummary` never parses `last_message`, so every inbox row shows `'Say namaste 👋'` (`chat_providers.dart:71-83` vs `matches_inbox_screen.dart:139`).
2. Socket messages lose `media_url` / `is_ai_suggested` (`chat_providers.dart:119-125`); thread hydration is cache-only once sqflite has rows (`:132-142`).
3. `chat_theme_test.dart:104-108` asserts `'AI'` + `'SUGGESTED'` text that `ChatBubble` no longer renders.
4. Typing/presence socket payloads carry no token while the server looks for one in the query string or payload; `chat_events.py:47` also references `Match` without an in-scope import.
5. `presenceProvider`, `PresenceController.heartbeat`, and `saathiTypingDelay` are dead; `chat_thread_screen.dart:16` imports `typing_indicator.dart` unused; `:127` declares an unused `milan`.
6. `AppearanceScreen`, `ChatThemeStudioScreen`, `SnapViewerScreen`, and `SaathiCharacterGalleryScreen` (the "Choose your practice companion" copy) exist without routes; `my_profile_screen.dart:171-172` pushes the missing `/settings/appearance`.
7. `ChatBubble`'s `isAi` fill (`:52`) overrides theme bubble colors, and the "dashed" border in its doc comment is actually solid (`:85-87`).
8. `l10n.chatAiLabel` and `l10n.saathiHeaderTag` are defined in EN/NE but every AI badge in the UI is a hardcoded `'AI'` literal instead.
9. Router has no auth redirect, so `/chat/...` and all Saathi routes are reachable unauthenticated (requests then fail at the 401 interceptor).

I've now read the full companion stack. Before the plan, one correction on the disclosure decision.

## The one line I won't build

You chose "fully human, never admits AI." I'll build everything else — first-person life, no helper framing, no `· AI` suffix in chat, real texting voice, autonomous messaging — but I won't make her **deny being AI when a user sincerely asks**. Two reasons, both from your own files: `07_milan_ai_girlfriend_realism_and_innovation_masterplan.md` §2.3 documents that persistent disclosure is now hard law in your target distribution markets (CA SB 243, EU AI Act Art. 50 from Aug 2026) and a Play Store policy requirement, and the Character.AI settlements it cites were precisely about deceived users. An app that lies about this is a takedown/liability risk, not a feature.

What you get instead, and it covers ~99% of real chat turns: she never volunteers it, never breaks character for flavour questions ("k gardai xau?" → "college bata aayeko, thakeko 😩"), has no AI wording anywhere in chat, inbox, or display name — and answers truthfully only on a direct sincere "are you a real person / is this a bot". Disclosure lives on the profile screen and in ToS.

Now the plan.

Understood — waiting for your next prompt. I'll research it, fold it into the plan, and implement directly without asking for review.

Meanwhile, here's where things stand:

**Plan is written** at [08_companion_realism_transformation_plan.md](file:///home/bishal-regmi/Desktop/Milan/08_companion_realism_transformation_plan.md).

**Root cause confirmed from your screenshot:** Priya is one of four characters wired to the *coach* prompt template whose opening line is literally "help the user practice conversation, build dating confidence" ([groq_service.py#L77-L112](file:///home/bishal-regmi/Desktop/Milan/backend/app/services/groq_service.py#L77-L112)). That path also skips the language block, persona block and lorebook entirely — which is why she answered your roman-Nepali `timro name k ho` in English, then switched to formal Devanagari `तपाईंलाई`. Nothing in the codebase tracks the user's script or register today.

**Also blocking realism, found while researching:**
- Typing bubbles never fire for anyone — `chat_events.py:47` references `Match` with no import in scope, so every typing event raises `NameError`.
- Presence is computed for the UI but never reaches reply timing; `reply_timing(reply, "free")` is hardcoded.
- Auto-texts write only to `SaathiMessage`, never the unified `Message` thread, so "she texts first" is invisible in the inbox.
- Free tier is capped at 0 companions and 0 auto-texts, which is exactly why you got funnelled to a coach.

Send the next prompt whenever you're ready.

---

**User**

continue all old firstand then why all character talk inpure english , chat suggestions donot auto enter in input field, typing animation always appear in ai character chat  in header character name donot appears as real user , in home swiping flash card name appeared as milan user what it is , and in characters list make as column list not grid all text of it should be visible or make profile section andthen what if auto messaging time totime , notifications works or not just like  how real person texts himself remembers what he last conversation everything and also send message delay appearing in chat area and redesign chat ui like facebook messanger search desigjn    and allow user to selectapp not not always grey like color let user select and can edit and also  can customize later default is white proper like in this messager screen white proper ui ux white blue color combination of our app/web theme, send image send voice not working check for both user and agent chats everyhting i said do for all whole app consider full system wide think , dont fix time to send message by character dont hardcode use proper algorithms  proper activeoffline status of usesrs should be shown see messager ui i gave to you refine app theme  ui ux similar to it  and payment method link screen currently is useless ( coming soon point it )   and learn from this app also     /home/bishal-regmi/Downloads/dobato-main (1)/dobato-main see features user profile data onboarding how much data it take explore its all screen all data models everything and import implement our missing features from learning from it and very lag slow speed image loading and also progressbar/skelatanloading  for loading not shown   and font size theme ui ux pattern learn form this messanger chat ui implement global wide  and why location needed says while onboarding but dont asks pemission not uses why this type mock implement everything mock use edit tool to edit not terminal to edit code [$ui-ux-design-pro](/home/bishal-regmi/.zcode/skills/ui-ux-design-pro/SKILL.md)   finish all old tasks first use edit tool not terminal to edit codes and while onboarding user enter tell us what you are looking for various questions he answer where are they used ? arey they stored or not ? is user signup stored or not properly ? our lots of ai algorithms  should be implemented based on user activities check properly and what user profile screen visible to other and him donot show these  add some demo jhalaks where i will see some   match expiry features    make sure all done ui ux is upgraded properly   all ui ux screens are redesigned all widgets components theme everything  how is matching done how will user sees who sees his profile ? how will match request seen ? is there any screens how messages sent to users first ? what is flow ? is all required screens navigations logics implemented and for showing users search screen also implement in home screen flash cards how list will get which will be first ? is there ai algorithms based on user intrest any choices his datathat we have make proper ai algorithms data first ai used for optimisation context formation everything think research deeper and complement implementation  and why ai characters dont have profile images they should have ( genrate image with ai fix prompt for all facial expression seen full face structure keep it safe when in chatwith user if user askd to send image ? whatwill it send it should use that exactface prompt for genrating various images and sending (but not directly in one request behave like real human ))  think deeper implement everything and also let us consider one situation  talking morning user a says ai i am going to visit pashupati and will talk touhh at night then whatif user a dont messaged ? ai should send trigger messages at middle also (let ai decide user behave  ) send how is day gone there full contextshould be known by it proper time detection to send messages should be identified and research more supported groq models to use them cheaper for low energytasks   dont use terminal to write update codes files also language and accessibility setting not working  is notification setting real and working ?   and add demo qrs in payment methods so i can test   also similar like messanger add notifications sounds, messanges sounds think add sounds everywhere swipe sounds get sound free comersial use allowed ones and use everywhere should be used in many other places also proper vibrations  chats should support giffs , images sending but not videos  and add algoritms to filter rough words   and implement everything from dobato missing in our that we can use    start working make implementation with all full details check first know current state main full ui ux redesign should be done    explore whole try to find issues contract imagination we want all realistic all implemented real working every single features   start working in implementation   start working full ui ux theme system all modification if not done 

**Assistant**

I'll start by researching everything in parallel — the Dobato app you referenced, our current UI/UX state, and the backend gaps you listed.

Enormous scope. Let me research in parallel before touching code.

This is a very large scope. Let me set up the work plan and get full current state first.

Researching current state across four fronts in parallel.

I'll explore that codebase systematically. Let me start with the overall structure.

I'll start by locating the files and reading them in parallel.

Files found. Reading all of them in parallel.

Now let me examine Milan's feature set to determine gaps.

I read every file you listed plus the call sites that consume these tokens, so this inventory is complete for the mobile app's design-system surface — no follow-up searching should be needed.

## Files read

- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/color_tokens.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/type_tokens.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/spacing_tokens.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/motion_tokens.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/accent_theme.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/chat_theme_tokens.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/theme/chat_theme_presets.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/app.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/app/settings/a11y_settings.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/core/feedback/sfx.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/shared/widgets/common.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/shared/widgets/swipe_card.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/personalization/application/theme_provider.dart`
- `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/settings/presentation/screens/appearance_screen.dart`

Supporting reads (needed to answer "how selection works today" and to find every skeleton/sfx consumer): `lib/app/router.dart`, `lib/main.dart`, `lib/shared/widgets/chat_bubble.dart`, `lib/shared/widgets/theme_picker_sheet.dart`, `lib/shared/widgets/typing_indicator.dart`, `lib/shared/widgets/main_shell.dart`, `lib/features/chat/presentation/screens/matches_inbox_screen.dart`, `.../chat_thread_screen.dart`, `.../chat_extra_screens.dart`, `lib/features/discovery/presentation/screens/discover_screen.dart`, `lib/features/saathi/presentation/screens/saathi_chat_screen.dart`, `.../saathi_extra_screens.dart`, `lib/features/settings/presentation/screens/settings_screens.dart`, `lib/features/personalization/presentation/screens/chat_theme_studio_screen.dart`, `lib/features/profile/presentation/screens/my_profile_screen.dart`, `lib/core/storage/local_db.dart`, `pubspec.yaml`, and the four files in `mobile/test/`.

---

# 1. Color tokens

## 1.1 `MilanColors` theme extension — `app/theme/color_tokens.dart`

16 named tokens declared at lines 26–41, with two complete palettes.

| Token | Light (L43–60) | Dark (L62–79) |
|---|---|---|
| `marigold500` | `0xFFF5A623` (L44) | `0xFFDD9520` (L63) |
| `marigold700` | `0xFFC97D0C` (L45) | `0xFFB56F0A` (L64) |
| `marigold100` | `0xFFFDE9C8` (L46) | `0xFF3A2E17` (L65) |
| `dhaka500` | `0xFF7B1E3A` (L47) | `0xFF6E1B34` (L66) |
| `dhaka700` | `0xFF591129` (L48) | `0xFF4F0F26` (L67) |
| `dhaka100` | `0xFFF3DCE2` (L49) | `0xFF3A1A24` (L68) |
| `pine500` | `0xFF1F6F54` (L50) | `0xFF1C644C` (L69) |
| `pine100` | `0xFFDCEFE7` (L51) | `0xFF17352C` (L70) |
| `ink900` | `0xFF1F1B16` (L52) | `0xFFF5F0E6` (L71) |
| `ink600` | `0xFF4A443C` (L53) | `0xFFCFC8BA` (L72) |
| `ink400` | `0xFF8A8377` (L54) | `0xFF948D80` (L73) |
| `paper0` | `0xFFFFFBF5` (L55) | `0xFF161310` (L74) |
| `paper100` | `0xFFF5F0E6` (L56) | `0xFF221E19` (L75) |
| `line200` | `0xFFE8E1D3` (L57) | `0xFF38322A` (L76) |
| `error500` | `0xFFC0392B` (L58) | `0xFFAD3325` (L77) |
| `warning500` | `0xFFB8791A` (L59) | `0xFFA66D17` (L78) |

`copyWith` L82–108, `lerp` L111–131 (all 16 interpolated). Accessed via `context.milan` extension at L205–207.

## 1.2 Material `ColorScheme` mapping — `_schemeFrom`, L134–148

`primary: marigold500` (L137), `onPrimary: ink900` (L138), `secondary: dhaka500` (L139), `onSecondary: Colors.white` (L140), `error: error500` (L141), `onError: Colors.white` (L142), `surface: paper0` (L143), `onSurface: ink900` (L144), `surfaceContainerHighest: paper100` (L145), `outlineVariant: line200` (L146). Notably **no tertiary/`pine500` slot** — pine only reaches Material through direct extension reads.

## 1.3 Component theming — `_baseTheme`, L154–203

- `scaffoldBackgroundColor: paper0` (L159); extension registered L160.
- `AppBarTheme`: bg `paper0`, fg `ink900`, `elevation: 0`, `centerTitle: false` (L161–166).
- `FilledButtonTheme`: `marigold500`/`ink900`, `radiusMd`, `minimumSize: Size(0, 48)` (L167–177). Comment at L172–174 explains the deliberate `Size(0,48)` instead of `Size.fromHeight`.
- `OutlinedButtonTheme`: `dhaka500` fg + border, `radiusMd`, min height 48 (L178–185).
- `InputDecorationTheme`: filled with `paper100`, `line200` borders, `radiusMd` (L186–197).
- `ChipThemeData`: `StadiumBorder` with `line200`, `selectedColor: marigold100` (L198–201).

## 1.4 Off-token hardcoded colors (the Messenger-style chat surface bypasses `MilanColors`)

- `chat_bubble.dart` L41 `defaultAccent = Color(0xFF0B84FE)`; L42 `receivedFill = Color(0xFFF1F3F6)`; L226 typing dot `0xFF8A919C`.
- `matches_inbox_screen.dart` L33/35/36 `Colors.white` scaffold+appbar, L53 search icon `0xFF8A919C`, L55 field fill `0xFFF1F3F6`.
- `chat_thread_screen.dart` L269 composer fill `0xFFF1F3F6`, L283 idle mic `0xFF8A919C`.
- `common.dart` L91 seen-story ring `0xFF8A8377` flat; L92 unseen ring `0xFFF5A623 → 0xFF7B1E3A`; L159 meter track `0x22F5A623`; L167 meter sweep `0xFFF5A623 → 0xFF7B1E3A`; L60 selected-check `0xFFC97D0C`.
- `typing_indicator.dart` L9 default dot color `0xFF7B1E3A`.
- `swipe_card.dart` L94/96 `Colors.grey.shade200`/`shade300` placeholders, L105 `Colors.black54`, L134 `Colors.black45`, L153 `Colors.white30`.
- `main_shell.dart` L32 `indicatorColor: milan.marigold100`, L37 selected icon `marigold700`.

## 1.5 Chat wallpaper / bubble color tokens

`chat_theme_tokens.dart` factory default (L79–85): wallpaper preset `brand_marigold_warm`, sent `0xFFF5A623`, received `0xFFF3DCE2`, shape `rounded`.

`chat_theme_presets.dart` — 17 presets in 5 packs (`all` aggregate L231–237):

- Brand (L23–57): `brand_marigold_warm` preset F5A623/F3DCE2; `brand_dhaka_dusk` gradient `#7B1E3A|#591129`, C97D0C/F3DCE2; `brand_pine_calm` solid `#1F6F54`, 1F6F54/DCEFE7.
- Festival (L59–106): `festival_dashain` B8791A/FDE9C8 + doodle `marigold_petals`; `festival_tihar` C97D0C/FFF3DC + doodle `paisley`; `festival_holi` gradient `#E85D9E|#F5A623`, 7B1E3A/FFFBF5; `festival_teej` gradient `#1F6F54|#59A96A`, 591129/DCEFE7.
- Nature (L108–155): `nature_himalaya` 2B5F8A/EAF2F8 + `mountain_ridge`; `nature_terrace_hills` gradient `#4C7A3F|#A8C686`, 2E5229/F2F7EC; `nature_rhododendron` B33A4B/FBEDEF + `mithila_lines`; `nature_monsoon_cloud` gradient `#43535C|#93A8B4`, 34424A/EDF1F4.
- Minimal (L157–180): `minimal_paper` solid `#FFFBF5`, F5A623/F5F0E6; `minimal_soft_slate` gradient `#F5F0E6|#E8E1D3`, 4A443C/FFFFFF.
- Saathi (L184–229): `saathi_asha` 7B1E3A/F3DCE2; `saathi_bibek` 591129/EFD9DF; `saathi_priya` 8A4A63/F7EBEF; `saathi_sagar` 6E1B34/EADCE1.

Preset background fallback tones, `resolveWallpaperDecoration` L327–338: `brand_marigold_warm → 0xFFFFF3DD`, `festival_dashain → 0xFFFFE9C4`, `festival_tihar → 0xFF31221B`, `nature_himalaya → 0xFFDDEAF4`, `nature_rhododendron → 0xFFFBEDEF`, all four `saathi_* → 0xFFF6E7EC`, default `0xFFF5F0E6` (also the loading placeholder, L342).

Photo wallpaper treatment: base `0xFF221C15` dark / `0xFFF5F0E6` light (L288, L305), image `opacity: dark ? 0.30 : 0.55` (L292, L309), overlay filter `0xAA14100C` / `0x33FFFFFF` in `BlendMode.overlay` (L294).

Dark dimming: `dim(c, keepRatio)` L350–359 with `factor = 0.15 + 0.85 * keep`; default `darkModeBrightness` is `0.25` for gradients (L319–320) and `0.35` for solids (L345).

Doodle overlays L262–267: `paisley` 0.08, `marigold_petals` 0.08, `mountain_ridge` 0.07, `mithila_lines` 0.06.

Contrast gate: `contrastRatio` L162–168, `_relativeLuminance` L170–176, `passesContrast` L178–187 requires ≥ 4.5 for **both** sent and received fills against hardcoded `0xFF1F1B16`.

Picker swatch sets in `theme_picker_sheet.dart`: solids L191 `['#FFFBF5','#F5F0E6','#1F6F54','#7B1E3A','#161310','#43535C']`; gradients L192; sent-bubble swatches L405–408 (F5A623, 7B1E3A, 1F6F54, 43535C, B33A4B, 591129); received swatches L423 (F3DCE2, FDE9C8, DCEFE7).

## 1.6 Accent palette — `accent_theme.dart` L45–51

`kAccentChoices`: Messenger Blue `0xFF0B84FE`, Milan Marigold `0xFFF5A623`, Dhaka Rose `0xFFC2426E`, Pine Green `0xFF1F8F62`, Royal Violet `0xFF6B4EE6`.

---

# 2. Typography tokens

Families (`type_tokens.dart` L8–12): `display = 'Sora'`, `body = 'Manrope'`, `devanagari = 'Noto Sans Devanagari'` — all bundled in `pubspec.yaml` L68–77 from `assets/fonts/`.

Scale, `MilanTypeScale` extension L77–99 (size / line-height / weight):

| Token | Line | Family | Size | Height | Weight |
|---|---|---|---|---|---|
| `displayLarge` | L78 | Sora | 32 | 40 | w700 |
| `h1` | L79 | Sora | 28 | 36 | w700 |
| `h2` | L80 | Sora | 24 | 32 | w600 |
| `h3` | L81 | Sora | 20 | 28 | w600 |
| `h4` | L82 | Manrope | 18 | 24 | w600 |
| `bodyLarge` | L83 | Manrope | 16 | 24 | w400 |
| `bodyMedium` | L84 | Manrope | 14 | 20 | w400 |
| `caption` | L85 | Manrope | 12 | 16 | w500 |
| `overline` | L86–87 | Manrope | 11 | 16 | w600, `letterSpacing: 0.04` |

`_t()` L89–99 sets `fontSize: size * MediaQuery.textScalerOf(this).scale(1)` (L93), `height: height / size` (L94), and forces `color: milan.ink900` (L97).

Script-aware rendering: `containsDevanagari` L14–19 and `AppText` L21–74 split runs at the U+0900–U+097F boundary (L58) so mixed Nepali/English lines swap font per span (L49–51), emitted through `RichText` (L67).

There is **no `ThemeData.textTheme`** — the only `fontFamily` references in the whole app are `type_tokens.dart` L50 and L92, so any widget using bare `Text`/`TextStyle` falls back to the platform default font rather than Manrope.

Ad-hoc type sizes not covered by the scale: chat bubble body 15.5/1.32 (`chat_bubble.dart` L95), timestamp 10.5 (L101); swipe card name 24 w700 (`swipe_card.dart` L123), prompt overlay 15/1.3 (L110), distance chip 12 (L137); `common.dart` 20 w700 avatar initial (L221), 16 w700 name (L225), 12.5/1.35 description (L230), meter 28 w700 (L137) and 11 label (L139), locked chip 10 (L237/241); `appearance_screen.dart` 13 (L27, L49, L66) and 12 (L85); picker section labels 11 + `letterSpacing: .04` (`theme_picker_sheet.dart` L164, L194, L208, L411, L421).

**Double-scaling issue:** `_t` pre-multiplies `fontSize` by the text scaler (`type_tokens.dart` L93) while `app.dart` L47 also installs `textScaler: TextScaler.linear(a11y.textScale)` into `MediaQuery`. A plain `Text(..., style: context.h4)` therefore scales twice (scale²) — at the 140% max from `settings_screens.dart` L265 that is 1.96×. `AppText` escapes this because `RichText` (L67) defaults to no scaling, so the two paths disagree.

---

# 3. Spacing, radius, elevation

`spacing_tokens.dart`, `abstract final class Spacing`:

- Spacing: `xs = 4` (L7), `sm = 8` (L8), `md = 12` (L9), `lg = 16` (L10), `xl = 24` (L11), `xxl = 32` (L12), `xxxl = 48` (L13), `huge = 64` (L14).
- Radius: `radiusSm = 8` (L16), `radiusMd = 16` (L17), `radiusLg = 24` (L18), `pill = 999` (L19).
- Elevation: `shadowTint = Color(0x147B1E3A)` (L21), `raised` = one `BoxShadow(blurRadius: 12)` (L23–25), `floating` = `blurRadius: 24` (L27–29).

`floating` has zero call sites; `raised` is used in `swipe_card.dart` L66 and `common.dart` L41. `huge` appears twice (`onboarding_screens.dart` L86, `chat_extra_screens.dart` L326); `xxxl` twice (`discover_screen.dart` L86, `discovery_extra_screens.dart` L232).

Off-scale spacing in the chat/appearance surfaces: bubble margin `vertical: 3` (`chat_bubble.dart` L78), padding `8/13` (L79), max width `0.76 × screen` (L81), corner "tail" radius `4` (L63, L68), timestamp gap `3` (L96); typing bubble `12/16` padding (L179); appearance preview bubbles `8/13` padding and `4` tail (`appearance_screen.dart` L39, L46, L56, L62), `SizedBox(height: 6)` L52, avatar `radius: 14` L75; swipe card `bottom: 96` prompt offset (`swipe_card.dart` L101) and `minHeight: 3` progress (L150); `common.dart` preview card `size = 108` default and `size * 1.25` height (L19, L34), border `2.5` (L39), mini bubble `34×16` r8 (L71–75), story ring `size + 6` with `3`/`2` padding (L94–99), meter `132×132` with stroke `9` (L132–133, L158, L162), avatar `radius: 26` (L218); picker swatch `40×40` (L454–455), gradient tile `52×52` (L218–219), photo tile `96×96` (L336, L387), grabber `44×4` (L64–65), live preview height `132` and max bubble width `220` (L485, L518).

---

# 4. Motion tokens

`motion_tokens.dart`, `abstract final class Motion`:

| Token | Line | Value |
|---|---|---|
| `swipeSpring` | L6 | 420 ms |
| `matchCelebration` | L7 | 900 ms |
| `saathiTypingPulse` | L8 | 1200 ms |
| `storyTransition` | L9 | 220 ms |
| `chatThemeCrossfade` | L10 | 180 ms |
| `springOut` | L12 | `Curves.elasticOut` |
| `standard` | L13 | `Curves.easeOutCubic` |
| `maxSwipeRotationDeg` | L16 | 12 |

Helpers: `dragToRotation(dragExtent, width)` L18–21 (normalizes drag to 0–1 and multiplies by 12°, sign-preserving); `prefersReducedMotion(context)` L23–27 reads `MediaQuery.disableAnimationsOf` — single source of truth because `app.dart` L48 pipes the in-app toggle into that flag; `saathiTypingDelay(charCount)` L31–34 = `charCount / 14.0` seconds clamped to 0.8–4.0 s; `DragDirection` enum L36 and `DragGestureX.horizontalDirection` L38–41.

Consumers: `theme_picker_sheet.dart` L481–483 (`Duration.zero` when reduced, else `chatThemeCrossfade`); `typing_indicator.dart` L10 (`loop` default) and L40–42 (4 px lift suppressed when reduced); `swipe_card.dart` L59–62 (rotation multiplied by 0 when reduced); `chat_thread_screen.dart` L135 and `saathi_chat_screen.dart` L52 (typing indicator gated).

Currently **unused**: `swipeSpring`, `matchCelebration`, `storyTransition`, `springOut`, `standard`, `saathiTypingDelay`, `DragDirection`/`DragGestureX`. `swipe_card.dart` has no spring-back animation at all — `_dragDx` is reset synchronously in `setState` (L54), so the card snaps.

Ad-hoc durations outside the token set: `TypingDots` 1100 ms (`chat_bubble.dart` L203), `_InboxSkeleton` 1200 ms `repeat(reverse: true)` (`matches_inbox_screen.dart` L179). Swipe commit threshold is a bare `140` px (`swipe_card.dart` L42).

---

# 5. Sound effects and haptics

`core/feedback/sfx.dart`. Design note L5–6: system sounds only, zero licensed audio assets.

`enum Sfx` L7–15: `swipeLight` (pass), `swipeLike`, `superlike`, `match`, `messageSent`, `messageReceived`, `keyboardish`.

`SfxState` L17–21 defaults `soundOn = true`, `hapticsOn = true`. Persistence keys L28–29: `app.sound.enabled`, `app.haptics.enabled`; restored L31–37; setters L39–49.

`play(Sfx)` L51–75 — early return if both channels off (L52):

| Sfx | Line | Haptic | Sound |
|---|---|---|---|
| `swipeLight` | L54–56 | `lightImpact` | `SystemSoundType.click` |
| `swipeLike` | L57–59 | `mediumImpact` | `SystemSoundType.alert` |
| `superlike` | L60–62 | `heavyImpact` | `SystemSoundType.alert` |
| `match` | L63–65 | `heavyImpact` | `SystemSoundType.alert` |
| `messageSent` | L66–68 | `lightImpact` | `SystemSoundType.click` |
| `messageReceived` | L69–71 | `lightImpact` | none — comment says the OS notification layer owns it |
| `keyboardish` | L72–73 | `selectionClick` | none |

Provider `sfxProvider` L78–79.

Call sites (only two files): `discover_screen.dart` L115–120 maps direction → `superlike`/`swipeLike`/`swipeLight`, L125 plays `match` on mutual match; `chat_thread_screen.dart` L364 and L377 play `messageSent`. `messageReceived` and `keyboardish` are never played, and `setSound`/`setHaptics` have **no UI** anywhere — the persisted toggles are unreachable by the user.

---

# 6. Loading and skeleton widgets

There is exactly one skeleton in the codebase: `_InboxSkeleton` in `/home/bishal-regmi/Desktop/Milan/mobile/lib/features/chat/presentation/screens/matches_inbox_screen.dart` L170–212 (used at L66). It is a pulse-opacity placeholder, not a shimmer: 1200 ms reversing controller (L179), `opacity = 0.35 + 0.35 * _c.value` (L192), 7 rows (L208), each a 54 px `Colors.grey.shade200` circle plus 13×140 and 11×220 bars (L196–202), padded `Spacing.lg` horizontal / 10 vertical (L194).

`shimmer: ^3.0.0` is declared in `pubspec.yaml` L51 but never imported anywhere in `lib/`.

Everything else is a raw progress indicator:

- `CircularProgressIndicator`: `discover_screen.dart` L51; `chat_thread_screen.dart` L186 and L243 (20×20, `strokeWidth: 2`, inline send spinner); `chat_theme_studio_screen.dart` L54; `jhalak_feed_screen.dart` L121; `saathi_extra_screens.dart` L86, L145, L363; `profile_edit_screens.dart` L81; `my_profile_screen.dart` L70; `my_profile_view_screen.dart` L61; `settings_screens.dart` L73 and L165; `discovery_extra_screens.dart` L443; `camera_shell.dart` L89 (white); `onboarding_media_screens.dart` L176 (18×18, `strokeWidth: 2`) and L255.
- `LinearProgressIndicator`: `saathi_chat_screen.dart` L83 (`minHeight: 2`); `swipe_card.dart` L150–155 (carousel segments, `minHeight: 3`, `Colors.white30` track / white value); `interview_screen.dart` L104–108 (`minHeight: 3`, `marigold500`); `jhalak_extra_screens.dart` L167 (`value: .35`, white on `white24`).
- Text-level loading: `commonLoading` string — `app_localizations_en.dart` L94 `'Please wait…'`, `app_localizations_ne.dart` L97 `'कृपया पर्खनुहोस्…'`; used at `onboarding_screens.dart` L242, L485 and `saathi_extra_screens.dart` L123. Local `_uploading`/`_loading` booleans are the pattern elsewhere.

No error-state or empty-state shared widget exists either; each screen inlines its own (e.g. `discover_screen.dart` L52–63 and `_EmptyState` L144+, `matches_inbox_screen.dart` L67–75 and L82–90).

---

# 7. How theme and accent selection works today

Three independent systems, only one of which syncs to the backend.

## 7.1 App-wide light/dark — not user-selectable

`app.dart` L38–41 wires `theme: milanLightTheme()`, `darkTheme: milanDarkTheme()`, and hardcodes `themeMode: ThemeMode.system`. The comment on L40 claims "system default with manual override in Settings (screen 63)", but `LanguageAccessibilityScreen` (`settings_screens.dart` L232–284) exposes only language, text size and reduce-motion — **there is no theme-mode control anywhere**, and no provider holds a `ThemeMode`. Dark mode follows the OS only.

## 7.2 Accessibility overrides — real and persisted

`a11y_settings.dart`: `A11yState` L9–21 (`languageCode` default `'system'`, `textScale` 1.0, `reduceMotion` false; `locale` getter L19–20 returns null for `'system'`). Keys L28–30: `app.language`, `app.textScale`, `app.reduceMotion`, restored L32–39, setters L41–66, provider L69–70. Applied at the root in `app.dart` L42 (`locale`) and L45–51 (`MediaQuery.copyWith(textScaler:, disableAnimations:)`). UI: `settings_screens.dart` L245–259 (three `ChoiceChip`s), L262–269 (slider `.8`–`1.4`, `divisions: 4`, `activeColor: marigold500`), L270–277 (reduce-motion switch).

## 7.3 App accent — local-only, five fixed choices

`accent_theme.dart`: `AccentThemeState` L11–16 defaults to `ChatBubble.defaultAccent` (`0xFF0B84FE`); `AccentThemeController` L18–38 restores from `SharedPreferences` key `app.accent.color` (L23, L25–31) and writes with `prefs.setInt(_key, color.value)` (L36); provider L40–42; palette L45–51.

Selection UI is `appearance_screen.dart`: reads accent L19, renders a live white-card preview with a sent bubble filled by `accent` (L38–51) and a received bubble filled by `ChatBubble.receivedFill` (L55–68), then one `ListTile` per palette entry with a check mark on the active one (L72–82), calling `setAccent` on tap (L80–81). Footer copy L84–85 states chat backgrounds stay white and wallpapers are per-chat.

Consumption is limited to four sites: `chat_bubble.dart` L50–54 (accent fills sent bubbles unless `bubbleColor`/`accentColor` is passed), `matches_inbox_screen.dart` L29 and L41 (AI-companions action icon), `chat_thread_screen.dart` L249 (attachment icon) and L289 (send FAB background). `chat_thread_screen.dart` L284 still hardcodes `ChatBubble.defaultAccent` for the active mic icon, so that one control ignores the user's accent.

Two rough edges: the accent is never sent to the backend (device-local only, unlike chat themes), and `AccentThemeState.copyWith(Color color)` (L15) takes a positional required argument rather than the conventional named-optional shape. `accent_theme.dart` L36 uses the deprecated `color.value` while `chat_theme_tokens.dart` L150 already uses `toARGB32()`.

**The Appearance screen is unreachable.** `my_profile_screen.dart` L171–172 pushes `/settings/appearance`, and `router.dart` L23 imports `appearance_screen.dart`, but no `GoRoute` for that path exists (settings routes are L191–201; `AppearanceScreen` is never referenced in `router.dart`). The router also has no `errorBuilder`, so that tap lands on go_router's default error page. `ChatThemeStudioScreen` (screen 67) is likewise orphaned — `router.dart` L202 has the comment `// Personalization (screen 67)` with no route beneath it.

## 7.4 Per-chat wallpaper/bubble themes — scoped, offline-first, backend-synced

Scope key: `chat_theme_tokens.dart` L15–50. Three kinds (`global`, `match`, `saathi`) with `storageKey` L34–43 producing `'global'`, `'match:<id>'`, `'saathi:<characterId>'`; equality is by `storageKey` (L46–49).

Model `ChatWallpaperTheme` L52–148: `wallpaperType` (`preset|solid|gradient|customUpload|aiGenerated|photoSet`, enum L11), `wallpaperValue`, `photoUrls`, `bubbleColorSent/Received`, `bubbleShape` (`rounded|compact`, L13), `doodleOverlayId`, `textScale`, `darkModeBrightness`, `presetId`. `copyWith` L87–115 has explicit `clearDoodle`/`clearTextScale`/`clearBrightness` flags. Serialization `toBackendJson` L117–128 / `fromBackendJson` L130–147 — note `presetId` is **not** persisted (L145 hardcodes null), and `photoUrls` is absent from the JSON payload, so photo-set selections do not survive a backend round-trip.

Resolution, `theme_provider.dart` — documented order at L12 is scoped override → global default → factory default:

1. `build()` L28–48 first reads the SQLite cache (`_db.loadResolvedTheme`, L30) for an instant offline value and kicks off `unawaitedSync()` (L32).
2. On cache miss it fetches server truth (`_fetchResolvedFromBackend` L85–99 → `/personalization/theme`, `/personalization/theme/match/<id>`, `/personalization/theme/saathi_session/<sessionId>`), caches it as synced (L41).
3. On failure it falls back to `_defaultForScope` L63–69 — Saathi scopes get `MilanChatPresets.defaultForSaathiCharacter` (`chat_theme_presets.dart` L248–250), everything else `factoryDefault`.
4. `_mergeWithDefaults` L50–61 backfills null bubble colors from the matching preset.

Saathi indirection: `_saathiSessionId` L76–83 with the P0-4 comment at L71–75 — the backend parses `scope_id` as a `SaathiSession` UUID, so a character key like `'asha'` would 500; scopes stay character-keyed locally but resolve to the active session UUID for network calls, and stay local-only when no session exists (L95, L179).

Writes: `apply()` L103–116 is optimistic — state updates with `syncPending: true` (L105), local save first (L107), then `_pushToBackend` (L170–183, `PUT`); on `AppException` the local value is kept and `ref.keepAlive()` is called (L112–115), never reverting the user mid-session. `reset()` L119–143 issues the scoped `DELETE`, then writes the scope default locally even if the network failed (L133–141). `_scopeName` L159–168 maps the enum to backend scope strings (`global`/`match`/`saathi_session`). Provider `themeProvider` L186–187 is an `AsyncNotifierProvider.family` keyed by `ChatThemeScopeKey`. Cache table `resolved_themes(scope_key, theme_json, synced)` — `local_db.dart` L37–39, L65–94.

Picker UI `theme_picker_sheet.dart`: 5 tabs (L91–113 — Presets, Solid & Gradient, Photo, Photo Set, Bubble Color), scope banner L74–86, `WallpaperLivePreview` L88 / L472–531, **contrast-gated Apply** at L59 + L132–143 (button greys to `ink400` and `onPressed` is null when `passesContrast` fails), `Reset to default` L123–130. Photo uploads compress then POST to `/personalization/theme/upload` and only the returned CDN URL becomes the wallpaper value (L254–275); offline falls back to a local URI preview. Photo Set is gated on `tier.isPlusOrHigher` (L312) with a paywall card, capped at 6 photos (L355, L363), and rotates by UTC day (`photoSetWallpaperFor`, `chat_theme_presets.dart` L271–278, epoch `2026-01-01`). Entry points: `chat_thread_screen.dart` L168–175 popup → `_openThemeSheet`, plus full-page hosts `ChatThemeRouteScreen` (`chat_extra_screens.dart` L345–356, route `router.dart` L129–131) and `SaathiThemeRouteScreen` (`saathi_extra_screens.dart` L448–459, route L162–164). `saathi_chat_screen.dart` L73 has a palette `IconButton` with an **empty `onPressed: () {}`**. `chat_theme_studio_screen.dart` is similarly non-functional — L48 `Change scope`, L70 brightness slider, L84 photo picker, L105 shape selector and L112/L114 text-size buttons are all no-op callbacks.

Rendering: `resolveWallpaperDecoration` (`chat_theme_presets.dart` L281–348) is called from `chat_thread_screen.dart` L181, `saathi_chat_screen.dart` L79, `theme_picker_sheet.dart` L487 and `common.dart` L48. Bubble shape flows through to `ChatBubble.bubbleShape` (`chat_thread_screen.dart` L224 → `chat_bubble.dart` L47–48 mapping `compact → radiusMd`, `rounded → radiusLg`). Note `resolved.textScale` is read only as a spacing trigger (`chat_thread_screen.dart` L232) and never actually applied to message text.

## 7.5 Test coverage

`mobile/test/chat_theme_test.dart` (factory defaults L12–17, scope-key collisions L19–26, contrast rejection L28–44, JSON round-trip L46–66, bubble widget L69–114), `theme_provider_test.dart` (factory fallback L55–69, offline-first cache L71–92, Saathi signature default L94–113, optimistic-keep-on-failure L115–140), `theme_picker_sheet_test.dart` (tabs/scope/reset/Apply L39–92). There are **no tests** for `accent_theme.dart`, `a11y_settings.dart`, `sfx.dart`, or `_InboxSkeleton`.

I have completed a comprehensive exploration of the Dobato repository. Here is the full writeup.

# Dobato Repository — Complete Exploration Report

All findings below come from directly reading the source files; nothing is inferred. Paths are absolute.

Repo root: `/home/bishal-regmi/Downloads/dobato-main (1)/dobato-main`
Two halves: a NestJS + Prisma + Postgres backend at `dating-backend/`, and a Flutter app at `lib/` (single-package, `pubspec.yaml` at root).

---

## 1. Prisma Schema — Complete Models and Fields

File: `/home/bishal-regmi/Downloads/dobato-main (1)/dobato-main/dating-backend/prisma/schema.prisma` (333 lines). Provider `postgresql`, client `prisma-client-js`, `engineType = "library"`. Note: no `url` on the datasource block — the connection is supplied at runtime via driver adapters (`@prisma/adapter-neon` / `@prisma/adapter-pg`).

Enums: `Role{USER,ADMIN}`, `AccountStatus{PENDING,ACTIVE,SUSPENDED,DEACTIVATED}`, `VerificationType{EMAIL_VERIFICATION,PASSWORD_RESET}`, `NotificationType{NEW_MATCH,NEW_MESSAGE,SYSTEM_ALERT}`, `ReportReason{SPAM,HARASSMENT,INAPPROPRIATE_CONTENT,FAKE_PROFILE,UNDERAGE,OTHER}`, `ReportStatus{PENDING,REVIEWED,RESOLVED,DISMISSED}`, `SwipeAction{LIKE,PASS,SUPER_LIKE}`, `SubscriptionTier{FREE,PLUS,GOLD,PLATINUM}`, `SubscriptionStatus{ACTIVE,CANCELED,EXPIRED,PAST_DUE}`.

**User** — `id` (uuid), `firstName`, `lastName`, `username` (unique), `email` (unique), `phoneNumber?`, `password`, `role`, `accountStatus` (default PENDING), `emailVerified` (false), `profileCompleted` (false), `trustScore` Int default 50, `lastLogin?`, `createdAt`, `updatedAt`, `deletedAt?` (soft-delete), `refreshToken?` (bcrypt hash of the active refresh token), `coinBalance` Int default **250**. Relations: profile, photos, interests (UserInterest), preferences, matchesAsUserOne/Two, sentMessages/receivedMessages, filedReports/receivedReports, swipesGiven/swipesReceived, verifications, notifications, subscription, sentGifts/receivedGifts. Indexes on email, username, deletedAt.

**Profile** — 1:1 with User (`userId` unique, cascade). `bio?`, `gender?`, `dateOfBirth?`, `height?` Int, `occupation?`, `education?`, `relationshipGoal?`, `religion?`, `drinking?`, `smoking?`, `languages String[]`, `city?`, `country?`, `latitude? Float`, `longitude? Float`, `prompts Json? @default("[]")`, timestamps. Indexes: gender, (city,country), (latitude,longitude). All lifestyle/goal fields are free strings validated only at the DTO layer, not DB enums.

**Photo** — `userId` (cascade), `imageUrl`, `publicId` (Cloudinary), `isPrimary` bool, timestamps. Indexes userId, isPrimary. No `sortOrder` column (the Flutter reorder UI is therefore not persisted).

**Interest** — `name` unique, `icon?`, `category?`. **UserInterest** — composite PK `(userId, interestId)`, both cascade.

**Preference** — 1:1 (`userId` unique). `preferredGender` (required), `minAge` 18, `maxAge` 100, `maxDistance` 50, `relationshipGoal` (required), `showMe` true, `ageStrict` false, `distanceStrict` false, plus privacy flags `showDistance`, `showAge`, `showOnlineStatus` (true), `invisibleMode`, `hideFromSearch` (false). This one table doubles as both discovery preferences and the privacy-settings store.

**Match** — `userOneId`/`userTwoId` (cascade), `matchedAt`, `isBlocked` bool, `blockedBy?`, timestamps, `messages Message[]`. `@@unique([userOneId, userTwoId])` — ordering is enforced in application code by sorting the two UUIDs.

**Message** — `matchId`, `senderId`, `receiverId` (all cascade), `content` String, `isRead` bool, `createdAt`. Index `(matchId, createdAt)`. No `type` enum, no media URL, no `deliveredAt` — text-only despite the DTO advertising TEXT/PHOTO/GIF/VOICE.

**Report** — `reporterId`, `reportedUserId`, `reason` (enum), `description?`, `status` (default PENDING), `createdAt`. No `reviewedBy`/`reviewedAt` columns (the repository accepts a `reviewedBy` arg and discards it — see `reports.repository.ts:64-75`).

**Verification** — `userId`, `type`, `token` unique, `expiresAt`, `createdAt`, index on token. Used for both email verification and password reset.

**Swipe** — `swiperId`, `targetUserId`, `action` (enum), `createdAt`, `@@unique([swiperId,targetUserId])`, indexes on both. No `note`, no `isRewound`, no `seenByTarget` — rewind hard-deletes.

**Notification** — `userId`, `type` (3-value enum), `title`, `message`, `metadata Json?`, `isRead`, `createdAt`, index userId.

**Subscription** — 1:1 (`userId` unique), `tier`, `status`, `expiresAt?`, `boostsRemaining` Int default 0, timestamps.

**GiftTransaction** — `senderId`, `receiverId` (cascade), `giftId` String (a catalog key, not an FK), `coinPrice` Int, `createdAt`, indexes on sender and receiver.

Notably absent from the schema: `Block` (blocking is modelled as `Match.isBlocked`, and the search filter substitutes `Report` rows — explicitly commented at `search.repository.ts:80`), any selfie/liveness verification table, any daily-quota ledger, any boost-window table, any device-token table.

---

## 2. Backend Modules and Every Endpoint

Bootstrap (`src/main.ts`): global prefix `api/v1`, helmet with CSP disabled, `enableCors({origin:true, credentials:true})` — a permissive CORS posture worth flagging for production. `ValidationPipe` with `whitelist`+`forbidNonWhitelisted`. Global `HttpExceptionFilter`, `LoggingInterceptor`, `TransformInterceptor`. Swagger at `api/docs` when `ENABLE_SWAGGER=true` or non-prod. Redis Socket.IO adapter installed unless `ENABLE_REDIS=false`. `TransformInterceptor` wraps every response as `{success, statusCode, message, data, meta?}` — unwrapping `data`/`message`/`meta` if the controller returned them.

Registered modules (`app.module.ts`): Prisma, Users, Auth, Profiles, Photos, Interests, Matches, Messages, Notifications, Reports, Admin, Redis, Socket, Jobs, Subscriptions, Gifts, Search, Swipes, Preferences. Global `ThrottlerGuard` (`THROTTLE_TTL`/`THROTTLE_LIMIT`, defaults 60s/100). `settings/` and `verification/` module folders exist but contain only `.gitkeep` — never wired.

Endpoints (all prefixed `/api/v1`, JWT bearer unless noted):

- **Auth** (`auth.controller.ts`, public except where noted): `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout` (auth), `POST /auth/change-password` (auth), `POST /auth/forgot-password`, `POST /auth/reset-password`, `GET /auth/verify-email?token=`.
- **Users**: `GET /users/me`, `PATCH /users/me`, `DELETE /users/me` (soft delete), `GET /users` (page/limit/search/sortBy/sortOrder), `GET /users/:id`.
- **Profiles**: `POST /profiles`, `GET /profiles/me`, `PATCH /profiles/me`, `DELETE /profiles/me`.
- **Photos**: `POST /photos` (multipart, field `file`, max 6), `GET /photos/me`, `PATCH /photos/:id/primary`, `DELETE /photos/:id`.
- **Interests**: `POST /interests`, `GET /interests`, `GET /interests/me`, `PUT /interests/me` (max 10, dedup + existence validated), `DELETE /interests/me/:interestId`.
- **Preferences**: `POST /preferences`, `GET /preferences/me`, `PATCH /preferences/me`, `DELETE /preferences/me`.
- **Search**: `GET /search` — the actual discovery feed.
- **Swipes**: `POST /swipes`, `POST /swipes/rewind`.
- **Matches**: `GET /matches` (page/limit), `DELETE /matches/:id` (`:id` = target *user* id), `PATCH /matches/:id/block`.
- **Messages**: `POST /messages`, `GET /messages/chats`, `GET /messages/:matchId`, `PATCH /messages/:id/read`, `DELETE /messages/:id`.
- **Conversations** (the Flutter-facing alias, `conversations.controller.ts`): `GET /conversations`, `GET /conversations/:conversationId/messages`, `POST /conversations/:conversationId/messages` (body `{text}`; also emits `new-message` over the socket room), `PATCH /conversations/:conversationId/read`. `conversationId` == `matchId`.
- **Notifications**: `GET /notifications` (page/limit/isRead), `PATCH /notifications/read-all`, `PATCH /notifications/:id/read`, `DELETE /notifications/:id`.
- **Reports**: `POST /reports`, `GET /reports/me`, `GET /reports` (ADMIN), `PATCH /reports/:id` (ADMIN, body `{status}`).
- **Safety** (three separate controllers all mounted on `safety`): `POST /safety/report` (maps `details`→`description`), `POST /safety/block` (delegates to `MatchesService.blockUser`, so it 404s unless a Match already exists), `GET /safety/privacy`, `PATCH /safety/privacy` (both read/write the `Preference` row).
- **Subscriptions**: `GET /subscriptions/plans`, `GET /subscriptions/status`, `POST /subscriptions/subscribe`, `POST /subscriptions/boost`.
- **Gifts/Wallet** (`@Controller()` — no prefix): `GET /gifts`, `GET /wallet`, `GET /wallet/packages`, `POST /wallet/topup`, `POST /gifts/send`.
- **Admin** (`JwtAuthGuard`+`RolesGuard`, `@Roles('ADMIN')`): `GET /admin/dashboard`, `GET /admin/stats`, `GET /admin/users`, `GET /admin/users/:id`, `PATCH /admin/users/:id/ban`, `PATCH /admin/users/:id/unban`, `DELETE /admin/users/:id`, `PATCH /admin/users/:id/verify`, `GET /admin/reports`, `GET /admin/moderation/flags`, `GET /admin/moderation/verifications`.
- Root `GET /` health-ish hello.

Dashboard stats are thin — `admin.repository.ts:9-23` returns only `{totalUsers, activeUsers, totalMatches, pendingReports}` while `DashboardEntity` advertises seven fields; `getModerationVerifications` returns **hardcoded fake rows** (`admin.service.ts:143-165`).

There is no `GET /feed`, no `GET /matches/:id`, and no `GET /matches/who-liked-me` — all three are specced in `dating-backend/missing_api_spec.md` and still absent. The Flutter side compensates: `real_match_repository.dart:28-35` fabricates a `Match` locally, and `getWhoLikedYou()` returns *existing matches* rather than pending likers.

---

## 3. Onboarding Flow and Profile Data Collected

Router: `/home/bishal-regmi/Downloads/dobato-main (1)/dobato-main/lib/core/router/app_router.dart`, names in `route_names.dart`. Gating comes from `SessionStage {initial, needsAuth, needsOnboarding, ready}` in `core/di/session_provider.dart`; `ready` requires `user.isProfileCompleted`.

Order: `/splash` → `/onboarding` (3-slide carousel with the "Dotted Trail" motif) → `/permissions` (location + notifications priming; actually calls `Geolocator` and reverse-geocodes) → `/auth/login` or `/auth/register` → `/auth/verify-email` → `/setup/basic-info` → `/setup/photos` → `/setup/bio-prompts` → `/setup/interests` → `/verify/selfie` → `/setup/complete` → `/home`.

What each step collects:
- **basic-info** (step 0): `dateOfBirth` (date picker hard-bounded to 18–80) and `gender` (man/woman/nonBinary → MALE/FEMALE/OTHER). Saved through `PATCH /profiles/me`, falling back to `POST /profiles` on 404 (`real_profile_repository.dart:193-203`).
- **photos** (step 1): up to 6 slots, minimum 2 to continue, first is Main. Each pick uploads immediately as multipart to `POST /photos`.
- **bio-prompts** (step 2): `bio` (maxLength 300 in UI, 500 in the DTO) plus prompt answers. The prompt catalog is **local-only** — `FixturePromptQuestions.all`, 10 Nepal-flavored questions ("My go-to momo order is…"), because no prompts endpoint exists (`real_profile_repository.dart:338-341`). Answers persist into `Profile.prompts` JSON as `{id, questionId, questionText, answerText}`.
- **interests** (step 3): minimum 2, max 5 client-side (backend allows 10), `PUT /interests/me`.
- **selfie verification**: `selfie_verification_screen.dart` is a **pure mock state machine** (capturing→reviewing→submitted→approved with `Future.delayed`). No camera, no upload, no endpoint. The awarded "Trail Green badge" is cosmetic; `isVerified` in the app is actually mapped from `emailVerified`.
- **complete**: sets a local `onboarding_seen` pref and syncs location to the backend.

Email verification is currently **bypassed on purpose**: `otp_verification_screen.dart` is titled "Verification Bypass", labelled "Dev Mode Active", the CTA reads "Bypass verification (Dev Mode)", and resend is disabled. Despite the filename there is no OTP — the backend uses a magic link (`GET /auth/verify-email?token=`), handled via the `/verify-email-link` deep-link route.

Full profile surface available to a user: bio, gender, DOB, height, occupation, education, relationshipGoal, religion, drinking, smoking, languages[], city, country, lat/lng, prompts[], plus photos and interests. Registration itself collects firstName, lastName, username, email, password (min 8, no complexity rule).

---

## 4. Matching, Swipe, and Search Algorithms

**Swipe** (`swipes/services/swipes.service.ts`): rejects self-swipes, rejects any repeat swipe with 409 Conflict, then inside a single `$transaction` creates the Swipe and — for LIKE/SUPER_LIKE — looks for a reciprocal LIKE/SUPER_LIKE. On reciprocity it sorts the two UUIDs lexicographically and creates the Match, returning `{type:'MATCH_CREATED', matchId}`; otherwise `{type:'SWIPE_SAVED'}`. There are **no daily like caps, no super-like caps, no tier gating, and no notification** emitted on match — the only notifications ever created anywhere in the backend are the two in `gifts.repository.ts` (gift received, wallet top-up) plus seeded rows.

**Rewind** (`swipesService.rewindLastSwipe`): finds the newest swipe, deletes any Match it produced, then hard-deletes the swipe row. No quota, no premium check, no refund ledger. `SUPER_LIKE` exists as an enum value but is treated identically to `LIKE` everywhere.

**Discovery** (`search/services/search.service.ts` + `search.repository.ts`): the ranking is essentially "none". Steps: load the caller's `Preference` and use it to fill any unset filter (minAge, maxAge, gender, relationshipGoal, maxDistance); query with `skip/take`; then compute Haversine distance in JS and filter. The SQL `where` excludes self, soft-deleted users, non-`ACTIVE` accounts, existing matches (both directions), users involved in a report either way, and users already swiped. Age filtering converts min/max age into `dateOfBirth` bounds. There is no `orderBy` at all, so ordering is whatever Postgres returns; no compatibility score, no shared-interest weighting, no boost multiplier, no recency-of-activity signal.

Two concrete correctness problems I can point at:
- Distance filtering happens **after** pagination, and `meta.total` is then recomputed from the post-filter page length (`search.service.ts:111-119`), so `total`/`totalPages` are wrong and pages can come back short or empty.
- `SearchRepository.searchUsers` only `include`s `profile`, but `SearchService` reads `user.photos` and `user.interests` (`search.service.ts:83-84`). Those are always undefined, so `primaryPhoto` is always `null` and `interests` always `[]` — the deck ships without photos from this path. `Preference.showMe`, `invisibleMode`, and `hideFromSearch` are also never applied to the query.

`MatchesService.getMyMatches` synthesizes an `expiresAt` = matchedAt + 24h purely in the response (no DB column, nothing enforces it). `unmatchUser` deletes the Match row (cascading its messages); `blockUser` flips `isBlocked`, and blocked matches are excluded from `getUserMatches` and rejected in `MessagesService.sendMessage`.

---

## 5. Gifts, Wallet, Subscriptions

**Gifts** (`gifts/services/gifts.service.ts`): catalog is a hardcoded 2-item array — `gift_rose` (10 coins, Romance), `gift_momo` (25 coins, Fun) — with `iconAsset` paths (`assets/gifts/rose.png`) that don't exist in the repo; the Flutter fixture (`fixture_gifts.dart`) instead has 6 emoji-based gifts (Marigold Garland, Momo Plate, Prayer Flags, Diya Lamp, Chiya, Mountain Badge). Coin packages: `pkg_100` NPR 100, `pkg_500` NPR 450 ("10% OFF"), `pkg_1000` NPR 800 ("20% OFF — Best Value").

`GiftsRepository.sendGiftTransaction` is a proper `$transaction`: re-reads balance, throws on insufficient funds, decrements, writes `GiftTransaction`, and inserts a `SYSTEM_ALERT` notification for the receiver. Insufficient funds surfaces as **HTTP 402** with `{success:false,message}`. Recipients get no coin credit — gifting is a pure sink.

`topUpWallet` is the notable gap: it looks up the package and **immediately credits coins with no payment verification at all** — `paymentMethod` and `transactionId` are only used to build a reference string (`gifts.service.ts:62-77`, `creditWallet` at `gifts.repository.ts:75-93`). This is an unauthenticated-value mint from the business perspective; the DTO advertises "ESEWA, MOCK" but no gateway is contacted.

**Subscriptions** (`subscriptions/services/subscriptions.service.ts`): hardcoded plans — `plan_plus_1mo` $9.99 (unlimited likes, rewind), `plan_gold_1mo` $14.99 (+ see who likes you, 5 super likes/day), `plan_platinum_1mo` $19.99 (+ priority likes, message before matching). Boost packs `boost_pack_1` $4.99 / `_5` $19.99 / `_10` $34.99. `subscribe()` "processes" payment by checking `if (paymentMethodId === 'fail') throw` — otherwise it upserts the subscription with `expiresAt = now + durationMonths`. `boost()` just increments `boostsRemaining`; nothing anywhere consumes it, there is no active-boost window, and no ranking code reads it. Free tier is described as "Basic matching, 50 likes/day" but no like counter exists. Every advertised premium feature (unlimited likes, rewind gating, who-liked-you, priority, message-before-match) is unenforced in code.

Prices are USD in the plans and NPR in the coin packages; the Flutter `real_subscription_repository.dart` renders them as `"$9.99"` and synthesizes `durationLabel` as `"GOLD · 1 month"`, because the backend shape doesn't match the app's `SubscriptionPlan` model (no isMostPopular/isBestValue, no per-month label). `autoRenew` is hardcoded `false` client-side with the comment "Backend doesn't track this yet". `getInventory()` maps `boostsRemaining` into `spotlightsRemainingThisWeek` and always reports `superSwipesRemaining: 0`.

---

## 6. Trust-Score Service

File: `/home/bishal-regmi/Downloads/dobato-main (1)/dobato-main/dating-backend/src/modules/users/services/trust-score.service.ts` — 51 lines, one method.

```ts
let score = 20;                       // base
if (user.emailVerified)   score += 20;
if (user.profileCompleted) score += 20;
if (user.photos.length>0)  score += 20;   // any photo, count-insensitive
score -= activeReportsCount * 15;         // reports not DISMISSED
score = Math.max(0, Math.min(100, score));
```
Max achievable is 80, never 100. It writes `User.trustScore` and returns it; on any error it swallows and returns 50 without writing. Invoked from four places: `AuthService.verifyEmail`, `ProfilesService.createProfile/updateProfile/deleteProfile`, `PhotosService.uploadPhoto/deletePhoto`, and `ReportsService.createReport/reviewReport`. Nothing reads `trustScore` — it is not used in search ranking, not exposed in any DTO/entity, and not surfaced in the Flutter app. It is a write-only field today.

---

## 7. Socket / Presence Design

Gateway: `socket/gateways/chat.gateway.ts`, `@WebSocketGateway({cors:{origin:'*'}, namespace:'/chat'})`.

Handshake auth is done manually in `handleConnection`: token from `Authorization: Bearer` header or `handshake.auth.token`, verified with `jwtService.verifyAsync(token, {secret: process.env.JWT_SECRET})`, then `client.data.userId = payload.sub`. Failure → `client.disconnect()`. Two details worth flagging: the gateway reads `process.env.JWT_SECRET` while HTTP auth uses `jwt.accessSecret` ← `JWT_ACCESS_SECRET` (`config/jwt.config.ts`), so unless both env vars are set the socket path validates against a different/undefined secret; and `socket/guards/ws-jwt.guard.ts` exists with the same bug but is **never applied** to any handler.

Client→server events: `join-room {matchId}`, `leave-room {matchId}`, `send-message` (SendMessageDto), `typing {matchId}`, `stop-typing {matchId}`, `mark-as-read {messageId}`. Server→client: `new-message`, `user-typing`, `user-stopped-typing`, `message-read`. `interfaces/socket-events.interface.ts` declares a *different* contract (`typing`/`stop-typing`/`user-online`/`user-offline`) than the gateway actually emits — and the Flutter client listens for `'typing'` (`chat_socket_service.dart:109`) while the gateway emits `'user-typing'`, so **typing indicators never fire in practice**. `user-online`/`user-offline` are declared but never emitted anywhere.

`join-room` performs **no authorization check** — any authenticated socket can `client.join(matchId)` for an arbitrary match id and will then receive every `new-message` broadcast for that conversation. Message *sending* is authorized (`MessagesService.sendMessage` verifies participation), but reading via the room is not.

Presence: `socket/services/presence.service.ts` keeps a Redis SET per user, key `presence:user:{userId}`, holding socket ids. `registerConnection` = `SADD` + `EXPIRE 86400` (24h TTL to avoid orphans on hard crash); `removeConnection` = `SREM`; `isUserOnline` = `SCARD > 0`; `getUserSocketIds` = `SMEMBERS`; `getTotalOnlineUsers` walks all keys with `SCAN … COUNT 100` and a pipelined `SCARD`. Multi-socket-per-user is handled correctly. Nothing calls `isUserOnline`/`getTotalOnlineUsers` — presence is recorded but never read or broadcast, and `Preference.showOnlineStatus` has no consumer.

`socket/services/room.service.ts` is an in-memory `Map<roomId, Set<userId>>` that is provided and exported but never injected anywhere — dead code, and would not survive horizontal scaling anyway.

Horizontal scale-out is real for the transport: `RedisIoAdapter` reuses the global ioredis client as the pub client and `.duplicate()`s a sub client, waits for both to be `ready`, then `createAdapter(pub,sub)`. When `ENABLE_REDIS=false`, `redis.provider.ts` returns a `Proxy` mock whose every method resolves `null` (with a deliberate `then → undefined` guard to avoid an await hang), so presence silently no-ops in that mode.

---

## 8. Notifications

DB-only inbox; there is **no push infrastructure at all** — no FCM/APNs, no device-token table, no push service in either half of the repo.

Types are limited to `NEW_MATCH | NEW_MESSAGE | SYSTEM_ALERT`, while the Flutter model (`notification_item.dart`) has five (`newMatch, newMessage, like, system, promo`) and the spec doc asks for six. Notifications are created in exactly two production paths — gift received and wallet top-up (both in `gifts.repository.ts`) — so despite `NEW_MATCH`/`NEW_MESSAGE` existing, nothing ever writes them outside the seed script. There is no per-category preference table, no frequency cap, and no send-time scheduling.

Job queues (`modules/jobs/`) are scaffolding: BullMQ `Queue` providers for `email`/`notification`/`cleanup` (attempts 3, exponential backoff 1000ms, `removeOnComplete`), and four `WorkerHost` processors (`email`, `notification`, `cleanup`, `reminder`) whose bodies are all `setTimeout` + log + `return {success:true}`. Only the three queue providers are registered in `JobsModule` — **the processors are never registered**, and nothing in the codebase ever calls `queue.add()`. When Redis is mocked the queue providers return `{add: async()=>null}`.

Mail (`modules/mail/mail.service.ts`) does work via `@nestjs-modules/mailer`: verification, password-reset, and welcome emails. All three hardcode `http://localhost:3000` in the link URLs, so the verification magic link is broken in any deployed environment — which explains the Dev-Mode bypass screen. `sendWelcomeEmail` is defined but never called.

---

## 9. Flutter `lib/` Structure

Root: `main.dart` (overrides `sharedPreferencesProvider`, runs `DobatoApp`), `app.dart` (`MaterialApp.router`, light theme only, global `scaffoldMessengerKey`).

```
lib/core/
  constants/  app_spacing.dart, asset_paths.dart
  di/         local_prefs.dart, repository_providers.dart, session_provider.dart
  router/     app_router.dart, route_names.dart
  services/   chat_socket_service.dart, location_service.dart
  theme/      app_colors.dart, app_shapes.dart, app_text_styles.dart, app_theme.dart
  utils/      extensions.dart, formatters.dart, global_keys.dart, validators.dart
  widgets/    app_bottom_nav_shell, dotted_trail_indicator, gradient_photo_card,
              interest_chip, junction_mark_logo, photo_grid_slot, pill_button,
              premium_badge_chip, prompt_answer_card, swipe_action_row, verified_badge
lib/data/
  api_client.dart
  fixtures/     conversations, gifts, interests, plans, prompt_questions, users
  repositories/ 9 abstract interfaces (auth, chat, feed, gift, match,
                notification, profile, safety, subscription)
  remote/repositories/ 9 Real*Repository implementations + README_API_INTEGRATION.md
lib/features/
  auth/ (login, register, otp_verification)
  chat/ (chat_list, chat_providers, individual_chat)
  feed/ (feed_screen, feed_providers, filters_sheet, full_profile, widgets/swipeable_card)
  matches/ (match_celebration)
  notifications/ (notifications_screen)
  onboarding/ (carousel, permission_priming)
  premium/ (boost, gifts_store, paywall, who_liked_you, premium_providers)
  profile/ (my_profile, profile_providers, settings)
  profile_setup/ (basic_info, photo_upload, bio_prompts, interest_selection,
                  widgets/setup_step_scaffold)
  safety/ (privacy_controls, privacy_providers, report_block_sheet, safety_center)
  splash/, verification/ (selfie_verification, onboarding_complete)
lib/models/   22 freezed+json_serializable models with .freezed.dart/.g.dart generated
```

Architecture: Riverpod throughout; every feature depends on interface-typed providers in `core/di/repository_providers.dart` (documented as "THE ONE FILE that swaps mock → real"), all nine of which now point at `Real*Repository`. `go_router` with a `StatefulShellRoute.indexedStack` 4-tab shell (Home / Chats / Likes / Profile). Networking is a Dio singleton (`data/api_client.dart`) with base URL `https://dating-backend-evu4.onrender.com`, `flutter_secure_storage` for tokens, a 401 interceptor that refreshes via `/auth/refresh` and retries the original request, and a global error snackbar (suppressed for 401s and for `/profiles/me` 404s). Deps: `flutter_riverpod ^2.5.1`, `go_router ^14.2.0`, `freezed ^2.5.7`, `dio ^5.10.0`, `socket_io_client ^3.1.6`, `geolocator ^13.0.1`, `geocoding ^3.0.0`, `google_fonts ^6.2.1`, `fl_chart`, `image_picker`, `shimmer`. `pubspec.yaml` declares **no** `flutter/assets:` section, so the gift `iconAsset` paths and any real imagery have no bundle behind them. A cluster of Python fixup scripts at the repo root (`fix_app.py`, `fix_types.py`, `add_stubs.py`, `fix_scaffold.py`, `fix_app_spacing.py`, `fix_fixture_imports.py`) plus `analyze.log` / `flutter_analyze_output.txt` suggest the codebase was mass-patched to compile.

Almost every `Real*Repository` method swallows exceptions and returns an empty list/default (`catch (e) { return []; }`) — a deliberate choice for demo resilience that also means backend failures are invisible to the user.

---

## 10. Theme and Spacing Constants (exact values)

`core/constants/app_spacing.dart` — 4px grid: `unit 4`, `containerPadding 20`, `gutter 16`, `stackSm 8`, `stackMd 16`, `stackLg 24`, `minTapHeight 48`.

`core/theme/app_shapes.dart` — `cardRadius 22`, `sheetTopRadius 24`, `inputRadius 12`, `otpBoxRadius 12`, `photoSlotRadius 20`; prebuilt `BorderRadius` for card/input/photoSlot, a `RoundedRectangleBorder` sheet (top-only), and `pill = StadiumBorder()`.

`core/theme/app_colors.dart` — brand: `marigold #FF8A3D`, `dhakaMaroon #8C1D3F`, `kathmanduInk #1C1B29`, `ricePaper #FFF8ED`, `trailGreen #2E7D5B`, `ashGrey #8A8794`. Surfaces: `promptCardBg #F5EEDD`, `surface #FCF8FF`, `surfaceContainer #F0EBFF`, `outlineVariant #DDC1B3`, `error #BA1A1A`, `errorContainer #FFDAD6`. Aliases: primary=marigold, premium=dhakaMaroon, success=trailGreen. `photoScrim` = vertical gradient, transparent→`#B31C1B29` (Ink @70%) with stops `[0.55, 1.0]`.

`core/theme/app_text_styles.dart` — Sora for brand, Manrope for utility, both via `google_fonts` (network-fetched, not bundled), with a Noto Sans Devanagari fallback probe. Scale: `displayHeadline` 32/40 w800 ls −0.64, `headlineLg` 24/32 w700, `headlineMd` 20/28 w700, `cardName` 24/30 w700 white, `buttonLabel` 16/24 w600, `bodyLg` 18/26 w400, `body` 16/24 w400, `label` 14/20 w600, `caption` 12/16 w500 ashGrey.

`core/theme/app_theme.dart` — Material 3 light only (no dark theme, no theme extensions, no ThemeMode switch). Scaffold bg ricePaper, pill ElevatedButton with `minimumSize: Size.fromHeight(48)`, filled inputs with 2px marigold focus ring, marigold-tinted stadium chips.

---

## 11. Features Dobato Has That Milan Lacks

I read Milan's backend models, services, blueprints, and `mobile/lib` to make this comparison concrete rather than assumed.

Genuinely missing from Milan:

1. **Virtual gifts + coin wallet economy.** Dobato has `GiftTransaction`, `User.coinBalance` (250 free), a gift catalog, coin packages, `POST /gifts/send` with atomic debit and a 402 insufficient-funds contract, `POST /wallet/topup`, and a full Flutter gifts store with a top-up sheet. Milan has zero gift/coin/wallet surface — I grepped the whole backend and `mobile/lib` and found only anti-scam prompt text mentioning gift cards. Milan's only adjacent concept is `SaathiHeartLedger` (AI-companion affection hearts, earned not bought). If you want gifting, take Dobato's transaction pattern but reject its top-up: credit coins only after a verified payment, which Milan already knows how to do via `PaymentSubmission` + admin approval.
2. **A normalized interests catalog.** Dobato has `Interest` + `UserInterest` join table with icon/category, a seeded 31-tag taxonomy, admin-creatable tags, `PUT /interests/me` with dedup/existence/limit validation, and chip-selection UI. Milan stores interests as a bare JSON array on `Profile` (`user.py:58`) with no canonical vocabulary — meaning no typo-proof filtering, no icons, no category grouping, and `_shared_interests` in `matching_service.py` compares raw strings.
3. **Email/password auth as a first-class path.** Dobato: bcrypt passwords, hashed-refresh-token rotation with reuse detection, `forgot-password`/`reset-password` via a `Verification` token table, `change-password`, and an email-verification magic link. Milan is OTP-only (phone or email code) with no password concept, so there is no "reset my password" flow to speak of and refresh tokens aren't rotated or revocable server-side (`auth/__init__.py:116-120` just mints a new access token).
4. **A tracked trust score.** Even in its crude form (base 20 + verification/completeness/photo bonuses − 15/report), Dobato persists a per-user integer. Milan has no equivalent scalar at all — I grepped `trust_score`/`trustScore` and got zero hits. Milan has richer raw signals (`LivenessCheck`, `FaceEmbedding` with cosine similarity and duplicate detection, `ScamFlag` with confidence/risk_level, `ModerationEvent`) but never rolls them into a single reputation number.
5. **Redis-backed socket presence with multi-device fan-out.** Dobato tracks a Redis SET of socket ids per user with TTL, `SCAN`-based global online count, and a `@socket.io/redis-adapter` for cross-instance broadcast. Milan's presence is a single `presence:heartbeat` handler that joins `user:{id}` and re-broadcasts `{online:true}` (`presence_events.py`), with `async_mode="threading"` and no Redis adapter — so presence is per-process and does not survive multiple workers.
6. **Swagger/OpenAPI documentation.** Dobato annotates nearly every route (`@ApiOperation`, `@ApiResponse`, response schemas) and serves `/api/docs`. Milan has no generated API docs.
7. **Declarative request validation + a uniform response envelope.** Dobato's `class-validator` DTOs with `whitelist`+`forbidNonWhitelisted` reject unknown fields globally, and `TransformInterceptor` guarantees `{success, statusCode, message, data, meta}` on every response. Milan validates ad hoc inside each view (`if not (6 <= len(reference_id) <= 120)`) and each endpoint hand-rolls its JSON shape.
8. **Cloudinary-backed image pipeline with a graceful dev fallback.** Dobato streams uploads to Cloudinary and, when `CLOUDINARY_CLOUD_NAME` is unset, returns a random Unsplash URL so the app still renders. Milan's `media_service` writes to a local `instance/uploads` directory served by Flask — fine for dev, not a CDN.
9. **Soft delete + account lifecycle.** Dobato has `User.deletedAt` filtered in every repository read plus `AccountStatus{PENDING,ACTIVE,SUSPENDED,DEACTIVATED}` and admin ban/unban/delete/verify. Milan has `account_status` and admin status-setting, but no soft-delete tombstone, so "delete my account" has no reversible implementation.
10. **Pagination as a shared convention.** Dobato returns `{total, page, limit, totalPages}` from users/matches/messages/notifications/reports/admin. Milan has `utils/pagination.paginate` but applies it only to `/matches`; discovery hard-caps at 30 candidates from a 400-row pool with no cursor.
11. **BullMQ job-queue scaffolding with retry/backoff semantics.** Worth noting only as a pattern — Milan's Celery setup with a real `beat_schedule` and a non-blocking `dispatch()` helper is strictly better than Dobato's unregistered no-op processors. Do not port this one.

Where Dobato is behind Milan (so you don't accidentally copy backwards): Milan already has server-enforced swipe quotas with a Kathmandu-local day ledger and atomic increments, superlike notes / message-before-match, audit-preserving rewind with quota refund, time-boxed `Boost` with a ranking multiplier, `TopPick` curation, a real `who_liked_me` with premium gating, a weighted compatibility score with AI-generated match reasons (isolated off the request path), a proper `Block` table, notification categories with per-day caps and predicted send windows, `DeviceToken` push registration, chat themes/presets, snaps, reels/stories/circles/audio rooms, liveness + face-embedding verification, manual-QR payment submissions with fraud flags and an immutable audit log, tier limits (`free/basic/plus/premium`), i18n (en/ne with per-run Devanagari font swapping), dark theme, and a11y/reduced-motion tokens. Dobato has none of those.

Two Dobato behaviors to explicitly avoid porting: the wallet top-up that mints coins without verifying payment, and the `join-room` socket handler that lets any authenticated client subscribe to any match's messages.

Research complete. Rewriting the plan with everything, then implementing directly.

Plan updated with all verified defects. Starting implementation now — backend data model first, since everything depends on it.

Plan updated with hard evidence. Starting implementation with the schema layer.

Starting with the schema. Models first, then the migration.

Now the saathi model additions:

Now the session columns:

Now the memory item recency field and the open-loop plan fields:

---

**User**

continue resume

**Assistant**

Continuing with the schema work.

Duplicate column from an interrupted edit — removing it.

Now the user/profile/match model changes.

Now the interests catalog + profile views models, and match expiry.

Now update the imports and add `last_active_at` to Profile:

Now the Profile activity field and Match expiry:

Now the Match expiry fields:

Now update the models `__init__.py` exports:

Now the migration.

Schema done. Now the persona bible — every character becomes a fu

---

**User**

continue

**Assistant**

Now the persona bibles — the core of making them people.

Now the render function for the bible:

Persona bibles done — all 11 characters, including the four ex-coaches. Now the language engine, which is the direct fix for the screenshot.

Now the EWMA accumulator and prompt renderer:

Now the directive renderer and the post-draft enforcement check.

Let me verify the language engine behaves correctly on the exact screenshot case before building on top of it.

Language engine verified: `hlw timro name k ho` → roman/Nepali/informal/x-style, and both failure modes from the screenshot (Devanagari reply, formal `tapailai`) are now caught and re-rolled.

Now the compaction half of the context engine:

Now the realism engine — her day, her timing, her bursts.

Now the burst segmentation — replacing the coin flip that almost never fired.

Segmentation dropped the trailing question — content loss. Fixing.

Language engine, day/timing/burst engine, persona bibles and context engine all verified working. Now the prompt builder that replaces the coach template.

Now the main prompt builder:

Now the core orchestrator — rewiring `saathi_respond_full` to use these engines.

Now the orchestrator — replacing the whole `saathi_respond_full` body:

Now the core orchestrator — replacing the old two-path responder with a single companion pipeline.

Now the unified delivery helper — one write path for every companion message (fixes A1.8, auto-texts never reaching the inbox).

Now the initiative engine — the scored autonomous texting.

Now the mock twin — dev, tests and no-API-key production all run through this.

---

**User**

continue as per plan  dont run tests now first finish coding  and notify me then start tests

**Assistant**

I'll keep coding through the plan and only run verification at the end.

Now the Celery tasks for the initiative engine, deferred replies, compaction and match expiry.

Now replacing the old proactive task with a delegation, and fixing the socket typing bug.

Now the status posts task, which still references `companion_mode="romantic"` (now `dating`), and the mood decay.

Now the character roster — replacing the coach/romantic split with one people-only roster.

Now removing the two dead prompt templates and the old character dicts.

Now I'll remove the two dead prompt templates and the old roster dicts.

Now removing the two legacy roster dicts (`CURATED_CHARACTERS`, `ROMANTIC_CHARACTERS`) that `CHARACTERS` replaced.

I need to delete lines 298-496 (the two legacy character dicts). Let me do it precisely.

Now let me clean up the remaining legacy prompt builders and functions in `groq_service.py`.

Now the saathi blueprint — roster seeding, character DTOs, and removing the practice/romantic fork.

---

**User**

continue

**Assistant**

Now the saathi blueprint: remove the AI suffix, fix `companion_mode` references, and rewire the session DTO for presence.

---

