# Milan — Master Build Orchestrator Prompt

> **Document 0 of 7 — read this one first, and paste it into your AI code editor first.** This document does not introduce new product decisions on its own; it tells the AI editor *how to read the other six documents as one system* before it writes any code. Put all seven files in the same project/working directory the AI editor has access to (repo root, or a `/docs` or `/specs` folder it can browse) — this prompt assumes it can see the other six by filename.

---

## Prompt starts here

You are about to build **Milan**, a Nepal-first, AI-native dating and connection app. The full specification is split across seven markdown documents sitting in your working directory. Before you write a single line of code, create a single file, or run a single scaffolding command, **read all seven documents in full, in this order**:

1. `00_milan_master_prompt.md` — this file (orchestration + non-negotiables)
2. `01_milan_vision_and_market_research.md` — why the product exists, competitive research, the full feature list, ethical guardrails
3. `02_milan_design_system_and_screens.md` — visual language, design tokens, all ~68 screens
4. `03_milan_flutter_app_build_prompt.md` — the mobile app (Flutter)
5. `04_milan_backend_flask_build_prompt.md` — the backend (Python/Flask)
6. `05_milan_ai_companion_and_matching_groq_prompt.md` — the AI layer (Groq): Saathi companion + matching intelligence
7. `06_milan_web_nextjs_prompt.md` — marketing site + admin dashboard (Next.js)

**Do not start implementing after reading only one or two of these.** Documents 3–6 each assume the other three exist and reference each other constantly (a screen in doc 2 maps to a route in doc 3, which calls an endpoint in doc 4, which calls a function whose contract is defined in doc 5). Reading only the doc closest to whatever you're about to build will produce code that's internally consistent but wrong at the seams — a Flutter screen that doesn't match the API shape, a backend model missing a field the AI layer needs, an admin dashboard that can't render what the moderation pipeline actually produces. Read everything, hold the whole system in mind, then build.

If your tooling truly can only ingest one file per turn, paste them in the numeric order above, and explicitly re-state (to yourself, in a scratch note) how the current document connects to the ones before it before you start generating code from it.

## 1. What Milan is, in one paragraph

Milan is a rebrand and v2 relaunch of an existing Nepal-focused dating and connection product (previously built and referred to internally as "Dobato"). It combines the proven, now-table-stakes innovations from the global dating-app market (AI-curated matching over swipe volume, video-first profiles, mandatory liveness verification, pre-send message intervention) with an original AI companion layer — **Saathi AI** — built for conversation-confidence practice, not romantic substitution, running on Groq's low-latency Llama inference stack. It is localized deeply enough (Nepali/English, eSewa/Khalti/Fonepay/ConnectIPS, horoscope compatibility, discretion controls, diaspora mode, low-bandwidth handling) to feel built *for* Nepal, not translated *into* it. Full rationale in document 1.

## 2. The rename: Dobato → Milan

This build renames the product from its prior working title, **Dobato**, to **Milan**. Two things fall out of that rename and are already applied consistently across documents 1–6 — don't reintroduce the old names:

- **The name itself is load-bearing.** *Milan* (मिलन) is a Nepali/Hindi/Sanskrit word meaning "union," "meeting," or "confluence" — it's not a borrowed or arbitrary brand word for this market, it's the actual vocabulary a Nepali user already associates with two people (or two paths, two rivers) coming together. That happens to line up neatly with the existing brand motif from the design system: the **"Junction Mark"** logo (two paths meeting) was designed before this rename and now reads as an even more literal expression of the app's name than it did under "Dobato." Keep the Junction Mark unchanged — it fits better now, not worse.
- **"Milan Mode" — the opt-in horoscope/kundali compatibility feature — is renamed to "Kundali Mode"** throughout documents 1, 2, and 5, purely to avoid the feature name colliding with the new app name. "Kundali" (birth chart) is, if anything, the more precise and more culturally native term for what the feature actually does (traditional Kundali Milan / horoscope matching), so this is a clarity improvement, not a compromise.
- A light trademark/naming-conflict check was done as part of this rebrand: no existing Nepal-market dating or matrimonial app (Mooche, Lahmee, Saino, BiheNepal) uses "Milan" as a product name. A European affair-dating site ("Victoria Milan") and the Italian city both use the word in unrelated contexts and are not realistic sources of confusion in the Nepal dating-app category — but do a proper legal trademark search in Nepal and any diaspora markets you plan to operate in before public launch; this is product research, not legal clearance.
- Where any document references "the existing Dobato codebase" or "existing Dobato/Ashlya infrastructure conventions," read that as *the existing engineering conventions this team already uses* — Ashlya is a separate, unrelated product in the same infrastructure family and is **not** part of this rename.

## 3. Document map — what governs what

| # | File | Governs | Read before touching |
|---|---|---|---|
| 1 | `01_milan_vision_and_market_research.md` | Strategy, competitive research, full feature list, ethical/legal guardrails, build phasing | Anything — this is the "why" behind every feature in 2–6 |
| 2 | `02_milan_design_system_and_screens.md` | Color/type/spacing/motion tokens, reusable components, the full ~68-screen inventory including the new Chat Theme & Wallpaper Studio (§2.7, §3.9) | Any UI work in doc 3 or doc 6 |
| 3 | `03_milan_flutter_app_build_prompt.md` | Mobile app architecture, state management, navigation graph, feature-by-feature implementation notes | The Flutter app itself |
| 4 | `04_milan_backend_flask_build_prompt.md` | Data models, REST API surface, real-time events, Celery tasks, security/compliance | The backend itself, and anything doc 3/5/6 call over the network |
| 5 | `05_milan_ai_companion_and_matching_groq_prompt.md` | Every Groq-backed function (`groq_service.py`), Saathi AI's persona/memory/proactive-messaging system, the AI safety pipeline | Anything that calls an AI feature from doc 3, 4, or 6 |
| 6 | `06_milan_web_nextjs_prompt.md` | Marketing site, admin/moderation dashboard | The web surface |

## 4. Build order

1. **Document 4 (backend) and document 5 (AI layer) first.** They jointly define the API contract everything else depends on — document 5 specifies the internals of `services/groq_service.py`, which document 4's blueprints call.
2. **Documents 3 (Flutter) and 6 (web) in parallel**, once the API contract from step 1 is stable. Both consume the same backend; neither should invent its own version of an endpoint doc 4 already defines.
3. **Document 2 (design system) is read continuously, not "done" at any single step** — every screen built in doc 3 or doc 6 pulls its tokens and components from it.

## 5. Non-negotiables that span every document (condensed from document 1 §5 — read the full version there)

These are enforced **server-side**, not just in the Flutter client, and apply to every AI-generated surface in the product, including the new personalization system in §6 below:

1. Saathi AI is never marketed, prompted, or monetized as a romantic or sexual partner substitute. No NSFW generation, ever, anywhere in the product — including in any AI-generated wallpaper/image feature you build per §6.
2. All AI-companion features are 18+ with real age-gating.
3. No autonomous agent-to-agent messaging or auto-sending on a user's behalf without an explicit, per-message tap.
4. No public ranking or leaderboarding of people, ever.
5. Every AI-generated message or piece of UI shown to a user is clearly labeled as AI where relevant.
6. Content moderation runs on every message thread by default, not only reported ones.
7. Biometric data (liveness selfies) is processed for verification and then discarded — never retained past what duplicate-account detection needs.
8. Saathi's proactive/first-contact messages are opt-in, frequency-capped, and route through the same notification service and caps as every other notification.
9. Ephemeral snaps always notify the sender on screenshot; no gamified streak mechanic is allowed to punish a missed day.

If you find yourself implementing something that would violate one of these to hit a feature request elsewhere in these documents, stop and flag the conflict rather than silently picking a side.

## 6. Cross-cutting feature added in this revision: full chat & companion personalization

This is new since the "Dobato" version of these documents and touches three of the six build docs — read all three sections together before implementing any part of it:

- **`02_milan_design_system_and_screens.md` §2.7** defines the visual system: preset theme packs (brand-palette, festival, nature, minimal), solid/gradient/custom-photo wallpapers, independent bubble-color and bubble-shape controls, Nepali-motif doodle overlays, dark-mode brightness handling, and the accessibility rules (contrast checking, text scale, reduced-motion). It also adds the new **Chat Theme & Wallpaper Studio** screen to the screen inventory (§3.9), reachable from a chat thread's overflow menu, from Saathi chat, and from Settings.
- **`03_milan_flutter_app_build_prompt.md` §4 and §6** define the `themeProvider`, the `ThemePickerSheet` widget, local caching so a theme change applies instantly without a network round-trip, and how `ChatBubble` and chat/Saathi backgrounds consume the resolved theme.
- **`04_milan_backend_flask_build_prompt.md` §2 and §3** define the `ChatTheme` model and the `/api/v1/personalization/*` endpoints that store and sync a user's global default and per-chat/per-Saathi-session overrides.

The design intent in one sentence: **this is a private, per-viewer personalization layer (the way WhatsApp and Telegram chat themes work — your match never sees your wallpaper choice, only you do), built from Milan's own brand tokens and cultural motifs rather than a generic third-party wallpaper library, with an optional (Phase 2+) AI-generated-wallpaper mode that is explicitly abstract/pattern-only — never a generator of photorealistic people — and moderated like any other user-facing generation surface.** Full customization means the user genuinely controls every layer (wallpaper source, bubble color, bubble shape, text size, dark-mode brightness) independently, with one-tap reset to Milan's own defaults at any time — not a forced choice between "default" and "one alternate skin."

## 7. Definition of done (combined checklist)

Before considering the build complete, confirm every item below — each traces back to a specific document, cited in parentheses:

- [ ] Every screen in the doc 2 inventory has a corresponding route and screen file (doc 3 §10)
- [ ] Dark mode is fully implemented for every screen, not a stub (doc 2 §2.1, doc 3 §10)
- [ ] Every AI-generated or AI-suggested piece of UI is visually labeled as such (doc 1 §5.5, doc 3 §10)
- [ ] No feature bypasses the notification frequency caps or the Saathi proactive-message cap (doc 1 §4.8, §5.8, doc 4 §6/§9)
- [ ] All user-facing strings are localized (Nepali/English), none hardcoded (doc 3 §7)
- [ ] Report/block affordances are reachable in ≤2 taps from every profile, chat thread, and reel (doc 1 §4.4, doc 3 §6)
- [ ] Liveness selfies are never persisted past the verification job (doc 1 §5.7, doc 4 §8)
- [ ] All Groq calls live only in `services/groq_service.py`, with prompt-injection and moderation checks on every function per document 5 §4/§5
- [ ] The chat/Saathi personalization system (§6 above) is private-per-viewer, has a working global default + per-scope override + one-tap reset, and any custom-uploaded wallpaper image passes through the same moderation/compression pipeline as any other user media upload (doc 4 §2/§3)
- [ ] Every reference to the app's old working title has been updated to **Milan**, and the horoscope-compatibility feature is named **Kundali Mode**, not "Milan Mode," anywhere in code, copy, or API payloads

Proceed to document 1.
