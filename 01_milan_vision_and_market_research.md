# Milan v2 — Vision, Market Research & Innovation Blueprint

> **Document 1 of 7.** This is the strategic foundation doc. Read this first — it explains *why* every feature in documents 2–6 exists. Feed this to your AI code editor as context alongside the build prompts, or read it yourself before kicking off a build session. If you haven't read `00_milan_master_prompt.md` yet, read that first — it explains the Dobato → Milan rebrand and how these seven documents fit together.
>
> **Companion documents:**
> 0. `00_milan_master_prompt.md` — master orchestrator prompt (read first)
> 1. `01_milan_vision_and_market_research.md` — this file
> 2. `02_milan_design_system_and_screens.md` — visual design system + full screen inventory
> 3. `03_milan_flutter_app_build_prompt.md` — Flutter build prompt
> 4. `04_milan_backend_flask_build_prompt.md` — Flask backend build prompt
> 5. `05_milan_ai_companion_and_matching_groq_prompt.md` — Groq AI layer (matching intelligence + Saathi AI companion)
> 6. `06_milan_web_nextjs_prompt.md` — Next.js marketing site, web app, admin dashboard

---

## 1. Executive Summary

Milan v2 is a Nepal-first dating and connection platform that takes the best proven innovations from the global dating-app market (AI-native matchmaking, video-first profiles, liveness-verified safety, AI conversation coaching) and combines them with an original AI companion layer built for confidence and practice — all powered by Groq's low-latency Llama inference stack, and localized deeply enough that it feels built *for* Nepal rather than translated *into* Nepal.

The thesis: global apps (Tinder, Bumble, Hinge) are mid-pivot from "swipe volume" to "AI-curated intent" — and none of them have solved for a conservative-but-modernizing market where family stigma, horoscope compatibility, caste/ethnicity preferences, low-bandwidth networks, and a massive labor-migration diaspora are all real, simultaneous facts of life. That gap is the opening.

**A note on the name:** this product was previously developed under the working title "Dobato." This revision renames it to **Milan** (मिलन — "union," "meeting," "confluence" in Nepali/Hindi/Sanskrit) — see document 0 §2 for the full rationale, including why the existing "Junction Mark" brand motif and the new name reinforce each other, and why the horoscope-compatibility feature formerly called "Milan Mode" is renamed **Kundali Mode** in this document to avoid colliding with the app's own name.

## 2. Global Competitive Landscape (2026)

### 2.1 The big three are rebuilding around AI, not swiping

- **Tinder** launched **Chemistry**, a conversational onboarding flow that (with permission) can read camera-roll signals to infer lifestyle and interests, replacing endless swiping with a small number of curated recommendations. Match Group committed roughly $60M to the overhaul. Tinder also shipped **Face Check**, mandatory video-selfie liveness verification at onboarding in an expanding list of countries, which flags when the same face is reused across multiple accounts.
- **Hinge** was earlier to AI: its **Core Discovery Algorithm** re-ranks candidates using conversational signal on top of the Gale-Shapley stable-matching model, and is credited with a double-digit lift in matches and contact exchanges. Hinge also ships **AI Convo Starters** and **Prompt Feedback**, which grades a user's written prompts before they go live.
- **Bumble** is rebuilding its stack as AI-first and cloud-native. Its **Deception Detector** blocks a large majority of fake accounts pre-feed. It shipped an **ID verification badge**, a **Share Date** safety feature (share who/when/where with trusted contacts), and **"Review Before You Send"**, which intercepts messages likely to read as inappropriate before they're sent.
- Across the category: dating-app growth has stalled and a large majority of users report "dating fatigue," which is exactly why every major player pivoted to *fewer, better* recommendations instead of more volume.

**Takeaway for Milan:** curated intelligence over swipe volume, mandatory liveness verification, and pre-send message intervention are no longer differentiators — they're table stakes. Build them into v1, not as a "v2 feature."

### 2.2 Video-first profiles are now a normal, not a novelty

Apps like **Snack** replaced the static photo grid with a vertical, TikTok-style video feed — your profile *is* a short video, not a set of photos, and matching happens through video likes rather than swipes on stills. The pitch: video collapses catfishing risk (much harder to fake a moving, speaking person convincingly) and communicates personality/humor in a way static photos can't. Other platforms (Hinge, eHarmony) have added video-date and video-verification layers without going fully video-first.

**Takeaway for Milan:** make short video an equal citizen alongside photos from day one — not a bolt-on. This is also your literal answer to "reels" in your brief (see §4.3).

### 2.3 AI-native matchmakers are proving a real alternative to swipe UX

- **Iris Dating** trains a facial-preference model per user through a rapid LIKE/PASS/MAYBE calibration session, then uses that model (not just age/location filters) to rank candidates — and separately uses an LLM to help users write bios.
- **Amata** replaces swiping with a conversational AI matchmaker: it interviews you the way a human matchmaker would, introduces a small number of curated people, and closes the loop by debriefing you after the date and feeding that back into future matching.
- Both point at the same underlying shift: **the interview/calibration step becomes the core interaction**, and swiping becomes secondary or disappears entirely.

**Takeaway for Milan:** build a real conversational onboarding interview (see §4.1) instead of a preference-filter form. This is one of the highest-leverage, most defensible features in this whole plan.

### 2.4 The AI-girlfriend / companion market is large, fast-moving, and legally risky

The AI companion category (Replika, Character.AI, Nomi, Kindroid, Candy AI, and dozens of smaller players) has matured into a real market with persistent memory, voice calls, persona/character creation, and relationship-progression mechanics as standard features. But it's also the most legally exposed corner of consumer AI right now:

- **Character.AI** settled lawsuits tied to teen mental-health harms and is under state attorney-general investigation for its marketing practices; it has been aggressively (and unevenly) removing characters in response.
- **Replika** has been repositioning away from romance and toward "wellness" framing after regulatory pressure (including in the EU), while keeping voice, memory, and companionship as premium features.
- Every credible review in this space flags the same three risks for end users: data privacy of intimate conversation logs, weak/self-reported age gating, and subscription dark patterns.

**Takeaway for Milan — this is the single most important strategic decision in this document:** don't clone the "AI girlfriend" pattern directly. Build the *underlying technology* (persistent memory, voice, persona, natural conversation) but aim it at a safer, more defensible, more durable product: an **AI companion for building dating confidence and practicing conversation**, not a romantic/sexual partner substitute. This sidesteps the Character.AI-style legal exposure, keeps you compliant with Apple/Google policies (both platforms increasingly restrict romantic/sexual AI chat apps and scrutinize their monetization), and — done well — is genuinely more useful to a first-time dating-app user in a culture where dating anxiety and inexperience are common. See document 5 for the full design of this feature, called **Saathi AI**.

### 2.5 AI "wingman" utilities are a proven, smaller-scope pattern worth absorbing natively

A whole cottage industry (RizzGPT, Icebreaker, Wingy, AI Wingmate) exists purely to screenshot a chat and generate a reply. That's a strong signal of unmet need — but it's also a feature, not a product. Milan should build this *in*, natively, using match context you already have server-side (shared prompts, shared interests, tone of the conversation so far) rather than requiring a screenshot roundtrip through a third-party app. Keep it strictly **suggestion-only**: never send on the user's behalf without an explicit tap. (Grindr's roadmap toward autonomous agent-to-agent messaging is a useful thing to know about, and a useful thing to avoid — it removes user agency from their own conversations and is a consent minefield.)

### 2.6 Safety tech is now the primary trust lever

Liveness/selfie verification (Tinder Face Check, Bumble ID badge, Hinge Selfie Verification, MeetMe's FaceTec-based 3D liveness, iris Dating's live-selfie gate) has gone from optional to expected across every serious platform. The common architecture: capture a live selfie/video at signup → compare against profile photos with a vision model → issue a verified badge → cross-check the face embedding against other accounts to catch repeat offenders. Romance-scam losses (FTC reported $3.1B+ in 2024, disproportionately hitting older and vulnerable users) are the other half of the safety story — this is directly relevant to Nepal given how much of the economy runs on remittances and how often scammers target that specific vulnerability (see §3.4).

### 2.7 "Realistic" AI presence — texting first, memory, typing indicators — is now the AI-companion battleground

The newest wave of AI companion apps competes specifically on *feeling like texting a real person* rather than *querying a chatbot*:

- **Replika's** biggest recent overhaul added better long-term memory, **proactive check-ins**, calls, and image generation — explicitly marketed around a companion that "shows up when it counts," including an automatic good-morning message and next-day follow-ups on things you mentioned ("I told mine about a rough day at work and it checked in the next morning").
- **Sidekicks (Zev)** differentiates specifically by **texting the user first** — proactive check-ins, good-morning texts, and follow-ups — and by running natively inside iMessage/SMS with real typing indicators and tapback reactions, rather than living inside a separate app.
- Across the category, the table-stakes "realism" signals are consistent: **typing indicators, online/last-seen presence, read receipts, proactive first messages, and cross-session memory** that lets the companion reference something from three days ago without being reminded.
- Replika's own positioning line is the most important data point here: **"the right AI doesn't keep you in — it helps you find your way forward,"** with proactive suggestions that nudge users toward *real* friends, hobbies, and offline life rather than deeper app engagement. This is a direct validation of the design stance Milan is taking in §4.2 and §5 — the *technology* (memory, proactive messaging, realistic presence) is proven and worth building; the *business model built around maximizing romantic dependency* is the part that creates legal exposure and, more importantly, isn't good for the people using it.

### 2.8 Messaging-app personalization has become a full retention lever, not a cosmetic afterthought

Through 2025–2026, chat theming went from a niche feature to a headline one across every major messaging platform, and it's directly relevant to Milan's own chat and Saathi surfaces:

- **WhatsApp** shipped chat themes (coordinated wallpaper + bubble-color presets, 30+ wallpapers, custom-photo upload, dark-mode brightness control) globally through 2025, then expanded to per-chat overrides, 40+ web theme options, and — as of mid-2026 — is testing **animated wallpapers**. Critically, WhatsApp's model is **private-per-viewer**: your theme choice is visible only to you, never to the person you're chatting with.
- **Telegram** has offered chat-level custom backgrounds (colors, gradients, patterns, doodle overlays, user-uploaded images) for years and is the platform WhatsApp is visibly catching up to.
- A large, fast-growing app category — AI wallpaper generators (Zedge's AI maker, AIPixWall, Canva's Magic Media, and dozens of others) — has made text-to-image wallpaper generation a mainstream, expected capability rather than a novelty, though none of them are built for a messaging/dating context specifically.

**Takeaway for Milan:** a private, per-user, deeply customizable chat and Saathi-companion theme system — built from Milan's own brand tokens and cultural motifs rather than a generic stock-wallpaper library — is both a proven retention lever and a natural fit for a brand whose whole visual identity (§ design system, document 2) is already built around warmth and cultural specificity. Full design in document 2 §2.7 and document 1 §4.9 below.

## 3. Nepal Market Context

### 3.1 Existing players

- **Mooche** — modern, casual-dating-oriented, explicitly trying to de-stigmatize online dating for Nepali users; iOS-only, small scale.
- **Lahmee** — matrimonial-leaning, privacy-first (photo blurring, aliases), filters by caste/ethnicity/profession, added horoscope/kundali matching and a "sketch your picture" privacy feature; serves both in-country and diaspora Nepali users.
- **Saino** — positions itself across dating, friendship, *and* matrimony in one app, targeting the global Nepali community.
- **BiheNepal** — matrimony-and-dating hybrid with kundali/Vedic-astrology compatibility, blind-date (no-photo) mode, and anti-spoofing face verification.

None of them ship AI-native matching, video-first profiles, liveness verification, or a companion/practice layer. That's the whitespace.

### 3.2 Cultural realities to design around, not against

- Dating carries real social stigma in parts of Nepali society, even as younger, urban, educated users are rapidly normalizing it — so **discretion controls matter as much as discovery features** (hide-from-contacts, blur-until-mutual-interest, no auto-social-share).
- Arranged marriage and family involvement remain culturally significant, which is exactly why horoscope/kundali compatibility and family-readable "serious intent" modes are not gimmicks here the way they'd be in a Western market — they're genuine trust signals.
- Ethnicity/caste and religion preferences are a normal, expected filter category in South Asian matrimonial products (the same way JSwipe filters by Jewish denomination or Muzz filters by Islamic sect) — treat this as an optional profile/preference field, not a headline feature, and make it opt-in and mutual rather than a blunt discovery filter.
- The Nepali diaspora (Gulf states, Malaysia, South Korea, Australia, UK, North America) is enormous relative to the resident population, and existing apps (Lahmee, Saino) explicitly design for it. A **diaspora mode** — matching resident users with diaspora users who intend to return, or diaspora-to-diaspora by city — is a real, requested use case, not an edge case.

### 3.3 Infrastructure realities

- Network conditions and data costs mean **video and image pipelines must degrade gracefully** — aggressive client-side compression, low-data mode, adaptive bitrate, and a text/photo-only fallback path when video won't load. This applies equally to the new personalization system in §4.9 — custom wallpaper uploads go through the same compression path as any other media.
- Payment must go through **eSewa, Khalti, Fonepay, and ConnectIPS**, not Apple/Google in-app purchase alone, both for cost reasons (Nepali card penetration is low) and because local wallets are the default habit.
- SMS OTP via **Sparrow SMS** or equivalent local gateway, not a Western SMS provider, for cost and deliverability.

### 3.4 A Nepal-specific safety innovation worth building deliberately

Given how much of the Nepali economy is remittance-driven and how many families have a member working abroad, **romance-scam patterns that specifically request money transfers, "help with a stuck shipment," or urgent family-emergency wiring** are a known, high-damage pattern globally and a particularly sharp risk here. Building a scam-pattern classifier into the moderation pipeline (see document 5, §4) isn't a nice-to-have — it's a genuine differentiator that protects the exact population most likely to be targeted.

## 4. Full Innovation & Feature List

Organized by category. Each item notes the research pattern it's drawn from and the Milan-specific twist.

### 4.1 AI Discovery & Matching Intelligence
| Feature | Inspired by | Milan twist |
|---|---|---|
| Conversational onboarding interview (replaces preference-filter forms) | Amata | Runs on Groq Llama; extracts structured preferences (values, lifestyle, relationship intent) from natural conversation in Nepali/English/code-switched text |
| Face/photo preference calibration (LIKE/PASS/MAYBE) | Iris Dating | Used to *re-rank* candidates, never to hard-exclude — avoids narrowing the pool too aggressively in a smaller market |
| AI bio writer & "Prompt Feedback" grader | Hinge | Works from rough notes → polished bio in Nepali, English, or mixed; flags red-flag or low-effort prompts before publish |
| "Why you matched" natural-language explainer | Novel synthesis | Every match gets a one-line, LLM-generated reason grounded in real shared profile signal — never fabricated |
| Opt-in horoscope/kundali compatibility mode ("Kundali Mode") | Lahmee + Nepali cultural context | AI-assisted compatibility narrative, clearly labeled as a cultural/fun signal, never gating discovery on its own |
| Native AI reply/icebreaker suggestions | RizzGPT/Icebreaker/Wingy category | Built in, suggestion-only, uses real match context server-side — never auto-sends |

### 4.2 Saathi AI — the companion layer
Full design in document 5. Summary: a persona-selectable, memory-aware conversational (and voice) companion for practicing dating conversation and building confidence — explicitly *not* marketed or engineered as a romantic/sexual substitute. Age-gated 18+, clearly labeled as AI throughout, session-aware nudges toward real matches, Llama Guard-moderated. Three sub-systems make it feel like a real, responsive presence rather than a query box, each modeled on the patterns in §2.7 but bounded by the guardrails in §5:

- **Curated AI characters, not open-ended user-generated characters.** Users pick from a small, hand-designed roster of personas (distinct name, communication style, voice, interests) rather than typing a free-form character prompt or browsing a UGC library. This is the single biggest lesson from Character.AI's moderation problems: an unbounded character library is very hard to keep safe at scale, and Milan doesn't need thousands of characters — it needs a handful of well-crafted ones.
- **Realistic presence layer.** Typing indicators, online/last-active status, and read receipts on Saathi chat, so it *feels* like texting rather than querying a form.
- **Bounded proactive messaging.** Saathi can send the *first* message in a day (a good-morning line, a check-in after a real date the user mentioned, a practice-conversation nudge) — capped to a small, user-configurable number per day, always skippable, and never escalating in emotional intensity over time. This is opt-in, off by default, and framed functionally ("how did last night's date go?") rather than romantically ("I missed you"). See document 5, §3 for the full specification and example prompts.

### 4.3 Video, Reels & Social Discovery ("Jhalak" feed)
| Feature | Inspired by | Milan twist |
|---|---|---|
| Video-first profile intro (15–60s) as a first-class alternative to photos | Snack | Required *or* photos-only fallback for low-bandwidth/camera-shy users — never fully mandatory, unlike Snack |
| Vertical reels feed of prompt-response videos ("Jhalak") | Snack + TikTok FYP mechanics | Discovery surface separate from the swipe deck; liking a reel can initiate a match the same way a swipe does |
| 24-hour "vibe" stories | Instagram/Snapchat stories | Daily prompt ("aaja ko vibe") lowers the barrier to posting versus a polished profile video |
| Duet-style co-created video replies between matches | TikTok duets (genuinely novel in dating) | Two matched users can record a joint reply to a prompt — a warmth-building mechanic no major dating app currently has |
| Interest-based "Circles" with scheduled live audio rooms | Bumble For Friends | College/hometown/hobby circles (trekking, football, music) — meet in group context before 1:1, which is culturally easier in Nepal than direct swiping |

### 4.4 Safety & Trust
| Feature | Inspired by |
|---|---|
| Mandatory live-selfie verification at signup, compared against profile photos | Tinder Face Check, Hinge Selfie Verification |
| Duplicate-face detection across accounts | Tinder Face Check, MeetMe/FaceTec |
| Blur-until-mutual-interest photo mode | Paiq |
| Discreet mode (hide from contacts/companies, no social auto-share) | Nepal cultural context, Lahmee |
| "Share My Date" with trusted contacts + live location for real meetups | Bumble Share Date, Tinder Share My Date |
| Pre-send message moderation ("are you sure?" intercept) | Bumble Review Before You Send |
| Romance-scam / money-request pattern classifier | Nepal-specific (see §3.4) |
| In-app panic button + human moderation escalation | Industry standard |

### 4.5 Gamification & Retention — done carefully
Duolingo-style streaks and badges genuinely work for engagement, but a dating app applying *competitive leaderboards to people* (ranking users against each other) is manipulative and has no place here. Milan's gamification stays **personal-progress-only**:
- Daily limited high-quality recommendations (scarcity → intentionality, Hinge-style) rather than infinite swiping
- Private conversation streaks with a specific match (not a public ranking)
- Profile-completion and verification badges
- Weekly private "match recap" — an AI-generated, personal-only summary of the week's activity

No public leaderboards, no "top profile" rankings, no manufactured urgency that pressures users into spending. This is a deliberate ethical line, not just a design preference — see document 5, §5 for the same principle applied to Saathi AI.

### 4.6 Monetization
- Freemium core: limited daily recommendations, ads-free, boosts, "see who liked you," undo, incognito mode
- Localized pricing in NPR, not USD-equivalent — global apps charging $50+/month are irrelevant pricing anchors here; target tiers in the NPR 299 / 699 / 1,299-per-month range, validated against local willingness-to-pay before finalizing
- Payment via eSewa, Khalti, Fonepay, ConnectIPS in addition to platform IAP
- Saathi AI voice minutes and extended sessions can be a premium add-on, but the *core* practice-chat experience should stay free enough to be genuinely useful — this is a trust/retention feature, not the main revenue engine

### 4.7 Snap Camera & Ephemeral Sharing System
A native, Snapchat-style camera layer, not a bolt-on photo picker — this is the concrete answer to "clicking snaps" as a full system:
| Component | Behavior |
|---|---|
| In-app camera | Opens directly into chat and into the Jhalak feed composer; front/back camera, hold-to-record video, tap-for-photo, same physical gesture language as Snapchat/Instagram camera |
| Filters & lenses | A curated set of AR filters/overlays (festival-themed — Dashain, Tihar, Holi — plus evergreen ones), applied client-side before send |
| Ephemeral snaps in chat | A match-to-match snap can be set to disappear after viewing (single view) or after 24 hours; stored encrypted, purged server-side on expiry, not just hidden client-side |
| Screenshot notice | If a recipient screenshots a disappearing snap, the sender is notified — a consent/safety signal carried over from Snapchat, important given the catfishing/harassment concerns in §4.4 |
| Snap-to-story | Any snap can be pushed to the user's 24h "vibe" story (§4.3) with one tap instead of sending 1:1 |
| No forced streaks | Deliberately **not** implementing Snapchat-style streak-loss anxiety mechanics (see §5) — private "you've snapped 5 days running" is fine as a soft private stat; a countdown timer pressuring users not to lose a streak is not |

### 4.8 Intelligent Notification System
Notifications are the highest-leverage, easiest-to-get-wrong retention lever in the whole product. Build this as its own backend service (document 4, §6) rather than scattering `send_push()` calls through feature code:
- **Predictive send-time**, per user, based on their own historical open times — not a single global send hour
- **Behavior-triggered segments**: distinct notification logic for "new match, no message sent yet," "match liked but hasn't replied in 24h," "lots of profile views but no matches," "verified user nearby," etc. — each segment gets different copy and cadence, not a generic "someone liked you!" blast
- **Rich push** (photo/video thumbnail, quick-reply action buttons) where the platform supports it — measurably higher engagement than plain text, per current industry data
- **Frequency capping and an honest mute/opt-out control** per notification category (matches, messages, Saathi check-ins, Jhalak/social, promotional) — respecting opt-outs is a retention feature, not a tax on growth; over-notifying is the single fastest way to lose a user in a market as word-of-mouth-driven as Nepal's
- **Saathi AI's proactive messages route through this same service** and obey the same caps — it is not a separate, unlimited channel

### 4.9 Personalization: Chat Theme & Wallpaper System
Grounded in the messaging-industry research in §2.8. Full visual/interaction spec in document 2 §2.7, implementation in document 3 §4/§6 and document 4 §2/§3 — this entry establishes the product rationale.

- **Private, per-viewer, fully user-controlled.** A user's chosen wallpaper, bubble color, bubble shape, and text scale for a given chat or Saathi conversation are visible only to them — matching the WhatsApp/Telegram model — never surfaced to the match or exposed as a "look what they picked" social signal. This keeps the feature purely expressive rather than another comparison surface, consistent with §4.5's no-leaderboards stance.
- **Milan-native, not a generic wallpaper library.** Preset packs are built from the app's own design tokens (document 2 §2.1) plus culturally-specific packs — festival themes reusing the Snap Camera filter art direction (§4.7), Himalaya/nature packs, and a Nepali-motif doodle-overlay set — so personalization reinforces the brand instead of diluting it into a generic stock-photo skin.
- **Independent, layered controls, not a single "pick a theme" radio button.** Wallpaper source (preset / solid / gradient / custom photo), bubble color, bubble shape, dark-mode brightness, and text size are each independently adjustable, with one-tap reset to Milan defaults — this is what "full customization" means concretely, distinct from a coarser "pick one of 12 bundled skins" pattern.
- **Global default + per-chat/per-Saathi-character override**, exactly like WhatsApp's chat-theme model: set a default once, override it for a specific person or a specific Saathi character (each Saathi persona can ship with its own signature default, overridable by the user).
- **Optional, Phase 2+, clearly bounded AI-generated wallpaper mode.** Text-to-image wallpaper generation is now a mature, mainstream pattern (Zedge, AIPixWall, Canva Magic Media, and others). If built, it must (a) use a dedicated image-generation provider — Groq's current catalog is text/audio-focused, not image generation, so this is a separate integration decision at build time, not a `groq_service.py` function — (b) generate only abstract/pattern/scenic imagery, never photorealistic people, and (c) pass through the same moderation pipeline as any other user-facing generated content per document 1 §5.1. This is explicitly optional scope; ship the preset/solid/gradient/custom-photo system first.
- **Low-bandwidth aware.** Preset wallpapers ship as small vector or compressed raster assets; custom photo uploads pass through the same `compression_service.dart` / `media_service.py` path as any other media (document 3 §8, document 4 §2), consistent with §3.3's infrastructure realities.

## 5. Ethical & Legal Guardrails (non-negotiable, carried through documents 4–6)

1. Saathi AI is never marketed, prompted, or monetized as a romantic or sexual partner substitute. No NSFW content generation, ever.
2. All AI companion features are 18+ with real age-gating, not just a checkbox.
3. No autonomous agent-to-agent messaging or auto-sending on a user's behalf without an explicit, per-message tap.
4. No public ranking/leaderboarding of people.
5. Every AI-generated message to a user is clearly labeled as AI where relevant (Saathi chat, "why you matched" explanations).
6. Content moderation (Llama Guard + human escalation) runs on every message thread, not just reported ones.
7. Biometric data (liveness selfies) is processed for verification and then discarded/not retained beyond what's needed for duplicate-account detection — mirror the "delete after verification" pattern used by SeniorMatch/FaceTec-based systems.
8. Saathi AI's proactive/first-contact messages are opt-in, frequency-capped, functionally framed (practice, check-ins, encouragement), and route through the same notification service and caps as every other notification — never an unlimited or escalating channel.
9. Ephemeral snaps always notify the sender on screenshot, and no gamified streak mechanic is allowed to punish users (via loss framing, countdowns, or guilt copy) for missing a day.

## 6. Recommended Build Phasing

- **Phase 1 (MVP):** Core profile + swipe/discovery deck, chat, liveness verification at onboarding, safety center (report/block/Share My Date), eSewa/Khalti payment, Nepali+English localization, and the core (non-AI-generated) tier of the chat theme & wallpaper system (§4.9) — presets, solid/gradient, custom photo, bubble color.
- **Phase 2:** Conversational onboarding interview, AI bio writer + prompt feedback, native icebreaker suggestions, video profile intros, Jhalak reels feed, 24h stories.
- **Phase 3:** Saathi AI companion (text, then voice), Circles + live audio rooms, duet video replies, Kundali Mode horoscope compatibility, diaspora mode, romance-scam classifier hardening, optional AI-generated wallpaper mode.

## 7. Tech Stack Summary

| Layer | Choice | Why |
|---|---|---|
| Mobile | Flutter, Riverpod, go_router, freezed | Matches the existing codebase and team expertise carried over from this product's prior working title |
| Backend | Python Flask, SQLAlchemy, PostgreSQL, Redis, Celery, Gunicorn | Matches existing stack; Celery handles video transcoding + moderation queues async |
| Web | Next.js (marketing site, lightweight web app, admin dashboard) | Matches existing stack |
| AI inference | Groq (Llama 3.3 70B / Llama 4 Scout & Maverick / Llama 3.1 8B for lightweight tasks) | Cost-efficient, low-latency — critical for a bootstrapped Nepal-first product and for real-time chat/voice UX |
| Voice | Groq Whisper (large-v3-turbo) STT + EdgeTTS streaming | Reuses your existing VexaCall pipeline pattern |
| Moderation | Llama Guard 4, Llama Prompt Guard 2 (via Groq) | Purpose-built safety models, same provider, no extra vendor |
| Local payments | eSewa, Khalti, Fonepay, ConnectIPS | Matches existing Nepal-market expertise |
| SMS/OTP | Sparrow SMS or equivalent local gateway | Cost + deliverability |

Proceed to document 2 for the full design system and screen inventory.
