# Milan v2 — Backend (Python/Flask) Build Prompt

> **Document 4 of 7.** Paste-into-AI-code-editor prompt for the backend. Pair with document 5 for the exact Groq AI service contracts and document 1 §5 for the non-negotiable safety/ethics rules this backend must enforce server-side (client-side enforcement in the Flutter app is not sufficient on its own).

---

## Prompt starts here

You are building the backend for **Milan v2**. Stack: **Flask, SQLAlchemy, PostgreSQL, Redis, Celery, Flask-SocketIO, Gunicorn**, deployed behind **nginx** on a **DigitalOcean Ubuntu droplet** — this matches the existing infrastructure conventions this team already uses (shared with the related Ashlya product), do not introduce a different stack (no Django, no FastAPI, no MongoDB).

### 1. Architecture overview

```
app/
  __init__.py              // app factory, extension init (db, socketio, celery, limiter)
  config.py                // env-based config classes (Dev/Staging/Prod)
  extensions.py            // db, migrate, jwt, socketio, limiter, cache singletons
  models/
    user.py                // User, Profile, Photo, VideoIntro
    verification.py        // LivenessCheck, FaceEmbedding (dup-detection)
    matching.py             // Swipe, Match, Prompt, PromptAnswer
    chat.py                  // Message, Snap, TypingEvent (ephemeral, Redis-backed not DB)
    jhalak.py                // Reel, ReelLike, Story, Circle, CircleMembership, LiveAudioRoom
    saathi.py                // SaathiCharacter, SaathiSession, SaathiMessage, SaathiMemoryItem
    safety.py                // Report, Block, ScamFlag, ModerationEvent
    notifications.py         // Notification, NotificationPreference, DeviceToken
    billing.py                // Subscription, Payment, PaymentMethod
    personalization.py         // ChatTheme — new in this revision, see §2
  blueprints/
    auth/                    // phone/OTP, JWT issue/refresh
    profile/
    discovery/
    matching/
    chat/
    jhalak/
    saathi/
    safety/
    notifications/
    billing/
    personalization/          // chat theme CRUD — new in this revision, see §3
    admin/                    // moderation queue, analytics — consumed by document 6's Next.js admin
  services/
    groq_service.py           // see document 5 — all Groq calls go through this module, nowhere else
    matching_service.py        // scoring/ranking logic
    moderation_service.py       // Llama Guard + scam-pattern classifier orchestration
    notification_service.py     // predictive send-time, segmentation, frequency caps (doc 1 §4.8)
    verification_service.py      // liveness check orchestration, face-embedding dedup
    media_service.py              // upload handling, compression trigger, CDN URLs — also handles custom wallpaper uploads (§3)
    payment_service.py             // eSewa/Khalti/Fonepay/ConnectIPS adapters
  tasks/                            // Celery tasks
    media_tasks.py                  // video transcode/compress
    moderation_tasks.py              // async message scan, scam-flag scan
    notification_tasks.py             // scheduled sends, proactive Saathi nudges
    matching_tasks.py                  // nightly batch re-ranking
    verification_tasks.py               // async face-embedding dedup scan
  sockets/
    chat_events.py                     // Flask-SocketIO event handlers
    presence_events.py
    audio_room_events.py
  utils/
    validators.py, serializers.py, pagination.py
migrations/                              // Alembic
tests/
```

### 2. Data models (key fields only — expand with standard audit columns `id`, `created_at`, `updated_at` on all)

| Model | Key fields |
|---|---|
| `User` | phone (unique), password_hash (optional, phone-OTP-primary), is_verified, date_of_birth, gender, intent_mode (`serious`/`casual`), discreet_mode (bool), account_status |
| `Profile` | user_id, display_name, bio, prompts (via `PromptAnswer`), interests (array), location (PostGIS point or lat/lng), horoscope_details (nullable, opt-in) |
| `Photo` / `VideoIntro` | user_id, url, order_index, moderation_status |
| `LivenessCheck` | user_id, status, **raw selfie is processed then deleted — store only the resulting face embedding + pass/fail result**, per document 1 guardrail #7 |
| `FaceEmbedding` | user_id, embedding_vector, used only for duplicate-account detection, not stored alongside identifiable image data |
| `Swipe` | swiper_id, target_id, direction (`like`/`pass`/`superlike`), created_at |
| `Match` | user_a_id, user_b_id, matched_at, compatibility_score, match_reason_text (AI-generated, cached) |
| `Prompt` / `PromptAnswer` | prompt bank + per-user selected answers |
| `Message` | match_id, sender_id, body, media_url (nullable), is_ai_suggested (bool), read_at |
| `Snap` | match_id, sender_id, media_url, view_mode (`single_view`/`24h`), viewed_at, expires_at, screenshot_detected (bool) |
| `Reel` | user_id, video_url, prompt_id (nullable), like_count, is_duet, original_reel_id (nullable) |
| `Story` | user_id, media_url, posted_at, expires_at (24h) |
| `Circle` / `CircleMembership` | name, category, member list |
| `LiveAudioRoom` | circle_id, scheduled_at, status, host_id |
| `SaathiCharacter` | name, persona_description, system_prompt_template_id (references doc 5 templates), illustrated_avatar_url, default_theme_preset_id (nullable, references `ChatTheme` preset catalog — doc 2 §2.7.2) |
| `SaathiSession` | user_id, character_id, started_at, last_proactive_message_at, proactive_messages_today (int, resets daily), is_paused |
| `SaathiMessage` | session_id, role (`user`/`saathi`), content, created_at |
| `SaathiMemoryItem` | session_id, summary_text, category, created_at, user-deletable |
| `Report` | reporter_id, target_id, target_type (`user`/`message`/`reel`), reason, status |
| `Block` | blocker_id, blocked_id |
| `ScamFlag` | message_id or session_id, pattern_matched, confidence, reviewed (bool) |
| `Notification` | user_id, category, title, body, sent_at, opened_at |
| `NotificationPreference` | user_id, category, enabled (bool), max_per_day |
| `DeviceToken` | user_id, platform, token |
| `Subscription` | user_id, tier, started_at, renews_at, payment_method |
| `Payment` | user_id, provider (`esewa`/`khalti`/`fonepay`/`connectips`), amount_npr, status, provider_ref |
| `ChatTheme` | user_id, scope (`global`/`match`/`saathi_session`), scope_id (nullable — `match_id` or `saathi_session_id` when scope isn't `global`), wallpaper_type (`preset`/`solid`/`gradient`/`custom_upload`/`ai_generated`), wallpaper_value (preset id, hex color(s), or media URL), bubble_color_sent, bubble_color_received, bubble_shape (`rounded`/`compact`), doodle_overlay_id (nullable), text_scale (float, nullable — null means "inherit OS setting"), dark_mode_brightness (float 0–1, nullable). One row per `(user_id, scope, scope_id)` — see §3 for resolution logic. |

### 3. REST API surface (representative — extend per screen inventory in document 2)

| Method | Path | Purpose | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/otp/request` | Send OTP via Sparrow SMS | Public |
| POST | `/api/v1/auth/otp/verify` | Verify OTP, issue JWT pair | Public |
| POST | `/api/v1/auth/refresh` | Refresh access token | Refresh token |
| GET/PUT | `/api/v1/profile/me` | Own profile CRUD | User |
| POST | `/api/v1/profile/bio/generate` | AI bio assistant (→ `groq_service`) | User |
| POST | `/api/v1/profile/prompts/feedback` | AI prompt grading (→ `groq_service`) | User |
| POST | `/api/v1/verification/liveness` | Submit liveness selfie, returns pass/fail | User |
| GET | `/api/v1/discovery/candidates` | Paginated candidate queue | User |
| POST | `/api/v1/discovery/swipe` | Record swipe, returns match if mutual | User |
| GET | `/api/v1/discovery/kundali/:matchId` | Horoscope compatibility narrative (Kundali Mode) | User |
| GET | `/api/v1/matches` | List matches | User |
| GET | `/api/v1/matches/:id/messages` | Message history (paginated) | User |
| POST | `/api/v1/matches/:id/icebreakers` | AI icebreaker suggestions (→ `groq_service`) | User |
| POST | `/api/v1/matches/:id/snaps` | Upload ephemeral snap | User |
| POST | `/api/v1/matches/:id/share-date` | Create Share My Date record + notify trusted contact | User |
| GET | `/api/v1/jhalak/feed` | Cursor-paginated reel feed | User |
| POST | `/api/v1/jhalak/reels` | Upload reel | User |
| POST | `/api/v1/jhalak/reels/:id/duet` | Upload duet response | User |
| GET/POST | `/api/v1/jhalak/stories` | Story feed / post | User |
| GET | `/api/v1/circles` | List circles | User |
| POST | `/api/v1/circles/:id/join` | Join circle | User |
| GET | `/api/v1/saathi/characters` | List curated personas | User |
| POST | `/api/v1/saathi/:characterId/sessions` | Start/resume session | User |
| POST | `/api/v1/saathi/sessions/:id/messages` | Send message (→ `groq_service`, moderated) | User |
| GET/DELETE | `/api/v1/saathi/sessions/:id/memory` | View/delete stored memory items | User |
| PUT | `/api/v1/saathi/sessions/:id/settings` | Proactive-message frequency/pause | User |
| POST | `/api/v1/safety/reports` | File a report | User |
| POST | `/api/v1/safety/blocks` | Block a user | User |
| GET/PUT | `/api/v1/notifications/preferences` | Notification category settings | User |
| GET/PUT/DELETE | `/api/v1/personalization/theme` | Get/set/reset the user's **global default** `ChatTheme` | User |
| GET/PUT/DELETE | `/api/v1/personalization/theme/:scope/:scopeId` | Get/set/reset a **scoped override** (`scope` = `match`\|`saathi_session`) — DELETE reverts that scope to the global default | User |
| POST | `/api/v1/personalization/theme/upload` | Upload a custom wallpaper image (→ `media_service`, compressed + moderated before it can be referenced by a `ChatTheme` row) | User |
| POST | `/api/v1/billing/checkout` | Start eSewa/Khalti/Fonepay/ConnectIPS checkout | User |
| POST | `/api/v1/billing/webhooks/:provider` | Payment provider webhook receiver | Signed webhook |
| GET | `/api/v1/admin/moderation/queue` | Human moderation queue | Admin |
| GET | `/api/v1/admin/analytics/overview` | DAU/MAU/match-rate/revenue dashboard feed | Admin |

### 4. Real-time (Flask-SocketIO)

Namespaces/rooms: one room per `match_id` for chat, one per `circle_id`+`room_id` for live audio signaling, one per `user_id` for presence broadcast.

| Event (client→server) | Event (server→client) | Notes |
|---|---|---|
| `chat:join` | `chat:message` | Join a match room; new messages broadcast to room |
| `chat:typing_start` / `chat:typing_stop` | `chat:typing` | Debounce client-side (≤1 event/2s) |
| `presence:heartbeat` | `presence:update` | Online/last-active status |
| `audio_room:join` / `audio_room:raise_hand` | `audio_room:state` | Backing store for live audio room UI (screen 45) |

Every inbound chat message passes through `moderation_service.py` **synchronously before broadcast** for a fast Llama Guard pass (low-latency Groq model), with a slower, more thorough async re-scan via `moderation_tasks.py` for pattern-based scam detection that doesn't need to block delivery.

### 5. Groq AI integration boundary

**All** Groq API calls live in `services/groq_service.py` — no blueprint or task calls the Groq SDK directly. This module exposes typed functions (`generate_bio()`, `grade_prompt()`, `suggest_icebreakers()`, `saathi_respond()`, `moderate_content()`, `transcribe_audio()`, `classify_scam_pattern()`) whose internals — model selection, system prompts, safety wrapping — are fully specified in document 5. This isolation matters for two reasons: it makes swapping/adding a fallback provider a one-file change, and it makes it possible to unit-test every AI-touching endpoint by mocking one module. Note: any optional AI-generated-wallpaper feature (document 1 §4.9, document 2 §2.7.2) is explicitly **out of scope for `groq_service.py`** — it requires a dedicated image-generation provider and, if built, should live in its own `services/image_gen_service.py` with the same moderation-before-return discipline as `groq_service.py`, not be shoehorned into the Groq boundary.

### 6. Notification service (document 1 §4.8)

`notification_service.py` implements:
- `predicted_send_time(user_id)` — reads the user's historical notification-open timestamps (stored on `Notification.opened_at`) and returns the best send window; falls back to a sensible default (7–9pm local) for new users with no history.
- `should_send(user_id, category)` — checks `NotificationPreference` and the category's daily cap before any send is queued, called by every task in `notification_tasks.py` including the Saathi proactive-message scheduler.
- `segment_for(user_id)` — classifies the user into a behavioral segment (new match/no message, liked-no-reply-24h, high-views-no-matches, dormant, etc.) to select notification copy/cadence.

### 7. Payments

`payment_service.py` defines one adapter class per provider (`EsewaAdapter`, `KhaltiAdapter`, `FonepayAdapter`, `ConnectIpsAdapter`) implementing a shared interface (`initiate(amount, user)`, `verify_webhook(payload, signature)`). Never store raw wallet/card credentials — only provider transaction references. All webhook endpoints verify provider signatures before processing and are idempotent (safe to receive the same webhook twice).

### 8. Security & compliance

- **Auth:** JWT access (short-lived, ~15min) + refresh (long-lived, rotated on use) via `flask-jwt-extended`.
- **Rate limiting:** `Flask-Limiter` on all public and write endpoints; stricter limits on `/auth/otp/request` (prevent SMS-bombing abuse), on `/saathi/*/messages` (cost control on Groq usage, independent of the proactive-message cap which is a UX/ethics control, not a cost control), and on `/personalization/theme/upload` (custom wallpaper uploads still cost storage/CDN/compression resources even though they're a lower-risk endpoint).
- **Encryption at rest:** sensitive columns (phone, location) encrypted at the application layer or via Postgres column encryption; liveness selfies are never persisted past the verification job (document 1 guardrail #7) — process in-memory/temp storage, store only the resulting embedding and pass/fail.
- **CORS:** locked to the known mobile app origin and the Next.js web app origin from document 6.
- **Audit logging:** all moderation actions, report resolutions, and admin access to user data are logged with actor + timestamp for accountability.
- **Custom wallpaper uploads:** even though a `ChatTheme` row and the wallpaper image behind it are private-per-viewer (document 2 §2.7.1) and never shown to another user, they are still user-uploaded media and must pass the same moderation check (`moderation_service.py`) as a profile photo before the upload is marked usable — private is not the same as unmoderated.

### 9. Background jobs (Celery, Redis broker)

| Task | Trigger | Purpose |
|---|---|---|
| `transcode_video` | On upload | Compress + generate thumbnail for video intros/reels/snaps |
| `scan_message_async` | On message send | Deeper scam-pattern + policy scan beyond the synchronous fast pass |
| `dedupe_face_embeddings` | On new verification | Cross-check new embedding against existing accounts, flag duplicates |
| `nightly_rerank` | Cron, nightly | Batch-refresh candidate ranking per active user using accumulated swipe/behavior signal |
| `send_scheduled_notifications` | Per-user predicted send time | Delivers queued notifications respecting caps |
| `saathi_proactive_check` | Cron, hourly | Evaluates which active Saathi sessions are eligible for a capped proactive message and queues them through the notification service — never bypasses `should_send()` |
| `expire_snaps_and_stories` | Cron, every few minutes | Purges expired ephemeral media from storage, not just hides it |
| `moderate_wallpaper_upload` | On `/personalization/theme/upload` | Runs the same moderation pass as profile photos on a newly uploaded custom wallpaper before it can be referenced by a `ChatTheme` row |

### 10. Deployment

- Gunicorn (with `eventlet` or `gevent` worker class for Flask-SocketIO compatibility) behind nginx, systemd-managed, on the existing DigitalOcean Ubuntu droplet convention.
- Alembic migrations gated in CI; no manual schema edits in production.
- Environment-based config classes; secrets (Groq API key, JWT secret, payment provider keys) via environment variables, never committed.
- Media storage: object storage (DigitalOcean Spaces or equivalent S3-compatible) behind a CDN, not local disk, so the app survives droplet redeploys.

Proceed to document 5 for the full Groq AI service specification referenced throughout this document, and document 6 for the Next.js web app and admin dashboard that consumes the `/api/v1/admin/*` routes above.
