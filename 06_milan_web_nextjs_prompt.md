# Milan v2 — Web (Next.js) Build Prompt: Marketing Site + Admin Dashboard

> **Document 6 of 7.** Paste-into-AI-code-editor prompt for the web surface. Two distinct apps in one Next.js project (or two projects sharing a design-token package — your call at build time): a public marketing site, and an internal admin/moderation dashboard. This is intentionally the lightest of the seven documents — the mobile app is the product; the web surface supports it.

---

## Prompt starts here

You are building the **Milan v2** web presence in **Next.js (App Router)** with **Tailwind CSS** and **shadcn/ui**. Reuse the design tokens from `02_milan_design_system_and_screens.md` §2 (color/type/spacing/personalization) as a shared Tailwind config — the web surface must feel like the same brand as the app, not a generic SaaS template with the logo swapped in.

### 1. Public marketing site

Routes:
```
/                    // hero, value prop, download CTAs (App Store/Play Store badges)
/features            // discovery/matching, Jhalak reels, Saathi AI, safety — one section each
/safety              // dedicated trust page: verification, reporting, Share My Date, scam-awareness education
/pricing             // NPR-denominated tier comparison, matches doc 1 §4.6
/saathi              // explains what Saathi AI is (and isn't) in plain language — this page matters for
                      // App Store review and user trust; be explicit that it's a practice companion,
                      // not a romantic AI, right in the marketing copy, not just the fine print
/download
/blog                // optional; only build if content plan exists — don't scaffold an empty CMS integration
/privacy, /terms
```

- Bilingual (Nepali/English) via `next-intl` or the App Router's built-in i18n routing (`/ne/...`, `/en/...`), same ARB-equivalent string source as the Flutter app where practical.
- Fully static/SSG where possible (marketing pages don't need per-request data) — deploy on the same DigitalOcean droplet via a Node process behind nginx, or a static export served directly by nginx if no server-side personalization is needed.
- The `/safety` and `/saathi` pages are not just marketing — treat them as genuine trust documentation; they're what a skeptical parent, a cautious first-time user, or an app-store reviewer will read.

### 2. Admin & moderation dashboard

This is the operational tool your team uses daily — prioritize information density and speed over marketing polish.

Routes:
```
/admin/login                       // admin-role auth, separate from consumer auth
/admin/moderation                  // queue of Reports + ModerationEvents + ScamFlags needing review
/admin/moderation/:caseId          // case detail: full thread context, user history, action buttons
/admin/users                       // search/filter users, view verification status, suspend/ban
/admin/users/:id                   // user detail: profile, reports filed/against, verification history
/admin/verification-queue          // manual review for liveness-check edge cases the automated pass didn't resolve
/admin/circles                     // manage Circles categories, feature/unfeature, schedule live audio rooms
/admin/personalization              // curate the Chat Theme & Wallpaper preset catalog (doc 2 §2.7.2) — add/retire
                                    // preset packs, rotate seasonal festival packs, set each Saathi character's
                                    // default theme; does not expose any individual user's chosen theme, since
                                    // that data is private-per-viewer by design (doc 2 §2.7.1)
/admin/analytics                   // DAU/MAU, match rate, message volume, notification open rates, revenue
/admin/analytics/saathi            // Saathi-specific dashboard: session volume, proactive-message send rate
                                    // vs. cap (watch for the cap being hit constantly — a signal to revisit
                                    // the daily default), crisis-indicator flag count (aggregate only, never
                                    // individual transcript browsing from this view)
```

- Auth: role-gated (moderator/admin/founder tiers), backed by the Flask `/api/v1/admin/*` routes from document 4 — implement as a proper role check server-side on every admin API call, not just a hidden frontend route.
- Moderation queue UI: default-sort by severity (scam-flag high-risk and safety reports above routine content flags), one-click resolve actions (dismiss / warn user / suspend / escalate), and every action writes to the audit log described in document 4 §8.
- Analytics dashboard: use `recharts` for time-series (DAU/MAU, revenue) and simple stat cards for point-in-time numbers (active Circles, pending verifications). Pull from `/api/v1/admin/analytics/overview` — don't compute aggregates client-side from raw record dumps.
- The Saathi analytics view exists specifically to catch product/ethics drift early — e.g., if most users are hitting their daily proactive-message cap, that's a signal to review whether the cap or the messaging itself needs adjustment, not a metric to simply celebrate as "engagement."
- The personalization admin view is deliberately catalog-only (preset packs, seasonal rotation, Saathi defaults) — it must never surface what any individual user has chosen for their own chats, matching the privacy stance in document 2 §2.7.1.

### 3. Optional lightweight web app (build only if there's a real desktop-discovery use case)

If you decide Nepal's desktop-usage patterns justify it: a minimal `/app` section (login, matches inbox, chat) reusing the same Flask API as the mobile app. Do not attempt to replicate Jhalak reels, Saathi AI, or the Snap camera system on web in v1 — those are camera/mobile-native experiences; a partial, worse version of them on web would undermine the brand rather than extend it. Ship web as "check your matches and messages from a laptop," not as a parallel full product. If you do build the chat view, respect the same personalization system (doc 2 §2.7) rather than shipping a plain, unthemed web chat — but this is explicitly a stretch scope item, not required for a functional lightweight web app.

### 4. Shared component notes

- Import the same color/type tokens as the Flutter app (document 2 §2) into `tailwind.config.ts` as custom theme values (`marigold`, `dhaka`, `pine`, `paper`, `ink`) so a designer or developer moving between the two codebases sees the same vocabulary.
- Use `shadcn/ui` primitives for the admin dashboard (tables, dialogs, forms) — don't hand-roll data tables or pagination.
- SEO: proper metadata, Open Graph tags, and a Nepali-language sitemap entry for the marketing site — this is a real, low-cost acquisition channel given how thin the Nepali-language dating-app content landscape currently is.

This closes the seven-document set. Build order: document 4 (backend) and document 5 (AI layer) first since the app and web dashboard both depend on the API surface they define; document 3 (Flutter) and this document can proceed in parallel once that API contract is stable.
