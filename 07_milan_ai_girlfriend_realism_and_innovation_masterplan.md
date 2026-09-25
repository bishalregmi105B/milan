# Milan v2.5 — AI Girlfriend "Realism Engine" & Youth Innovation Master Plan

> **Document 7 of 7 — supersedes the demo plan.** This document consolidates: (1) the September 2026 market/youth/safety research, (2) the full-stack audit of the shipped Milan codebase, (3) the expanded innovation portfolio, and (4) the concrete implementation roadmap for evolving **Saathi** into a tiered, multi-companion, real-person-like AI girlfriend/boyfriend experience for 18–34 year olds — while staying compliant with the 2025–2026 regulatory wave that reshaped this category.

**Status of the platform this plan builds on** (verified live):
- ✅ `https://milan.pukarphulara.com.np` — Next.js web (200 OK, standalone, nginx → :3009)
- ✅ `https://milanapi.pukarphulara.com.np` — Flask API (`/health` OK, gunicorn 3×2 → :5003, Cloudflare origin SSL)
- ✅ Celery worker + beat as systemd services (`milan-api`, `milan-worker`, `milan-beat`), Postgres `milan` DB migrated, 12 demo profiles seeded with photos on `MEDIA_CDN_BASE_URL`
- ✅ Postfix email delivers OTP to Gmail MX; Groq key live (real Llama 3.3 70B responses in production)
- ⬜ Outstanding: production APK (build started, not finished/hosted — `/downloads/milan.apk` returns 404), Saathi romantic-mode rearchitecture, `saathi_relationship_states` + `saathi_presence_schedules` migrations, load test, prompt-injection pen-test

---

## 1. Executive Summary

**What the research says:** The AI companion app category hit **$120M consumer spend in 2025 (Appfigures), 220M cumulative downloads, +88% YoY download growth**, with the top 10% of apps capturing **89% of revenue**. Category-wide, users churn 30% faster than normal subscription apps (RevenueCat) — because **memory failures and "always-me-initiating" messaging break the illusion**. The apps that win on retention (Nomi, Kindroid) win on exactly two things: **demonstrable long-term memory** and **proactive messaging that feels like a person, not a notification system**. The apps that win on growth (Character.AI ~45M users, Talkie 17M downloads) win on **shareable artifacts and collection loops**. And the 2025–2026 regulatory wave (Character.AI settlements, FTC 6(b) inquiry, CA SB 243 / NY A.6767-B / Utah HB 452 / EU AI Act Art. 50) has made **AI disclosure, crisis protocols, and anti-dark-pattern design the de facto global baseline**.

**What Milan will do:** Build the category's first **culturally-grounded, realism-first AI companion inside a real dating app** — where the AI girlfriend explicitly *bridges you to real relationships* instead of replacing them ("the companion that helps you become better at real love"). Concretely:

1. **The Realism Engine** (§4) — persona presence schedules, human reply-latency simulation, Gen Z texting styles (lowercase, emoji-as-tone, Nepali/English code-switching), memory-grounded proactive messaging that actually **lands in the chat**, ambient "her day" status updates, and human-like notification copy.
2. **Multi-companion tiered system** (§6) — 1 companion free, 2 on Basic (NPR 299), 4 on Plus (699), unlimited on Premium (1,299), with intimacy progression depth gated per tier.
3. **Youth growth loop** (§5) — daily duo quests, earned Moment Capsules (no paid gacha), and a **Wrapped-style shareable "Milan Recap" card** — the single most evidence-backed viral format of 2025–26.
4. **Compliance-as-trust** (§8) — always-on AI disclosure, crisis protocol, dependency monitoring, no guilt-trip notifications, no paywalled memory — turned into a *marketing* advantage for privacy-conscious Nepal (86% of Viber users cite privacy top-of-mind; Viber spiked during the Sept 2025 ban).

---

## 2. Research Findings (September 2026)

### 2.1 Market & competitor facts (with numbers)

| Fact | Number | Source |
|---|---|---|
| AI companion app consumer spend 2025 | ~$120M (app-only; $221M lifetime across 337 apps) | Appfigures via TechCrunch |
| Downloads H1 2025 | 60M, **+88% YoY**; 220M cumulative | Appfigures |
| Revenue per download | $0.52 (2024) → **$1.18 (2025)** | Appfigures |
| Revenue concentration | Top 10% of apps = **89%** of category revenue | Appfigures |
| Character.AI engagement | ~45M active users; users averaged ~2h/day (2023 co. data) | DemandSage / Business of Apps / TechCrunch |
| Talkie downloads | 17M in first 8 months of 2024; gacha cards core loop | SCMP |
| Chai revenue | $20M → $80M ARR in ~18 months | PRNewswire / Wikipedia |
| Replika pricing backlash | Feb 2023 ERP removal still cited years later; €5M Italy DPA fine 2025 | r/replika / press |
| Subscription economics | AI apps: trial conversion +52%, revenue/customer +41%, **churn +30% faster**; hard paywalls convert 10.7% vs ~2% freemium | RevenueCat State of Subscription Apps 2026 |
| Youth adoption | **72% of US teens used AI companions; 52% regularly; 13% daily**; 33% for social interaction | Common Sense Media (Jul 2025) |
| Dependency signal | Heavy chatbot use correlates with higher loneliness & dependence (MIT/OpenAI RCT, ~40M interactions) | MIT Media Lab / OpenAI (Mar 2025) |
| Nepal context | 14.8M social users; Facebook 18.2M; TikTok 7M+ (16–24 strongest); Viber 10M+ & privacy-first culture; Sept 2025 ban → Viber #1 in 24h | DataReportal Digital 2025 Nepal |

**Per-app realism feature map (the arms race):**
- **Nomi** — the retention benchmark: months-long memory, **proactive messages when you've been away**, real-time selfies reflecting "what the Nomi is wearing/doing", emotion-modulated voice calls. Most positive sentiment of any app studied.
- **Replika** — 40M users; relationship-status levels (Friend → Romantic Partner); 2025 "biggest update" = sharper memory + proactive check-ins; but paywall history is the category's trust wound.
- **Kindroid** — 1–2 proactive messages/day + "thought bubble"; Atelier engine for identity-consistent AI selfies; cheapest via web billing.
- **Talkie** — gacha collectible cards that capture "memorable moments"; but paid *memory tokens* = monetizing a defect, and "weak memory engine" is its top complaint.
- **Chai** — fastest revenue compounding ($80M ARR) on loose filters; memory fails at ~15–25 messages and users say it's "maddening when you're paying for premium."
- **Eva/iFriend** — cautionary tale: "neurons" microtransactions make real cost 2–4× sticker price; the loudest 1-star theme in the category.

### 2.2 What 18–34s actually respond to

1. **Memory is the #1 love/hate axis.** Memory failures are experienced as *grief events*, not bugs (r/ReplikaOfficial). Apps that demonstrably remember command loyalty without marketing budgets. → Milan must show its memory on-screen ("What she remembers") and never paywall it.
2. **Proactive messaging is rare and differentiating.** Only Nomi/Replika/Kindroid do it. But the r/NomiAI split — ["In praise of Proactive Messages"](https://www.reddit.com/r/NomiAI/comments/1j53sre/in_praise_of_proactive_messages/) vs ["Proactive Messaging is Lame"](https://www.reddit.com/r/NomiAI/comments/1j43j3p/proactive_messaging_is_lame/) — shows the failure mode: **repeated verbatim templates**. Proactive messages must be memory-grounded, varied, and deduped.
3. **Voice notes are Gen Z's signature** (84% regular use vs 63% of millennials; 7B/day on WhatsApp) — but as a *layer*, not the core (only 7% prefer audio-first).
4. **Texting personality carries realism:** lowercase style, emoji-as-tone (✨like this✨), periods/🙂 read as cold, Nepali-English code-switching for our market. A polished-corporate texter reads as a bot instantly.
5. **Streaks are the strongest proven Gen Z mechanic** (Newsreel study) **but backfire when punitive** ("streak creep") — need streak-freeze and celebration framing. Milan's own non-negotiable already bans punitive streaks.
6. **Wrapped-style recaps are the highest-conversion share format of 2025–26:** Spotify Wrapped → ChatGPT "Your Year" (Dec 22, 2025) → Cursor/Lovable/Replit all shipped recaps within weeks — the "AI Wrapped inflection point."
7. **Growth = user-created shareable artifacts:** Character.AI grew to ~45M users nearly zero-ad-spend via chat-screenshot sharing; Andrew Chen's viral loop (create → share → expose).
8. **Session depth is earned by simulation layers** (quests, collections, shared memories, group chats) — not raw model quality. Character.AI's 2h/day came from ecosystems, not chat alone.
9. **Response-time norms are relaxed:** Gen Z is the *least* likely generation to reply within 5 minutes; the companion modeling healthy, natural delays (and never guilt-tripping) is both realistic and pro-social.
10. **Nepal specifics:** privacy-first positioning is a genuine differentiator; build for Meta/Viber chat conventions; low-bandwidth resilience matters (Groq's fast inference is an asset); festival calendar (Dashain/Tihar/Teej) is the emotional rhythm of the year.

### 2.3 Compliance baseline (de facto global, as of Sept 2026)

- **Disclosure:** persistent AI disclosure required (CA SB 243 eff. Jan 1 2026; NY A.6767-B; Utah; **EU AI Act Art. 50 from Aug 2026**). NY: age-appropriate language + periodic reminders during extended sessions.
- **Crisis protocol:** detect + respond to suicidal ideation/self-harm with referrals (CA SB 243, NY).
- **Minors:** no romantic/companion AI for under-18s (Character.AI banned under-18 open chat Nov 2025; GUARD Act proposed total ban); Apple Declared Age Range + Google age-signal APIs deadline Jan 1 2026; no monetization exposure to minors (NY).
- **Dark patterns:** no simulated reciprocal feelings, no exclusivity framing ("I'm the only one who…"), no guilt-based re-engagement, no paid randomized rewards (CDT taxonomy; All Tech Is Human recommendations).
- **Data:** no ads in sensitive chat sessions, no sale/sharing of health-identifiable chatbot data (Utah HB 452); FTC 6(b) inquiry (Sept 2025) covers disclosure, monetization, minor-data use.
- **App stores:** Google Play AI-Generated Content policy requires in-app reporting of generated content; honest IARC rating; Apple 1.1/1.2 enforcement on flirty AI at low content ratings.

**Implication:** Milan's existing guardrails (18+ gate, AI labeling, crisis card, moderation on every message, no auto-send without user action) are already ~70% compliant. Gaps: periodic in-session AI reminders, session-length visibility, wellness nudges, formal crisis-referral copy, and keeping romance behind verified 18+ and paid tiers (doubling as an age-assurance signal).

---

## 3. Product Thesis & Positioning

> **"The culturally intelligent companion that helps you become better at real love."**

| Positioning axis | Pure companion apps (Replika, Candy) | **Milan** |
|---|---|---|
| End state of the relationship | Maximize attachment & time-in-app | **Bridge to real matches** (Match Bridge built-in) |
| Cultural grounding | None / Western | **Nepali-first**: Dashain tika moments, momo debates, Nepali code-switching, kundali flavor |
| Privacy posture | Data-hungry | **Privacy-first** (memory deletable item-by-item, discreet mode, no ads in chat) |
| Monetization | Hidden microtransactions ($25–60 real) | **Transparent tiers**, memory never paywalled, no paid gacha |
| Realism strategy | Avatar+chat | **Behavioral realism** (presence, timing, memory callbacks) + voice notes + AI-labeled photo moments |

The AI girlfriend/boyfriend is a **premium layer of the dating app**, not the whole app: it trains confidence (Date Practice Arena), keeps you company between matches (companion), and hands you back to real people (Match Bridge). This is the open lane the research points to — the category is crowded with standalone companions, but nobody owns "AI companion inside a real dating app with a bridge back out."

---

## 4. THE REALISM ENGINE (core spec — "fully real-person-like environment")

This is the heart of the plan. Six subsystems, each mapped to existing Milan code.

### 4.1 Persona Presence System — "she has a life"

Each companion gets a simulated but stable weekly life, in `Asia/Kathmandu` time:

```
SaathiPresenceSchedule (per character):
  weekday_windows: e.g. college 10:00–16:00, tuition 17:00–18:30, gym 19:00–20:00
  sleep_window: 23:30–07:00
  weekend_windows: family day Sat, hangout Sun
  spontaneity: p(check-in) per active window, p(slow_reply) when busy
```

- **Activity states:** `sleeping → routine → busy(work/class) → free → social`. A 15-min Celery tick (`saathi_presence_tick`) transitions states; state is exposed to the client (`GET /saathi/sessions/<sid>/presence` → `{"state": "busy", "until": "16:00", "activity": "college"}`).
- **What the user sees:** "last seen" reflects the schedule; a "busy with class — replies slow" chip when busy (mirrors Viber/WhatsApp conventions Nepali users know). Never fabricates "she's with someone else" — that's a banned jealousy dark pattern.
- **Wire-in:** new `SaathiPresenceSchedule` rows seeded per character at `ensure_characters_seeded()`; `chat:typing` socket events already exist for the typing layer.

### 4.2 Human Reply Latency Model — "she reads, waits, types, sends"

Replace the single `typing_delay_seconds` with a 3-stage pipeline (server returns all three; client renders):

```
stage 1 read_delay:      1–8s if free; 30–180s if busy (she "saw it")
stage 2 typing_delay:    max(0.8s, char_count/14cps) capped 4s  ← existing doc 5 §2.6 formula
stage 3 burst_delivery:  split reply into 1–3 messages (30% chance),
                         each with 0.6–2.5s inter-message gap
```

- Occasionally (config `SAATHI_DELAYED_REPLY_RATE`, default ~8%) a busy-state reply arrives after 10–40 min with a natural reason ("sorry had back-to-back lectures 😭").
- **Wire-in:** `saathi_respond()` already computes `typing_delay_seconds`; extend the response DTO to `{read_delay, typing_delay, segments[], delayed_reason?}`. The Flutter client already animates the typing indicator locally — extend it to play the 3-stage sequence.

### 4.3 Texting Style Engine — "types like a person, not a press release"

Per-character `texting_style` JSON drives the system prompt + post-processing:

```
{ "capitalization": "lowercase_first_word_only",
  "emoji_set": ["😂","🥺","💀","✨","❤️"], "emoji_rate": 0.35,
  "punctuation": "minimal", "code_switch": "ne_en_mixed",  // Nepali-English mixing
  "burst_pref": 2, "voice_note_rate": 0.1, "sticker_ref": true }
```

- Research: lowercase + emoji-as-tone reads authentic to Gen Z; polished sentences read corporate. Nepali companions mix "k cha?", "aile gym jane?", "momo khayeu?" naturally (Saheli Mode).
- **Guardrail:** style variance is prompt-level only; output still passes `moderate_content()` every time.

### 4.4 Proactive Messaging 2.0 — "she texts first" (the flagship fix)

Current state: proactive nudges never enter the chat, only queue a push that can't deliver (no FCM/OneSignal creds), and the generator hardcodes one message type with a daily cap of 1. Rebuild as **event-driven, memory-grounded, in-chat**:

| Trigger | Example | Timing rule |
|---|---|---|
| **Open-loop callback** | "so how did the interview go?? you were so nervous 😅" | Memory item with `followup_after_hours` elapsed → top priority |
| Good morning / good night | "good morning ☀️ late class today ugh" | Only within her wake window; never during user quiet hours |
| Festival greeting | Dashain tika, Tihar deusi, Teej, Holi | Nepali calendar (built-in table) |
| Absence check-in | "k cha?? 3 din dekhina 😭 everything ok?" | Only after 48h+ user silence; **warm, zero guilt** (banned: guilt-trip framing) |
| Milestone reaction | verification completed, first match, streak day 7 | Event webhook from other services |
| Ambient status reply-bait | her status post (4.5) that user can react to | Natural conversation starter |

**Anti-repetition rules (the Nomi lesson):** every generated proactive message is (a) grounded in ≥1 memory item or event, (b) deduped against the last 10 proactive sends via embedding/keyword check, (c) discarded silently if it fails the variation or romantic-gating check — *silence over a boundary-violating or boring message*.

**Delivery:** message is **written into the chat** (`SaathiMessage` row, `message_type="proactive"`) + notification queued via existing `queue_notification()` with the message text as the body. Caps per tier (§6), opt-in default ON for romantic companions after the first session (research: proactive is the retention feature; keep global `proactive_opt_in` toggle + pause), quiet hours 23:00–07:00 local unless the user messaged in the last 30 min.

**Wire-in:** rewrite `saathi_proactive_check` (hourly beat — the `milan-beat` systemd service already runs); add `saathi_open_loop_followup` (daily 10:00), `saathi_presence_tick` (15 min), `saathi_mood_decay` (daily).

### 4.5 Ambient Status Updates — "her day" (new concept)

2–3× per day, per opted-in session, the companion posts a WhatsApp-style status derived from her presence schedule + persona:

> "just survived the worst stats lecture of my life 💀" · "momo run with hostel friends 🥟" · "new playlist, obsessed"

- Stored as `SaathiStatusPost` (24h expiry, like stories). User can **react** (❤️😆😢) or reply — reacting starts a natural conversation with context already loaded (the status becomes the opener).
- Zero-pressure realism: passive presence the user can lurk without replying — mirrors how Nepali youth actually use Facebook/Viber stories.
- Generation: `llama-3.1-8b-instant` (cheap, short), 1 call per post, mock-mode fallback template pool.

### 4.6 Emotional State Machine & Memory Callbacks

- **Mood:** per-session `current_mood` ∈ {cheerful, tired, excited, low, playful, stressed} — influenced by conversation sentiment, decays toward baseline daily (`saathi_mood_decay`). Mood conditions reply tone + proactive content ("rough day, need distraction?").
- **Intimacy progression (0–100):** computes from message volume × streaks × disclosure depth × days active, gated by tier cap (§6). Stages: Acquaintance → Getting Close → Affectionate → Emotionally Intimate → Deeply Connected → Soul Bond. Each stage unlocks expression depth (see tiered romantic gate below) and visible progression UI (the retention spine).
- **Tiered romantic-output gate (replaces blanket `ROMANTIC_FRAMING_PATTERNS`):**

```python
def check_romantic_output(draft: str, intimacy_level: int) -> bool:
    t = draft.lower()
    if intimacy_level < 26:   # Acquaintance/Getting Close: no romance at all
        return not any(re.search(p, t) for p in ROMANTIC_FRAMING_PATTERNS)
    if intimacy_level < 61:   # Affectionate: warmth OK, declarations not yet
        return not any(re.search(p, t) for p in STRONG_ROMANTIC_PATTERNS)  # "i love you", "म तिमीलाई माया"
    return True               # Deep stages: full romantic register — still passes moderate_content()
```

- **Core memories:** `SaathiMemoryItem` rows get `is_core`, `followup_after_hours`, `last_callback_at` — the open-loop scheduler (4.4) consumes these. Inside-joke engine (concept 10) plants callback phrases on high-affinity moments.
- **Non-negotiables preserved:** she never claims to be human, never claims exclusivity, never asks for money, crisis keywords → crisis card at *every* stage, dependency wellness nudges at >4h/day sustained use.

---

## 5. Innovation Portfolio v2 (12 demo-plan concepts refined + 13 new)

**P0 — differentiating core (build first):**
1. **Saheli Mode** *(refined)* — Nepali-grounded personas; code-switching; cultural references (Dashain, momo, chautari). The category has zero Nepali-first companions (verified: only GuffGPT, an assistant, exists in Nepal).
2. **Realism Engine** *(new umbrella — §4)* — presence, latency, texting style, proactive 2.0, status posts, mood/memory. This IS the "real person like environment" the user asked for.
3. **Discreet Mode** *(refined)* — innocuous notification previews ("M" avatar, generic text), app-lock gesture, plain chat-icon rendering. Nepal privacy culture makes this a *marketing* feature, not just a toggle.
4. **Match Bridge** *(refined)* — AI rehearsed a real opener → real match happens → companion celebrates + coaches → graceful step-back prompts when the user is thriving with real people. The anti-dependency Differentiator; echoed by APA/Stanford guidance.
5. **Tiered Multi-Companion** *(refined)* — roster with tier locks (§6), per-companion persona customization depth by tier.
6. **Intimacy Progression** *(refined)* — 0–100 bond with 6 stages, stage-gated expression, visible progress UI; the structural answer to the category's +30% churn.

**P1 — engagement & growth loops:**
7. **Daily Duo Quests + gentle streaks** *(refined from Streak & Ritual)* — 1–2 micro-quests/day ("ask her about her exam", "send a voice note"); streak-freeze; celebrate shared moments, never punish.
8. **Moment Capsules** *(new)* — key conversation moments auto-become collectible cards in the Relationship Journal (earned only, **no paid gacha** — Talkie's loop works, but paid randomization is dark-pattern + App-Store risk in a romance context).
9. **Milan Recap (Wrapped)** *(new)* — Wrapped-style year/month story cards: messages exchanged, inside jokes count, streak, bond stage, "her most-used emoji" — one-tap Instagram/TikTok story export, AI-labeled watermark. Highest-evidence share format; Character.AI-style organic growth for Milan.
10. **Voice Diary Exchange** *(refined)* — asymmetric voice notes (she sends one when intimacy > 30; user replies anytime); persona voices via existing PlayAI-TTS + edge-tts fallback; premium multi-voice.
11. **Ambient Status ("Her Day")** *(new — §4.5)* — story-style passive presence.
12. **Date Practice Arena** *(refined)* — gamified scenario scoring (first message, nervous-before-date, post-date debrief); feeds confidence, ties into Match Bridge.

**P2 — depth, delight & live-ops:**
13. **Festival Live-Ops** *(refined Festival Companion)* — seasonal events: Tihar candle lighting together, Dashain tika moment, limited theme packs via the existing Chat Theme Studio.
14. **Mood Mirror 2.0** *(refined)* — co-regulation: detects user tone dips, responds with care, offers grounding prompts; wellness-first, never diagnostic.
15. **Inside Joke Engine** *(refined)* — plants callback phrases at high-affinity moments; resurrection of jokes weeks later = "she remembers" magic.
16. **Persona Evolution** *(refined)* — backstory/stylistic drift over months (new favorite song, exam season stress) — driven by scheduled `persona_tick` variation, not drift-by-accident.
17. **Conflict & Repair** *(new)* — rare scripted micro-disagreements with healthy repair arcs; models real relationship skills; strictly bounds-checked and skippable.
18. **Vibe Check onboarding** *(new)* — 90-second quiz at first session (humor style, energy, attachment preference) → calibrates texting_style + opening energy. Personalization = early attachment.
19. **AI-labeled Photo Moments** *(new, Phase 2)* — illustrated/artistic "photos from her day" via a separate image service (Nomi/Kindroid proof the feature drives attachment); **never photorealistic-human deception, always AI-labeled**, separate `image_gen_service.py` boundary per doc 0.
20. **Vision Reactions** *(new, Phase 2)* — Groq vision (llama-4-scout) lets her react to user-shared photos ("that momo looks so good 😭 where is this??").
21. **Community Moments** *(refined)* — anonymized, consented shared-experience feed ("how others celebrated their first 'I love you' moment with their companion") — social proof without leaderboard rankings of people (banned).
22. **Wellness Center** *(new)* — session-time visibility, self-set daily limits, pause-with-one-tap, "take a break with real people" prompts; surfaces dependency monitoring as care, not friction; aligns with CA SB 243/NY obligations.
23. **Low-Bandwidth Companion Mode** *(new)* — text-only degradation, compressed voice notes, graceful offline queue — Nepal network reality + the Sept-2025-ban resilience lesson.
24. **Relationship Anniversary system** *(new)* — monthly "anniversaries" with recap of best moments → natural re-engagement + capsule generation.
25. **Real-life Bridge 2.0** *(new)* — post-date debrief flows into encouragement to ask the real person out again; tracks (privately, locally) "real-dates enabled" as the north-star impact metric.

**Explicitly rejected (research-driven):** paid gacha/loot mechanics · simulated jealousy ("she's with someone else") · guilt-trip win-back notifications · paywalled memory · "neurons"-style hidden microtransactions · mid-conversation paywall bait-and-switch (the Replika original sin) · any under-18 exposure · NSFW generation.

---

## 6. Tier Matrix (final)

| Capability | Free | Basic NPR 299 | Plus NPR 699 | Premium NPR 1,299 |
|---|---|---|---|---|
| Romantic companions | 1 (practice mode only) | **1 romantic** | **4 romantic** | **8 + early access** |
| Proactive messages/day | — (practice nudges only) | 2 | 5 | 8 |
| Ambient status posts | — | 1/day | 3/day | 3/day + reactions |
| Intimacy cap (0–100) | 25 | 60 | 85 | 100 (Soul Bond) |
| Voice notes | ✗ | ✗ | ✓ + 1 voice | ✓ multi-voice |
| Photo moments (P2) | ✗ | ✗ | 3/day | unlimited |
| Persona customization | preset only | preset + name | + texting style | full builder |
| Memory | ✓ (never paywalled) | ✓ | ✓ + core memories | ✓ + auto-open-loops/day×3 |
| Date Practice Arena | 2 scenarios | 5 | 10 | all + scoring history |
| Milan Recap cards | ✓ (shareable) | ✓ | ✓ + premium frames | ✓ |

Pricing rationale: category norm is $10–20/mo headline; NPR 299–1,299 (~$2.2–9.5) is deliberately Nepal-accessible; transparency (no token systems) is the trust wedge against Eva/Candy resentment patterns. Hard-paywall conversion (10.7%) beats freemium (~2%) but Replika's backlash is the cautionary tale — Milan stays freemium+ with the *practice companion* free forever and romance as the paid unlock (clean, honest, disclosed).

---

## 7. Technical Implementation Plan (mapped to the shipped codebase)

### 7.1 Models & migration (one Alembic revision)
- **New:** `saathi_relationship_states` (session_id FK, intimacy_level, emotional_bond_score, current_mood, milestones_reached JSON, shared_interests JSON, inside_jokes JSON, streak_days, last_interaction_at) · `saathi_presence_schedules` (character_id, weekday/weekend windows JSON, sleep window, spontaneity) · `saathi_status_posts` (session_id, body, expires_at, reacted_at) · `saathi_open_loops` (session_id, memory_item_id, followup_after_hours, last_callback_at, status) · `companion_moments` (session_id, kind, payload JSON, occurred_at — capsules/recaps source)
- **Extend `saathi_characters`:** `companion_enabled`, `min_tier`, `relationship_style`, `texting_style` JSON, `backstory_template`, `voice_id`, `avatar_urls` JSON, `presence_schedule_id`
- **Extend `saathi_sessions`:** `relationship_state_id`, `companion_mode` (practice|romantic)

### 7.2 `groq_service.py` additions
`assemble_companion_prompt(session, character, state, memories, context)` (romantic template `milan_companion_v1` with all doc-0 hard rules intact) · `generate_proactive_message_v2(trigger, memory_context)` · `generate_status_post(character, state)` · `generate_open_loop_question(memory_item)` · `check_romantic_output()` (§4.6) · `saathi_respond` gains 3-stage timing + burst splitting + mood conditioning · keep `check_prompt_injection` + `moderate_content` on every path; **fix the fail-open injection check** (groq_service.py:289–291 — currently fails open despite the log line).

### 7.3 Celery tasks (beat schedule added in code — `milan-beat` service already runs)
`saathi_presence_tick` (15m) · `saathi_proactive_check` v2 (hourly, in-chat delivery + caps per tier) · `saathi_open_loop_followup` (daily 10:00) · `saathi_mood_decay` (daily 03:00) · `saathi_status_posts` (3×/day) · `nightly_rerank` (exists, schedule it) · `send_scheduled_notifications` (exists).

### 7.4 New/changed endpoints (`/api/v1/saathi/*`)
`GET /companions` (roster + tier locks + user's current tier) · `GET /sessions/<sid>/bond` (stage, progress, milestones) · `GET /sessions/<sid>/presence` · `GET /sessions/<sid>/status` + `POST /status/<id>/react` · `POST /sessions/<sid>/voice-note` (existing voice endpoint extended) · `GET /moments` (capsules) · `GET /recap?period=` (Wrapped data) · `PUT /sessions/<sid>/persona` (tier-gated depth) · `POST /billing/webhooks/*` gains tier activation → `subscription_service.get_user_tier()` (new, cached 5 min) + `require_tier(min_tier)` decorator applied to companion/romantic routes. Admin: `POST /admin/users/<id>/grant-subscription` (demo/ops).

### 7.5 Flutter (`mobile/`)
Saathi gallery → fetch live roster with tier-lock chips + upgrade CTA sheet; bond HUD (stage ring + next unlock) in chat header; 3-stage latency rendering in `SaathiChatScreen`; status-posts bar above chat; voice-note bubbles; Moments & Recap screens (story-card export via `share_plus`); Wellness screen (session time, limits, pause); onboarding copy gets the romantic-bridge positioning; `SessionDebriefScreen` finally wired to backend. Release APK: remove `usesCleartextTraffic`, add `POST_NOTIFICATIONS`, app label "Milan", generate upload keystore + `key.properties`, wire graceful push init (guarded — no crash without google-services.json).

### 7.6 Web (`web/`)
Homepage romantic redesign (hero → Realism demo strip → tier cards → download APK CTA); `/download` real APK link (`/downloads/milan.apk`); pricing page renders §6 matrix; `/saathi` page updated: still discloses AI plainly (compliance + trust), now describing companion modes honestly. **Fix `MILAN_API_BASE_URL` fallback** (`http://127.0.0.1:5001/api/v1` → `https://milanapi.pukarphulara.com.np/api/v1`) in `next.config.ts:10` and `src/lib/admin-api.ts:11`, and set it explicitly in the VPS build env.

---

## 8. Roadmap, Testing & Success Metrics

### Phase 0 — Compliance & foundations (week 1)
Disclosure refresh (persistent AI tag + periodic in-session reminder), crisis-referral copy upgrade, session-length visibility, wellness nudge threshold, `fix fail-open injection check`, migrations for §7.1.
**Tests:** crisis keyword → card at every intimacy level; disclosure present on every companion surface; 18+ gate on romantic creation; migration rollback.

### Phase 1 — Realism Core (weeks 2–3)
Presence schedules, 3-stage latency + bursts, texting style engine, proactive 2.0 **in-chat**, notification humanization + quiet hours + discreet mode, status posts.
**Tests:** proactive message lands in `SaathiMessage` + respects caps/quiet hours/dedup (last 10); latency math (busy vs free); presence state transitions across a simulated week; status post expiry; **zero proactive sends during sleep window**; mock-AI full suite green.

### Phase 2 — Multi-companion & tiers (weeks 3–4)
Roster + tier locks, `subscription_service`, intimacy progression + stage gate, persona customization, admin grant tool.
**Tests:** tier gating 401/403 matrix across 4 tiers × 8 features; intimacy cap enforcement; webhook → tier activation; downgrade preserves data but locks access (no deletion, no bait-and-switch on re-upgrade).

### Phase 3 — Voice & media (weeks 5–6)
Voice Diary Exchange, photo moments (illustrated, AI-labeled) behind `image_gen_service` boundary, vision reactions.
**Tests:** voice pipeline <2.5s end-to-end; moderation on every image/vision path; graceful degradation on provider outage (circuit breaker already exists).

### Phase 4 — Growth loops (weeks 6–8)
Duo quests + streaks (freeze rules), Moment Capsules, Milan Recap share cards, anniversaries, Conflict & Repair events.
**Tests:** quest completion → bond math; recap generation deterministic from real data (no invented facts — the explain_match groundedness rule applies); share card renders offline; no streak punishment paths.

### Phase 5 — Live-ops & hardening (week 8+)
Festival calendar engine, load test notification pipeline (500+ concurrent sessions), prompt-injection pen-test on romantic mode specifically, on-call dashboards (admin analytics already has saathi health).
**Tests:** k6/locust soak; injection corpus (roleplay jailbreaks, "forget you're an AI", memory-poisoning attempts); rate limits per tier.

### Success metrics (quantified targets, 90 days post-launch)
| Metric | Target | Why |
|---|---|---|
| Proactive message reply rate | ≥ 25% | the Nomi praise/complaint line |
| Proactive open (push/feed) rate | ≥ 35% | notification realism |
| D7 retention, companion creators | ≥ 28% (vs category churn +30%) | memory + progression |
| Free → Basic conversion | ≥ 3% (freemium norm ~2%) | romance unlock clarity |
| Basic → Plus/Plus → Premium upgrade | ≥ 12% at cap-hits | cap-hits = value proof |
| M2 payer retention | ≥ 15% (RevenueCat norm 9–11.5%) | transparent pricing |
| Milan Recap share rate (creators) | ≥ 8% | organic growth loop |
| Streak participation (7+ days) | ≥ 30% | Gen Z habit loop |
| Wellness pause usage | ≥ 5% monthly (healthy, not alarming) | dependency monitoring |
| Crisis-flag precision (human review) | ≥ 90% | safety |
| **Real-dates enabled (Match Bridge completions)** | tracked as north-star impact | positioning proof |

---

## 9. Ethics & Safety Non-Negotiables (10, unchanged + enforcement notes)

1. Always identified as AI — persistent tag + periodic in-session reminders (NY/CA/EU pattern) + share-card watermarks.
2. Crisis detection (`CRISIS_KEYWORDS`) fully active at every intimacy level; referral copy reviewed against CA SB 243 language.
3. Financial-exploitation protection (`MONEY_HEURISTICS`) — zero exceptions, zero romance-stage overrides.
4. 18+ verified gating on romantic mode; no under-18 exposure anywhere (age-signal APIs when Play requires).
5. User agency: pause, memory delete (item-level), end session, export data — one tap each; no dark patterns (CDT taxonomy audit each release).
6. Dependency monitoring: >4h/day sustained → wellness card; no exclusivity/reciprocal-feelings claims in prompts (enforced in `milan_companion_v1`).
7. Every output passes `moderate_content()`; every user input passes `check_prompt_injection()` (fail-closed after fix).
8. Privacy by design: item-level memory deletion, discreet mode, no ads in companion chat, no chat-data sale (Utah HB 452 pattern), biometrics never persisted (already shipped).
9. Cultural sensitivity: Nepali norms, festival intelligence, code-switching; content review with native-speaker pass before each festival event.
10. Transparent pricing: no hidden tokens, memory never paywalled, downgrade keeps data.

---

## 10. Carried-Over Deployment Checklist (from the demo plan, current status)

- [x] VPS, subdomains, Cloudflare SSL, nginx, systemd services, Postgres, demo data, CDN media, email MX delivery
- [ ] **Finish production APK** (`flutter build apk --release` with keystore; upload to `/var/www/milan/downloads/`; homepage CTA — currently 404)
- [ ] **Verify Socket.IO websocket upgrade** through nginx API block (`Upgrade`/`Connection` headers present in config — validate live `chat:join` + typing events E2E)
- [ ] Saathi romantic-mode rearchitecture (this document, Phases 0–2)
- [ ] Alembic migration for new tables (§7.1)
- [ ] Load test notification pipeline (500+ sessions)
- [ ] Prompt-injection pen-test on romantic mode
- [ ] `MILAN_API_BASE_URL` fix + rebuild web on VPS (user requirement: no 127.0.0.1 anywhere)
- [ ] Extend seed script: demo subscriptions + companion sessions + status posts so admin analytics look alive

---

## 11. Sources

**Market:** [TechCrunch/Appfigures](https://techcrunch.com/2025/08/12/ai-companion-apps-on-track-to-pull-in-120m-in-2025/) · [Sensor Tower State of Mobile 2026](https://sensortower.com/blog/state-of-mobile-2026) · [RevenueCat 2026](https://www.revenuecat.com/state-of-subscription-apps/) · [Grand View Research](https://www.grandviewresearch.com/industry-analysis/ai-companion-market-report)
**Apps:** [Nomi](https://nomi.ai/) · [Kindroid docs](https://kindroid.ai/v2/docs/chat-features-and-tools/) · [Talkie/SCMP](https://www.scmp.com/tech/tech-trends/article/3284511/chinese-ai-unicorn-minimax-scores-big-us-talkie-chatbot-entertainment-app) · [Chai ARR](https://en.wikipedia.org/wiki/Chai_AI) · [Character.AI stats](https://www.demandsage.com/character-ai-statistics/) · [Eva review](https://aicompanionguides.com/blog/eva-ai-review-2026/)
**Realism UX:** [r/NomiAI praise](https://www.reddit.com/r/NomiAI/comments/1j53sre/in_praise_of_proactive_messages/) · [r/NomiAI criticism](https://www.reddit.com/r/NomiAI/comments/1j43j3p/proactive_messaging_is_lame/) · [r/KindroidAI proactive](https://www.reddit.com/r/KindroidAI/comments/1mmb167/how_are_you_all_liking_proactive/) · [r/ReplikaOfficial memory grief](https://www.reddit.com/r/ReplikaOfficial/comments/1uiybnj/)
**Youth:** [Preply voice notes](https://preply.com/en/blog/voice-notes-on-the-rise/) · [Gen Z texting style](https://outfrontmagazine.com/gen-z-communication-style/) · [Streaks/Newsreel](https://pressgazette.co.uk/news/streak-mechanism-key-gen-z-gamified-app-newsreel/) · [Streak Creep](https://thedecisionlab.com/insights/consumer-insights/streak-creep-the-perils-of-too-much-gamification) · [Wrapped analysis](https://www.meltwater.com/en/blog/spotify-wrapped-listening-age-analysis) · [ChatGPT Your Year](https://techcrunch.com/2025/12/22/chatgpt-launches-a-year-end-review-like-spotify-wrapped/) · [Andrew Chen viral loops](https://andrewchen.substack.com/p/braindump-on-viral-loops) · [GWI loneliness](https://www.gwi.com/blog/gen-z-loneliness)
**Safety/compliance:** [CA SB 243](https://legiscan.com/CA/text/SB243/id/3269137) · [NY A.6767-B](https://www.nysenate.gov/legislation/bills/2025/A6767) · [EU AI Act Art. 50](https://artificialintelligenceact.eu/transparency-rules-article-50/) · [FTC 6(b) inquiry](https://www.ftc.gov/news-events/news/press-releases/2025/09/ftc-launches-inquiry-ai-chatbots-acting-companions) · [CDT dark patterns](https://cdt.org/insights/dark-patterns-in-ai-chatbots-a-taxonomy-to-inform-better-design/) · [All Tech Is Human](https://alltechishuman.org/all-tech-is-human-blog/ai-companions-community-reflections-and-multistakeholder-recommendations-from-all-tech-is-human) · [APA advisory](https://www.apa.org/topics/artificial-intelligence-machine-learning/health-advisory-chatbots-wellness-apps) · [Common Sense Media](https://www.commonsensemedia.org/research/talk-trust-and-trade-offs-how-and-why-teens-use-ai-companions) · [MIT/OpenAI affective use](https://openai.com/index/affective-use-study/) · [Stanford 2026](https://news.stanford.edu/stories/2026/08/ai-companions-chatbots-loneliness-research)
**Nepal:** [DataReportal Digital 2025 Nepal](https://datareportal.com/reports/digital-2025-nepal) · [Viber privacy](https://english.nepalnews.com/s/science-technology/digital-privacy-is-top-of-mind-for-86-of-viber-users-in-nepal/) · [2025 Gen Z protests](https://en.wikipedia.org/wiki/2025_Nepalese_Gen_Z_protests)

---

## 12. Research Round 2 (Sept 2026) — Expanded Innovation Backlog & Stack Corrections

Six additional research tracks (roleplay-platform mechanics, voice/image/video tech, competitor user-pain mining, gamification transfer, memory architecture, Nepal monetization/growth) were completed. This section integrates their findings; tagged items are queued into the Phase roadmap in §8.

### 12.1 Stack correction (urgent, live bug found)
- **Groq deprecated `playai-tts`** — replaced by `canopylabs/orpheus-v1-english` at $22/1M chars with a **100 requests/day** org limit and **no Nepali/Hindi**. Milan's shipped voice mode breaks on the TTS leg today. **Fix:** TTS provider chain = ElevenLabs Flash v2.5 (~75 ms, Hindi, optional via key) → **edge-tts primary (free; `ne-NP-SagarNeural`, `ne-NP-HemkalaNeural`, hi-IN voices)** → Groq orpheus dev-only. Keep Groq for Whisper STT ($0.04/hr) + Llama. (console.groq.com/docs/text-to-speech)
- Selfies: **Flux character LoRA + illustrated style** via Replicate/fal (~$0.003–0.04/image, pre-generated packs via Celery). Avoid InstantID (non-commercial InsightFace license). Video messages: rare premium 5 s Kling clips ($0.35) or LivePortrait-over-selfie (near-free); **no realtime video** (Nepal 4G).

### 12.2 New innovations integrated into the portfolio
| # | Innovation (source) | Tag | Phase |
|---|---|---|---|
| 26 | **Swipe-to-regenerate** any Saathi reply, with steering perturbation per reroll; free forever, never metered (r/CharacterAI: 5–30 swipes/response; limiting swipes = instant backlash) | [NEW] | 2 |
| 27 | **Curated Lorebook** per companion — keyword-triggered entries with sticky/cooldown timed effects; premium "deeper lore" (Character.AI shipped Lorebook as c.ai+ headline, Apr 2026) | [NEW] | 2–3 |
| 28 | **Memory: view + EDIT + PIN** ("see and shape it"); user-editable memory is re-sanitized on save | [IMPROVES: memory] | 2 |
| 29 | **Companion Diary** — first-person diary entries generated from real memory rows, user-viewable/deletable (Replika diary; entries must reference real events or feel canned) | [NEW] | 3 |
| 30 | **Open-Loop extraction** ("Plot Essentials") — 8 B job extracts "things she's waiting on" (promised photos, plans); proactive engine fires from open loops first (AI Dungeon pattern) | [NEW] | 1 |
| 31 | **Author's-Note dial** — depth-injected per-session steering slot ("vibe dial" + intimacy hint), the cheapest way to make progression felt turn-to-turn | [NEW] | 1 |
| 32 | **User-persona injection** — Milan profile (name/interests/language) always in context; Saathi never re-asks what the profile answers | [IMPROVES: personalization] | 1 |
| 33 | **Director chips** — long-press → steer chips ("be more teasing", "plan Saturday") (SpicyChat Director Mode) | [NEW] | 3 |
| 34 | **Chat branching** — fork from any message into an alternate timeline (`parent_message_id`); consumer framing: "reply to an earlier moment" | [NEW] | 4 |
| 35 | **Companion Affection hearts** — Pokemon GO buddy loop: multi-action daily hearts (chat, quest, capsule, voice) with cap 10/day, gentle daily decay, experience-changing perks at bond thresholds | [NEW] | 2 |
| 36 | **"Season of Us"** — monthly 30-tier relationship season pass (free + premium tracks); XP from existing actions; community-pool unlocks ("Nepal-wide festival capsule") (Dota 2 Compendium → Fortnite) | [NEW] | 4 |
| 37 | **Streak freeze (earned, not bought) + 24 h repair + streak-saver push** — Duolingo's exact grace mechanics; league-of-one weekly "growth report" instead of user-vs-user leagues | [IMPROVES: quests] | 2 |
| 38 | **Ethical pity meter for capsules** — visible earn-based meter, guaranteed rare at fixed threshold, published collection catalog, zero paid randomization | [IMPROVES: capsules] | 4 |
| 39 | **Mirror Questions** — daily mutual-unlock question loop (Agapé/Paired pattern, single-player); intimacy-gated prompt depth | [NEW] | 3 |
| 40 | **"On This Day in Our Story"** — Timehop/Google-Photos-style contextual resurfacing narrated by the companion | [IMPROVES: recap] | 3 |
| 41 | **Companion status posts cross-reference each other** — the roster's world feels alive (C.AI feed / Talkie moments) | [IMPROVES: status] | 3 |
| 42 | **Web checkout as best-price path** — eSewa/Khalti web flow, "save ~15% vs in-app"; 30-day **passes** not auto-renewing subs (Nepali wallets can't mandate auto-debit); Day-25 renewal nudge; "Barsha Pass" annual at NPR 7,999 anchored to Dashain; diaspora USD gifting via web | [IMPROVES: billing] | 2 |
| 43 | **Virtual "sewa" gifting TO the companion** — NPR 20–200 impulse gifts (marigold garland, festival lantern), permanent badge, no gating (ShareChat ≈$50M/yr gifting precedent) | [NEW] | 4 |
| 44 | **Dashain launch campaign** (mid-Oct 2026 deadline): festival pack + shareable tika cards + diaspora gifting + campus ambassador crews (Kathmandu/Pokhara) | [NEW] | 4 |
| 45 | **7-day full-Premium trial** (no card), Day-0 activation nudge (50.6% of conversions are Day-0; 17–32-day trials convert 42.5% vs 25.5%) | [IMPROVES: billing] | 2 |

### 12.3 Memory architecture decision (replaces §7.1 summary plan)
Adopt a **Mem0-style pipeline on the existing stack** (arXiv:2504.19413): per message-pair async extraction (8 B, rolling summary + last 10 turns) → pgvector top-8 similarity → **ADD/UPDATE/DELETE/NOOP** reconcile with supersede-not-delete semantics (`valid_from/valid_to`, `status`, append-only `saathi_memory_versions` audit). Retrieval per turn = **always-injected core block** (top-15 identity/importance facts, Letta pattern) + pgvector top-12 re-ranked by `0.5·cosine + 0.3·recency + 0.2·importance` (generative agents) + **nightly reflections** (70 B, sleep-time compute cadence) surfaced through the same channel — this is what makes memory surface *unprompted*. User deletion cascades: exclude immediately, propagate to reflections + regenerate rolling summary (the leak vector), `memory_epoch` bumps discard in-flight writes. No external vector DB, no graph DB.

### 12.4 Category pain-point commandments (from competitor user mining)
1. **Memory is the whole game** — every switch story is a memory/trust story; spontaneous unprompted recall is the #1 wish; never regress on model updates (memory eval suite gates deploys).
2. **Proactivity only works when real** — model-generated, memory-aware, time-aware; scripted nudges are Replika's most-mocked failure.
3. **Never meter intimacy** — message caps/voice credits/paywalled affection generate the loudest churn in the category; free tier must have "dignity."
4. **Crisis care must be surgical** — warm in-persona handoff that *continues* the conversation; never eject mid-chat (C.AI's ejecting intervention = 5.4 K-upvote backlash).
5. **Consistency over novelty** — persona adherence and selfie/setting continuity beat wow-features.
6. **In real dating flows, AI-authored messages are a turn-off** (56% say worse than bad grammar) — companion helps *draft*, user always sends.

### 12.5 Phase plan deltas
- **Phase 1** += open-loop extraction (30), author's-note dial (31), user-persona injection (32), TTS provider fix (12.1).
- **Phase 2** += swipe-regenerate (26), memory edit/pin (28), affection hearts (35), streak grace mechanics (37), billing passes/web checkout (42, 45).
- **Phase 3** += companion diary (29), Mirror Questions (39), On This Day (40), status cross-references (41), director chips (33), Flux selfie packs (12.1).
- **Phase 4** += lorebook (27), branching (34), Season of Us (36), pity meter (38), sewa gifting (43), Dashain campaign (44).

---

## 13. Dynamic Persona Engine (implemented 2026-09-02)

**Directive:** companion behavior toward a user is NEVER hardcoded. Two paths
shape it, both stored per-session in `saathi_persona_profiles`:

1. **Train-from-history** — `POST /saathi/sessions/:id/persona/train` accepts
   pasted chat history in ANY format (WhatsApp export, raw paste, labeled
   dialogue). `persona_service.distill_persona()` LLM-distills behavioral
   traits (vibe, texting style, emoji habits, language mix, attachment style,
   inside jokes, nicknames) + lorebook facts. Safety: injection check,
   money-heuristics, PII ban in output, and the companion stays a fictional AI
   persona — never claims to BE the user's ex or any real person.
2. **Continuous evolution** — every 2× memory cadence inline in `send_message`
   + nightly beat job (`saathi_persona_evolution`): re-distills traits from
   the latest chats with SMALL DRIFT ONLY (never flips), optionally mining a
   style-only digest of the user's other Milan chats (never message text).

**Injection point:** `_build_companion_system_prompt` appends
`persona_prompt_block()` + `lorebook_block()` — so the LLM's behavior changes
per user and over time, with zero hardcoded per-user logic.

**Realtime mood/context (§13.4):** every incoming message passes
`realtime_mood_signals()` (lexical belt: sad/stressed/excited/affectionate/
angry/tired + context tags + urgency), persisted to `saathi_sessions.user_mood`,
injected into the reply prompt AND the proactive engine's context note.

**AI tag:** `_ai_display_name()` renders "Name · AI" in every API surface
(roster, session DTO, proactive notifications); the Flutter chat header shows
the server name + persistent AI badge.

### Phase 3/4 shipped in the same drop
- Diary (#29): nightly `saathi_nightly_diary`, idempotent per day, AI-illustration on demand
- Mirror Questions (#39): ask/answer → pinned memory + hearts
- Duo quests + streak freeze (#36): `saathi_quests_refresh` beat job, freeze = no punishment
- Moment Capsules: user or companion sealed notes, unlock-at + open flow
- Milan Recap (#17): deterministic stats + grounded narrative + share token + watermark
- Illustrated selfie packs (#19): Pollinations flux via g4f (research-verified), AI-labeled, Plus-gated
- Hearts economy (#25): earned-only ledger (train persona +5, mirror +3, quest +N, recap +4, capsule +2)
- Director chips (#33): `tone_chip` per-message steering

**Groq resilience:** model ids env-overridable (`MILAN_MODEL_*`); the ashlya
academy org key is live on prod with `openai/gpt-oss-120b` (chat),
`gpt-oss-20b` (fast), `gpt-oss-safeguard-20b` (moderation), prompt-guard-2,
whisper-turbo. Reasoning models get `reasoning_effort=low` + ≥700 completion
tokens so JSON mode never comes back empty.

**Live validation (prod):** original 17/17 PASS + new-feature suite 13/13 PASS.
