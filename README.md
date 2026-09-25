# Milan (मिलन)

Nepal-first, AI-native dating and connection app. Built from the seven-document
spec in this repo root (`00`–`06`). The app is named **Milan**; the horoscope
feature is **Kundali Mode** — never the old working titles.

## Layout

| Path      | What it is                                                              | Spec      |
| --------- | ----------------------------------------------------------------------- | --------- |
| `backend/`  | Flask + SQLAlchemy + Celery + Flask-SocketIO API; all AI behind `app/services/groq_service.py` (real Groq when a key is set, deterministic mock algorithms otherwise) | docs 4+5 |
| `mobile/`   | Flutter app (Riverpod 2.x, go_router, bundled Sora/Manrope/Noto Devanagari fonts) | doc 3 |
| `web/`      | Next.js marketing site (`/`) + admin dashboard (`/admin`)               | doc 6     |
| `0*.md`     | The seven spec documents                                                | doc 0     |

## Live stack status (verified)

```
Flask API   http://localhost:5000        (binds 127.0.0.1; Android emulator uses 10.0.2.2:5000)
Web         http://localhost:3000        marketing site + /admin dashboard
Postgres    localhost:5432/milan         role milan / password milan  (docker: sajilo_postgres)
Redis       localhost:6379               Celery broker
```

- CORS allows `http://localhost:3000` by default in dev (prod stays locked to
  milan.app domains via `MILAN_CORS_ORIGINS`).
- **Mock-AI mode is active whenever `GROQ_API_KEY` is unset** (or force with
  `MILAN_MOCK_AI=1`): bios, prompt grading, icebreakers, match explainers,
  Kundali guna-milan narrative, Saathi coaching, session-memory extraction,
  scam heuristics, moderation heuristics, STT transcript and WAV-synthesising
  TTS all run as deterministic local algorithms — the whole product works
  end-to-end offline from any external AI vendor.
- Media uploads persist to `backend/instance/uploads/` and are served from
  `/media/<key>` in dev (S3/CDN takes over when Spaces credentials exist).
- Push delivery logs via `MockPushBackend` until OneSignal creds are set.

## Running it

```bash
# one-time DB bootstrap (creates schema via Alembic migration 0001)
cd backend && .venv/bin/flask --app wsgi:flask_app db upgrade

# API
cd backend && MILAN_ENV=dev .venv/bin/python wsgi.py          # > server.log

# Web
cd web && npm install && npm run dev            # port 3000

# Mobile (Android emulator hits 10.0.2.2:5000 automatically)
cd mobile && flutter run
# physical device:
#   flutter run --dart-define=MILAN_API_BASE_URL=http://<LAN-IP>:5000/api/v1 \
#               --dart-define=MILAN_WS_URL=http://<LAN-IP>:5000
```

### Admin access

1. Sign up in the app or via `/api/v1/auth/otp/request`. Production codes are
   never written to server logs; configure the SMS/email providers or a
   test-only delivery adapter for local verification.
2. `cd backend && .venv/bin/flask --app wsgi:flask_app seed-admin <phone>`
3. Log in at `http://localhost:3000/admin/login` — moderator/admin/founder
   roles are re-verified server-side on every call.

## Verification status

- **Backend:** `.venv/bin/python -m pytest tests/` → 48 passing.
- **Live E2E:** `.venv/bin/python live_test.py` → 44 checks over real HTTP
  against the running server + real Postgres (auth/age-gate, matching,
  chat+moderation-defer, personalization scope resolution, Saathi coaching +
  voice WAV, kundali, recap, billing HMAC signatures, media persistence,
  admin role gating).
- **Mobile:** `flutter analyze` clean · `flutter test` → 15 passing
  (theme resolution order, contrast gate, ChatBubble variants,
  ThemePickerSheet tabs/scope indicator).
- **Web:** `npm run build` → all 19 routes compile.

## Guardrails enforced server-side (docs 1 §5 / 4 §8)

Liveness selfies processed in-memory then discarded (only embedding +
pass/fail stored); every inbound message passes moderation before broadcast
with async re-scan; Saathi outputs fail closed when moderation is unavailable;
proactive Saathi messages route through the same caps as every notification
and default OFF; custom wallpaper uploads are moderated despite being
private-per-viewer; crisis indicators surface Milan's resource card and never
build memory items.
