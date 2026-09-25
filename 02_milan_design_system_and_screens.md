# Milan v2 — Design System & Screen Inventory

> **Document 2 of 7.** Visual language + the complete list of screens the app needs. Feed this alongside document 3 (Flutter build prompt) to your AI code editor — document 3 references these tokens and screens by name rather than re-specifying them.

---

## 1. Design Philosophy

Milan should feel *warm, confident, and unmistakably Nepali* — never a reskinned Tinder clone. The existing identity (Marigold / Dhaka Maroon palette, Sora/Manrope/Noto Sans Devanagari type system, "Junction Mark" motif) carries forward unchanged; everything below extends it to cover the new AI, video, social, and personalization surfaces rather than replacing it. The **Junction Mark** — two paths meeting — reads more literally than ever now that the app itself is named Milan (मिलन, "union"/"meeting"/"confluence"): keep it as the anchor mark for splash, app icon, and empty-state illustrations.

Three principles govern every new screen added in this revision:
1. **Realness over gloss.** Verification badges, liveness checkmarks, and "AI-generated" labels are treated as first-class visual elements, not fine print — trust is the product.
2. **Warm minimalism.** Generous whitespace, one strong accent color per screen, soft warm-tinted shadows instead of pure black — never a cluttered, notification-badge-everywhere feel.
3. **Culturally legible, not culturally decorative.** Marigold/Dhaka motifs, festival filter packs, and Devanagari type are functional design decisions for a Nepali audience, not surface-level ornamentation on an otherwise generic template. This principle applies directly to the personalization system in §2.7 — cultural wallpaper packs are curated design work, not a stock-photo dump.

## 2. Design Tokens

### 2.1 Color

| Token | Hex | Usage |
|---|---|---|
| `marigold.500` (primary) | `#F5A623` | Primary actions, active states, swipe-like accent |
| `marigold.700` | `#C97D0C` | Primary pressed/hover |
| `marigold.100` | `#FDE9C8` | Primary surface tint, selected chip background |
| `dhaka.500` (secondary) | `#7B1E3A` | Secondary actions, premium/paywall accents, Saathi AI brand color |
| `dhaka.700` | `#591129` | Secondary pressed |
| `dhaka.100` | `#F3DCE2` | Secondary surface tint |
| `pine.500` (tertiary) | `#1F6F54` | Verification/safety/success accents (deliberately distinct from generic green) |
| `pine.100` | `#DCEFE7` | Success surface tint |
| `ink.900` | `#1F1B16` | Primary text |
| `ink.600` | `#4A443C` | Secondary text |
| `ink.400` | `#8A8377` | Placeholder/disabled text |
| `paper.0` | `#FFFBF5` | Base background (warm off-white, not pure white) |
| `paper.100` | `#F5F0E6` | Card/section background |
| `line.200` | `#E8E1D3` | Dividers, input borders |
| `error.500` | `#C0392B` | Errors, report/block actions |
| `warning.500` | `#B8791A` | Scam-pattern warnings, safety interstitials |

**Dark mode:** invert `paper`/`ink` roles (`paper.0` → `#161310`, `ink.900` → `#F5F0E6`), keep `marigold`, `dhaka`, and `pine` hues but drop their luminance by ~10% to avoid glare on dark backgrounds. Every screen in §4 must be specified for both modes.

### 2.2 Typography

| Style | Font | Size / Line height | Weight |
|---|---|---|---|
| Display | Sora | 32/40 | 700 |
| H1 | Sora | 28/36 | 700 |
| H2 | Sora | 24/32 | 600 |
| H3 | Sora | 20/28 | 600 |
| H4 | Manrope | 18/24 | 600 |
| Body Large | Manrope | 16/24 | 400 |
| Body | Manrope | 14/20 | 400 |
| Caption | Manrope | 12/16 | 500 |
| Overline | Manrope | 11/16, uppercase, +0.04em tracking | 600 |

Devanagari fallback: any string containing Devanagari Unicode range (U+0900–U+097F) renders in **Noto Sans Devanagari** at the same size/weight mapping. Build the `AppText` widget (document 3) to auto-detect and swap font family per-string, not per-screen, since Nepali/English code-switching happens mid-sentence in real usage.

### 2.3 Spacing, radius, elevation

- Spacing scale (px): `4, 8, 12, 16, 24, 32, 48, 64` — all margins/padding snap to this scale.
- Corner radius: `sm=8` (chips, small buttons), `md=16` (cards, inputs), `lg=24` (swipe deck cards, bottom sheets, matching the "Junction Mark" rounded motif), `pill=999` (tags, filter chips).
- Elevation: three tiers only — `flat` (0), `raised` (subtle warm-tinted shadow, `rgba(123,30,58,0.08)` blur 12), `floating` (bottom sheets/modals, blur 24, same tint). No heavy drop shadows anywhere.

### 2.4 Motion

- Swipe deck: card follows finger 1:1, rotates up to 12° at max drag, snaps back with a spring curve (`Curves.elasticOut`-equivalent) if released below the commit threshold.
- Match celebration: marigold-petal confetti burst, ≤900ms, skippable by tap.
- Saathi AI typing indicator: three-dot pulse, 1.2s loop, `dhaka.500`.
- Story/reel transitions: 220ms crossfade + slight scale (0.96→1.0), never a hard cut.
- Chat theme changes (§2.7) apply with a 180ms crossfade on the wallpaper layer only — bubbles restyle instantly, never a hard flash across the whole screen.
- Respect `prefers-reduced-motion` / platform accessibility settings — fall back to opacity-only transitions.

### 2.5 Iconography & imagery

- Line icons, 1.5px stroke, rounded caps — no filled/glyph icons except for active nav-bar states.
- Festival filter/lens pack (Dashain tika, Tihar diyo, Holi color splash) lives in the Snap Camera system (screen inventory §4.6) and is refreshed seasonally; the same art direction feeds the festival wallpaper pack in §2.7 so the two surfaces feel like one coherent seasonal identity, not two unrelated asset sets.
- Illustration style for empty states: flat, warm-palette, line-art figures — never stock photography, never generic 3D-blob illustrations.

### 2.6 Core components to build once, reuse everywhere

| Component | Notes |
|---|---|
| `SwipeCard` | Photo/video carousel, prompt overlay, verification badge, distance/age chip |
| `PrimaryButton` / `SecondaryButton` / `GhostButton` | Marigold/Dhaka/transparent variants, all with loading + disabled states |
| `ChatBubble` | Sent/received variants, read-receipt ticks, timestamp on long-press, AI-labeled variant (dashed border + small "AI" tag for Saathi messages); bubble color and shape are theme-driven per §2.7, never hardcoded |
| `TypingIndicator` | Shared by match chat and Saathi chat |
| `StoryRing` | Gradient ring (marigold→dhaka) around avatar when an unseen story exists, gray ring when seen |
| `VerifiedBadge` | Pine-colored checkmark, tap for verification detail sheet |
| `ReelPlayerControls` | Mute, like, comment, share, report — vertical action rail, TikTok-style |
| `CameraShell` | Shared camera UI for profile video, story snaps, and chat snaps — filter carousel, hold-to-record, tap-to-photo |
| `NotificationPreferenceRow` | Category label + toggle + frequency stepper, used across the whole notification settings screen |
| `AICharacterCard` | Used in Saathi character-selection gallery |
| `CompatibilityMeter` | Circular/arc meter for match %, reused on match detail and Kundali Mode screens |
| `ThemePickerSheet` | New (§2.7) — tabbed bottom sheet (Presets / Solid & Gradient / Photo / Bubble Color) with a live preview pane; opens scoped to "this chat," "this Saathi character," or "all chats" depending on entry point |
| `WallpaperPreviewCard` | New (§2.7) — thumbnail tile used inside `ThemePickerSheet` and the Chat Theme & Wallpaper Studio screen; shows a mini sample bubble pair over the candidate wallpaper so the pairing is judged together, not the wallpaper alone |

## 2.7 Personalization: Chat Theme & Wallpaper System

Product rationale and competitive research in document 1 §2.8 and §4.9 — this section is the concrete design spec. Implemented in document 3 §4/§6 (Flutter) and document 4 §2/§3 (backend/storage).

### 2.7.1 Principles

- **Private per viewer.** A theme choice — wallpaper, bubble colors, bubble shape, text scale, dark-mode brightness — is visible only to the user who set it, exactly like WhatsApp/Telegram chat themes. The other person in a match, and the Saathi character itself, never see or react to it.
- **Layered, not bundled-only.** Every control below is independently adjustable. Presets exist as a fast starting point (a coordinated wallpaper + bubble-color pairing a user can apply in one tap), but nothing forces a user to accept a bundle wholesale — they can start from a preset and then override just the bubble color, for instance.
- **Global default + scoped override.** One default theme applies everywhere; a specific 1:1 chat or a specific Saathi character's chat can override it. Resolution order: chat/character-specific override → global default → Milan factory default. One-tap "Reset to default" at every level.
- **Milan-native asset library.** No integration with a third-party generic wallpaper app or stock-photo library. Every preset ships as part of the app's own design system.

### 2.7.2 Wallpaper sources

| Source | Behavior |
|---|---|
| Preset packs | Curated, coordinated {wallpaper + bubble-color pairing}. Ship at least: **Brand** (marigold/dhaka/pine gradients and solids drawn straight from §2.1), **Festival** (Dashain, Tihar, Holi, Teej — same art direction as the Snap Camera filter pack, §2.5), **Nature** (Himalaya skyline, terraced hills, rhododendron line-art, monsoon-cloud gradient), **Minimal** (paper-tone solids and soft two-color gradients for users who want a plain look), and a **Saathi** pack (dhaka-forward tones, one signature look per curated character from document 5 §2.2, distinct enough that a Saathi conversation is never visually mistaken for a match chat even before reading the AI-labeled header) |
| Solid color | Full token palette (§2.1) plus a broader curated color wheel; not restricted to brand tokens alone, since personal taste extends beyond the brand |
| Gradient | Two-color picker, linear or radial, live-previewed behind sample bubbles before applying |
| Custom photo | Pull from device gallery or camera; supports crop, fit/tile/blur, and a brightness dim slider for dark mode (mirrors the WhatsApp pattern in document 1 §2.8); passes through the same compression and moderation pipeline as any other user-uploaded media (document 4 §2) — a wallpaper is private, but it is still a stored asset and still subject to the same content-safety pass as a profile photo |
| Doodle overlay | Optional, layered on top of any of the above: a Milan-drawn line-art pattern set (paisley, marigold petals, mountain-ridge repeat, Mithila-inspired geometric line work) at low opacity, togglable independent of the base wallpaper |
| AI-generated *(Phase 2+, optional)* | Text-prompt → abstract/pattern/scenic wallpaper via a dedicated image-generation provider (not Groq — see document 1 §4.9 and document 5 §1 for why this is a separate integration). Hard constraint: never generates photorealistic people, and every generation passes moderation before it can be applied. Ship the rest of this system first; treat this row as explicitly deferrable scope. |

### 2.7.3 Bubble & text controls

- **Bubble color:** sent and received bubbles have independently settable colors (or inherit from the selected preset); enforce a minimum contrast ratio against the chosen text color and against the wallpaper so messages stay legible — reject/flag combinations that fail a basic WCAG-AA-equivalent contrast check rather than silently allowing unreadable text.
- **Bubble shape:** two options — soft/rounded (default, matches `lg=24` radius language) and a slightly sharper variant (`md=16`) for users who prefer a denser, less playful look. No "tail" toggle needed if the rounded-corner grouping already reads clearly as sender vs. recipient.
- **Text scale:** respects the OS accessibility text-size setting by default, with an in-app override stepper for users who want chat text specifically larger/smaller without changing their whole device's text size.
- **Dark-mode brightness:** a single slider per wallpaper controlling how much the wallpaper is dimmed in dark mode, independent of the light-mode version of the same wallpaper.

### 2.7.4 Entry points

- Chat Thread (screen 29) overflow menu → "Chat theme" → opens `ThemePickerSheet` scoped to that match.
- Saathi Chat (screen 49) header menu → "Chat theme" → opens `ThemePickerSheet` scoped to that character.
- Settings → new **Chat Theme & Wallpaper Studio** screen (§3.9, screen 67) → full-screen version of the same controls, scoped to "all chats" (the global default), with the same live preview pane.

### 2.7.5 Accessibility & performance

- Every preset ships in a pre-verified light and dark variant; a custom wallpaper's dark-mode brightness must be user-adjustable (§2.7.3) rather than assuming one brightness works for both.
- Contrast-check bubble/text/wallpaper combinations before allowing "Apply" (§2.7.3).
- Respect `prefers-reduced-motion` for the wallpaper crossfade (§2.4).
- Preset assets are small (vector where possible, compressed WebP otherwise) so switching themes is instant and doesn't re-trigger a network fetch on a slow connection, consistent with document 1 §3.3's low-bandwidth requirements.

## 3. Screen Inventory

Full list, grouped by flow. **~67 screens total** (the original ~65-screen inventory plus the new Chat Theme & Wallpaper Studio screen in §3.9 — treat all counts in this document as approximate). Each row: purpose, key elements, and states an AI code editor should scaffold (empty/loading/error where relevant — omitted when not applicable).

### 3.1 Onboarding & Verification (11)
| # | Screen | Purpose | Key elements | States |
|---|---|---|---|---|
| 1 | Splash | Brand load | Junction Mark logo animation | — |
| 2 | Language Select | Nepali/English choice | Two large tappable cards | — |
| 3 | Phone Entry | Start auth | Phone input, country code locked to +977 with override | Error (invalid number) |
| 4 | OTP Verify | Confirm phone | 6-digit input, resend timer, Sparrow SMS-backed | Error, expired |
| 5 | Basic Info | Name, DOB, gender | Form, age-gate check (18+ hard block) | Error |
| 6 | Photo Upload | Min 2, max 6 photos | Grid uploader, reorder by drag | Error (upload failed) |
| 7 | Video Intro Capture | Required-or-skip 15–60s intro video | Uses `CameraShell`, countdown, retake | — |
| 8 | Liveness Verification | Face Check-style live selfie | Camera guide overlay, real-time face position feedback | Fail/retry, success |
| 9 | Conversational Interview | AI-driven onboarding interview (§4.1 of doc 1) | Chat-style UI, Saathi-branded but clearly "onboarding assistant," progress dots | — |
| 10 | Location Permission Primer | Explain why before OS prompt | Illustration + rationale copy | — |
| 11 | Notification Permission Primer | Explain categories before OS prompt | Preview of 2–3 notification types | — |

### 3.2 Profile & Identity (7)
| # | Screen | Purpose | Key elements |
|---|---|---|---|
| 12 | My Profile (view) | Self-view of public profile | Photo/video carousel, prompts, badges |
| 13 | Edit Profile | Edit all fields | Same layout as public view, inline edit |
| 14 | Prompt Answers Editor | Hinge-style prompt selection | Prompt bank picker, 3 active slots |
| 15 | AI Bio Assistant | Turn notes → polished bio | Rough-notes input → 3 AI draft options → edit |
| 16 | Prompt Feedback | AI grades prompts pre-publish | Per-prompt score + suggestion chip |
| 17 | Verification Status | Badge detail | Verified/unverified state, re-verify CTA |
| 18 | Privacy & Discreet Mode | Hide-from-contacts, blur-until-match toggles | Toggle list with plain-language explanation per toggle |

### 3.3 Discovery & Matching (9)
| # | Screen | Purpose | Key elements | States |
|---|---|---|---|---|
| 19 | Discover (Swipe Deck) | Core discovery | `SwipeCard` stack, filter shortcut, mode switch (Serious/Casual) | Empty (no more profiles today), loading |
| 20 | Discovery Filters | Age/distance/intent/etc. | Sliders, chips | — |
| 21 | Mode Switch Sheet | Serious vs Casual, like Bumble Modes | Two large cards with descriptions | — |
| 22 | Match Celebration | "It's a match" moment | Confetti motion, both photos, CTA to message | — |
| 23 | Match Detail / Why We Matched | AI-generated explainer | `CompatibilityMeter`, grounded reasons list | — |
| 24 | Kundali Mode (Horoscope) | Opt-in kundali compatibility | Birth details form → AI-generated compatibility narrative, clearly labeled cultural/fun signal | — |
| 25 | Who Liked You | Paywalled grid | Blurred grid, unlock CTA | Empty |
| 26 | Boost Purchase Sheet | Temporary visibility boost | Package options, NPR pricing | — |
| 27 | Rewind/Undo | Undo last swipe | Single confirmation card | — |

### 3.4 Chat & Real-Time Connection (9)
| # | Screen | Purpose | Key elements | States |
|---|---|---|---|---|
| 28 | Matches Inbox | List of active matches | Avatar + `StoryRing`, last message preview, unread state | Empty |
| 29 | Chat Thread | 1:1 messaging | `ChatBubble`, `TypingIndicator`, media/voice-note attach, snap-camera launcher, overflow-menu entry point to Chat Theme (§2.7.4) | Loading history |
| 30 | AI Icebreaker Panel | Suggested openers (in-thread) | 3 suggestion chips, tap-to-insert-then-edit (never auto-send) | — |
| 31 | Voice Note Recorder | Record/send voice message | Waveform preview, hold-to-record | — |
| 32 | Snap Camera (in chat) | `CameraShell` variant | Filter carousel, single-view/24h toggle | — |
| 33 | Ephemeral Snap Viewer | View a disappearing snap | Full-screen, hold-to-view, screenshot-detection notice | Expired |
| 34 | Share My Date | Send date plan to trusted contact | Contact picker, date/time/location fields, live-location toggle | — |
| 35 | Video Call | In-app video call | Standard call UI, safety-report shortcut always visible | Connecting, failed |
| 36 | Voice Call (audio-only) | Lighter-weight than video, better for low bandwidth | Waveform avatar, call controls | — |

### 3.5 Jhalak Reels & Social Discovery (9)
| # | Screen | Purpose | Key elements |
|---|---|---|---|
| 37 | Jhalak Feed | Vertical reels discovery | `ReelPlayerControls`, prompt-response captions |
| 38 | Reel Camera/Composer | Record a prompt-response reel | `CameraShell`, prompt-of-the-day overlay, trim/filter |
| 39 | Duet Recorder | Co-create a reply with a match | Split-screen record UI, original clip pinned |
| 40 | Stories Bar | Horizontal story rail (home top) | `StoryRing` list |
| 41 | Story Viewer | Full-screen story playback | Tap-to-advance, reply field |
| 42 | Story Camera | Post a 24h "aaja ko vibe" story | `CameraShell`, daily prompt sticker |
| 43 | Circles Directory | Browse interest-based communities | Category grid (trekking, football, music, college, hometown) |
| 44 | Circle Detail | Community home | Member grid, upcoming live audio room, join CTA |
| 45 | Live Audio Room | Scheduled group audio | Speaker/listener grid, raise-hand queue, moderator controls |

### 3.6 Saathi AI Companion (8)
| # | Screen | Purpose | Key elements |
|---|---|---|---|
| 46 | Saathi Intro/Consent | First-run explanation | Plain-language "this is AI, here's what it's for and isn't for," 18+ confirm |
| 47 | Character Selection Gallery | Choose a curated persona | `AICharacterCard` grid, short persona description each |
| 48 | Character Detail | Preview before starting | Persona bio, sample opening line, "start chat" CTA |
| 49 | Saathi Chat | Text conversation | `ChatBubble` (AI-labeled variant), `TypingIndicator`, "AI" tag persistent in header, header-menu entry point to Chat Theme scoped to this character (§2.7.4) |
| 50 | Saathi Voice Call | Voice-mode conversation | Waveform avatar, live transcript toggle |
| 51 | Saathi Settings | Proactive messaging controls | Frequency stepper, category toggle, "pause Saathi" switch |
| 52 | Session Debrief | Optional post-real-date reflection prompt from Saathi | Short structured reflection form, feeds back into matching signal (with consent) |
| 53 | What Saathi Remembers | Transparency screen | Plain list of stored memory items, per-item delete, "clear all" |

### 3.7 Safety & Trust (6)
| # | Screen | Purpose | Key elements |
|---|---|---|---|
| 54 | Safety Center Home | Hub for all safety tools | Cards: report, block list, share my date, verification, scam-awareness tips |
| 55 | Report Flow | Multi-step reporting | Reason picker → evidence attach → confirm |
| 56 | Block List | Manage blocked users | Simple list, unblock action |
| 57 | Scam Warning Interstitial | Triggered by AI classifier | Plain-language warning, "don't send money" education, report shortcut |
| 58 | Panic/Emergency | Quick-access safety action | Large single CTA, local emergency contact info |
| 59 | Verification Detail | Explain how verification works | Step visual, re-verify CTA |

### 3.8 Notifications & Settings (7)
| # | Screen | Purpose | Key elements |
|---|---|---|---|
| 60 | Notification Center | In-app notification feed | Grouped by category, mark-all-read |
| 61 | Notification Preferences | Per-category control | `NotificationPreferenceRow` list (matches, messages, Saathi, social, promo) |
| 62 | Account Settings | Core account management | Email/phone change, delete account, data export |
| 63 | Language & Accessibility | Nepali/English, text size, reduced motion | Toggle list |
| 64 | Payment Methods | eSewa/Khalti/Fonepay/ConnectIPS management | Linked-method list, add-new flow |
| 65 | Subscription Plans | Compare/select premium tier | 3-tier comparison table, NPR pricing |
| 66 | Help & Support / FAQ | Support access | Searchable FAQ, contact-support CTA |

### 3.9 Personalization (1 — new in this revision)
| # | Screen | Purpose | Key elements | States |
|---|---|---|---|---|
| 67 | Chat Theme & Wallpaper Studio | Full-screen version of the `ThemePickerSheet` controls (§2.7), scoped to "all chats" by default | Tabs: Presets / Solid & Gradient / Photo / Bubble Color; live preview pane with sample sent/received bubbles; bubble-shape toggle; text-size stepper; dark-mode brightness slider; "Apply to all chats" vs. context-specific scope indicator when opened from a chat/Saathi entry point; "Reset to default" | Uploading (custom photo), generating (AI mode, if built) |

*(Numbering continues sequentially past 64 in the settings table above; treat the inventory as ~67 screens once settings, support, and the new Studio screen are included — round to "~67 screens" when referencing this doc elsewhere.)*

## 4. Handoff Note for Document 3

Every screen above should be scaffolded as its own route in `go_router` using the naming convention `/feature/screen-name` (e.g. `/saathi/character-gallery`, `/jhalak/feed`, `/safety/report`, `/settings/chat-theme`). Document 3 assumes this inventory and these tokens exist and does not repeat them — it specifies architecture, state management, and implementation detail per feature domain instead, including the `themeProvider` that powers the personalization system in §2.7.
