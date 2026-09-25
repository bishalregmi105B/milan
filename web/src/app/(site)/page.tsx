import type { Metadata } from "next";
import Link from "next/link";
import {
  IconAlert,
  IconArrowRight,
  IconBadgeCheck,
  IconInfo,
  IconShield,
} from "@/components/icons";
import { HeroScene } from "@/components/hero-scene";
import { Reveal } from "@/components/reveal";
import { CountUp } from "@/components/count-up";
import { APK_DOWNLOAD_URL } from "@/lib/download-config";

export const metadata: Metadata = {
  title: { absolute: "Milan — भेट हुने ठाउँ · Where two paths meet" },
  description:
    "The romantic, verified Nepali dating app — liveness-checked real profiles, matchmaking that learns what you actually like, Messenger-smooth chat, and Saathi AI companions who are always honestly AI. Built for Nepal.",
};

function AndroidDownloadCta({ className }: { className: string }) {
  const content = (
    <>
      Download the app
      <IconArrowRight size={18} />
    </>
  );

  if (!APK_DOWNLOAD_URL) {
    return (
      <span
        aria-disabled="true"
        className={`${className} cursor-not-allowed opacity-70`}
      >
        Android build coming soon
        <IconArrowRight size={18} />
      </span>
    );
  }

  return (
    <a href={APK_DOWNLOAD_URL} download className={className}>
      {content}
    </a>
  );
}

/* ── Hero copy (rendered inside the 3D HeroScene stage) ───────────────── */

function HeroCopy() {
  return (
    <>
      <p className="animate-fade-up mb-5 text-xs font-semibold uppercase tracking-[0.18em] text-marigold-700">
        नेपालको आफ्नै डेटिङ एप · Made in Nepal · 18+
      </p>
      <h1 className="animate-fade-up-1 text-4xl font-bold leading-[1.08] tracking-tight text-night-900 sm:text-6xl">
        भेट हुने ठाउँ,{" "}
        <span className="bg-gradient-to-r from-marigold-600 via-dhaka-500 to-dhaka-600 bg-clip-text text-transparent">
          मिलन।
        </span>
        <span className="mt-3 block text-2xl font-semibold tracking-tight text-night-500 sm:text-3xl">
          Where two paths meet.
        </span>
      </h1>
      <p className="animate-fade-up-2 mx-auto mt-6 max-w-xl text-base leading-relaxed text-night-500 lg:mx-0">
        Real, liveness-verified Nepali people. Matchmaking that learns what you
        actually like. Chats that feel like the app you already love. Milan is
        dating built for Nepal — सुरक्षित, इमानदार, र तपाईंकै लागि।
      </p>
      <div className="animate-fade-up-3 mt-9 flex flex-col items-center gap-3.5 sm:flex-row lg:justify-start sm:justify-center">
        <AndroidDownloadCta className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-full bg-action-500 px-8 py-3.5 font-semibold text-white shadow-[0_10px_30px_rgba(11,132,254,0.35)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-action-600 hover:shadow-[0_14px_36px_rgba(11,132,254,0.42)] sm:w-auto" />
        <a
          href="#companions"
          className="inline-flex min-h-12 w-full items-center justify-center rounded-full border border-night-900/15 bg-white/70 px-8 py-3.5 font-semibold text-night-900 backdrop-blur transition-all duration-200 hover:-translate-y-0.5 hover:border-night-900/30 hover:bg-white sm:w-auto"
        >
          Meet the companions
        </a>
      </div>
      <div className="animate-fade-up-3 mt-6 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs font-medium text-night-400 lg:justify-start">
        <span className="inline-flex items-center gap-1.5">
          <IconBadgeCheck size={14} className="text-pine-600" />
          Liveness-verified profiles
        </span>
        <span className="inline-flex items-center gap-1.5">
          <IconShield size={14} className="text-dhaka-500" />
          18+ only
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden="true" className="h-2 w-2 rounded-full bg-marigold-500" />
          Made in Nepal
        </span>
      </div>
      <p className="animate-fade-up-3 mt-3 text-xs text-night-300">
        {APK_DOWNLOAD_URL
          ? 'Free on Android · APK direct install · iOS coming soon'
          : 'Android build coming soon · iOS coming soon'}
      </p>
    </>
  );
}

/* ── Marquee divider — the little things Milan is made of ─────────────── */

const MARQUEE_WORDS = [
  "माया",
  "momo dates",
  "चौतारी",
  "Dashain lights",
  "monsoon walks",
  "tika & jamara",
  "साथी",
  "KTM evenings",
  "भेटघाट",
  "पहाडको सूर्योदय",
];

function MarqueeDivider() {
  return (
    <div
      aria-hidden="true"
      className="marquee relative overflow-hidden border-y border-line200 bg-white py-4"
    >
      <div className="marquee-track flex w-max">
        {[0, 1].map((copy) => (
          <div key={copy} className="flex shrink-0 items-center">
            {MARQUEE_WORDS.map((word) => (
              <span
                key={`${copy}-${word}`}
                className="flex items-center font-display text-sm font-semibold tracking-wide text-night-400"
              >
                <span className="px-7">{word}</span>
                <span className="text-[9px] text-marigold-500">◆</span>
              </span>
            ))}
          </div>
        ))}
      </div>
      {/* Edge fade */}
      <div className="pointer-events-none absolute inset-y-0 left-0 w-16 bg-gradient-to-r from-white to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 w-16 bg-gradient-to-l from-white to-transparent" />
    </div>
  );
}

/* ── Feature trio ─────────────────────────────────────────────────────── */

const FEATURES = [
  {
    title: "Verified with selfie liveness",
    body: "Every profile clears a LivenessCheck — a real human, live on camera, not a borrowed photo. Look for the tick before you say hi.",
    visual: (
      <div className="flex h-20 items-center gap-3">
        <span className="relative grid h-14 w-14 place-items-center rounded-full bg-pine-100 text-pine-600">
          <IconBadgeCheck size={26} />
          <span aria-hidden="true" className="presence-dot absolute inset-0 rounded-full" />
        </span>
        <span className="rounded-full bg-pine-100 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-pine-700">
          Live · human · unique
        </span>
      </div>
    ),
  },
  {
    title: "Matchmaking that learns you",
    body: "Milan listens to how you actually talk — topics, humour, tempo — then curates a few people worth meeting, each with a grounded “why you matched”.",
    visual: (
      <div className="flex h-20 items-center gap-3">
        <span
          className="relative grid h-14 w-14 shrink-0 place-items-center rounded-full"
          style={{ background: "conic-gradient(#0B84FE 0% 94%, #E8E1D3 94% 100%)" }}
        >
          <span className="grid h-11 w-11 place-items-center rounded-full bg-white text-[11px] font-bold text-night-900">
            94%
          </span>
        </span>
        <span className="text-[11px] font-bold uppercase tracking-wider text-action-700">
          why you matched
        </span>
      </div>
    ),
  },
  {
    title: "Chat that feels like home",
    body: "Typing dots, read receipts, voice notes — messaging as smooth as the chat app you already use, so nothing gets lost between match and माया।",
    visual: (
      <div className="flex h-20 flex-col justify-center gap-1.5">
        <span className="w-fit rounded-2xl rounded-bl-md bg-paper-100 px-3 py-1.5 text-[11px] text-night-900">
          तिमी कस्तो छौँ?
        </span>
        <span className="ml-auto flex w-fit items-center gap-1 rounded-2xl rounded-br-md bg-action-500 px-3.5 py-2">
          <span aria-hidden="true" className="typing-dot inline-block h-1 w-1 rounded-full bg-white/90" />
          <span aria-hidden="true" className="typing-dot inline-block h-1 w-1 rounded-full bg-white/90" style={{ animationDelay: "0.16s" }} />
          <span aria-hidden="true" className="typing-dot inline-block h-1 w-1 rounded-full bg-white/90" style={{ animationDelay: "0.32s" }} />
        </span>
      </div>
    ),
  },
] as const;

function FeatureTrio() {
  return (
    <section id="features" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20 sm:py-24">
      <Reveal className="mx-auto max-w-2xl text-center">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-marigold-700">
          साँचो मान्छे, साँचो सम्बन्ध
        </p>
        <h2 className="text-3xl font-bold tracking-tight text-night-900 sm:text-4xl">
          Real connections, real people
        </h2>
        <p className="mt-4 leading-relaxed text-night-500">
          No endless swiping, no fake profiles, no games. Milan is built around
          three honest promises.
        </p>
      </Reveal>

      <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-3">
        {FEATURES.map((feature, i) => (
          <Reveal key={feature.title} delay={i * 90} className="h-full">
            <article className="group h-full rounded-lg border border-line200 bg-white p-7 shadow-raised transition-all duration-300 hover:-translate-y-1.5 hover:border-line300 hover:shadow-floating">
              {feature.visual}
              <span aria-hidden="true" className="mb-3 mt-5 block h-[3px] w-9 rounded-full bg-marigold-500 transition-all duration-300 group-hover:w-14" />
              <h3 className="mb-2 font-display text-lg font-semibold tracking-tight text-night-900">
                {feature.title}
              </h3>
              <p className="text-sm leading-relaxed text-night-500">{feature.body}</p>
            </article>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ── Animated counters ────────────────────────────────────────────────── */

const STATS = [
  { to: 4, suffix: "", label: "Saathi companions with real lives" },
  { to: 100, suffix: "%", label: "profiles liveness-verified" },
  { to: 2, suffix: "", label: "taps to report or block anyone" },
  { to: 1, suffix: "", label: "country we build for — Nepal" },
] as const;

function StatBand() {
  return (
    <section className="border-y border-line200 bg-paper-50/70">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-x-6 gap-y-10 px-6 py-14 lg:grid-cols-4">
        {STATS.map((stat, i) => (
          <Reveal key={stat.label} delay={i * 80} className="text-center">
            <p className="font-display text-4xl font-bold tracking-tight text-night-900 sm:text-5xl">
              <CountUp to={stat.to} suffix={stat.suffix} />
            </p>
            <p className="mx-auto mt-2 max-w-[16ch] text-sm leading-snug text-night-400">
              {stat.label}
            </p>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

/* ── Saathi companions ────────────────────────────────────────────────── */

const COMPANIONS = [
  {
    name: "Asha",
    role: "Warm & curious",
    life: "In the library till 4, then chai at the corner tapri.",
    presence: "Online now",
    avatarClass: "bg-marigold-100 text-marigold-700",
    dot: "bg-pine-500",
  },
  {
    name: "Bibek",
    role: "Quick wit & banter",
    life: "Deep in a football debate you'll get pulled into.",
    presence: "Online now",
    avatarClass: "bg-dhaka-100 text-dhaka-700",
    dot: "bg-pine-500",
  },
  {
    name: "Priya",
    role: "Calm & patient",
    life: "Sketching by the window before evening class.",
    presence: "Free after 6",
    avatarClass: "bg-pine-100 text-pine-700",
    dot: "bg-marigold-500",
  },
  {
    name: "Sagar",
    role: "Direct & honest",
    life: "At the gym, then dinner with the family.",
    presence: "Texting soon",
    avatarClass: "bg-action-100 text-action-700",
    dot: "bg-marigold-500",
  },
] as const;

function CompanionsSection() {
  return (
    <section id="companions" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20 sm:py-24">
      <Reveal className="mx-auto max-w-2xl text-center">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-dhaka-500">
          साथी · clearly-labeled AI companions
        </p>
        <h2 className="text-3xl font-bold tracking-tight text-night-900 sm:text-4xl">
          Companions with lives of their own
        </h2>
        <p className="mt-4 leading-relaxed text-night-500">
          Four Saathi companions text first, remember your week, and cheer for
          your real dates. A taste of the future — always clearly AI, never
          pretending to be human, and only for verified adults.
        </p>
      </Reveal>

      <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {COMPANIONS.map((companion, i) => (
          <Reveal key={companion.name} delay={i * 80} className="h-full">
            <article className="group relative h-full rounded-lg border border-line200 bg-white p-6 shadow-raised transition-all duration-300 hover:-translate-y-1.5 hover:shadow-floating">
              <span className="absolute right-4 top-4 rounded-full bg-dhaka-100 px-2 py-0.5 text-[9.5px] font-bold uppercase tracking-wide text-dhaka-700">
                AI
              </span>
              <span className={`relative grid h-14 w-14 place-items-center rounded-full font-display text-xl font-bold ${companion.avatarClass}`}>
                {companion.name[0]}
                <span
                  aria-hidden="true"
                  className={`presence-dot absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full border-2 border-white ${companion.dot}`}
                />
              </span>
              <h3 className="mt-4 font-display text-lg font-semibold tracking-tight text-night-900">
                {companion.name}
              </h3>
              <p className="text-xs font-semibold uppercase tracking-wider text-night-400">
                {companion.role}
              </p>
              <p className="mt-3 border-l-2 border-marigold-200 pl-3 text-sm italic leading-relaxed text-night-500">
                “{companion.life}”
              </p>
              <p className="mt-4 flex items-center gap-1.5 text-xs font-medium text-night-400">
                <span aria-hidden="true" className={`h-1.5 w-1.5 rounded-full ${companion.dot}`} />
                {companion.presence}
              </p>
            </article>
          </Reveal>
        ))}
      </div>

      <Reveal delay={120} className="mt-8 text-center">
        <p className="mx-auto max-w-2xl text-sm leading-relaxed text-night-400">
          Presence rhythms, memories you can inspect and delete, quiet hours
          respected — bounded by design.
        </p>
        <Link
          href="/saathi"
          className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold text-dhaka-500 underline-offset-4 transition-colors hover:text-dhaka-700 hover:underline"
        >
          See how companions are built
          <IconArrowRight size={15} />
        </Link>
      </Reveal>
    </section>
  );
}

/* ── Safety — dark band ───────────────────────────────────────────────── */

const SAFETY_ITEMS = [
  {
    icon: IconShield,
    title: "18+ gate",
    body: "Age-verified adults only — nobody under 18 gets past the door.",
  },
  {
    icon: IconBadgeCheck,
    title: "LivenessCheck",
    body: "A quick selfie video proves every profile is a real, live, one-of-a-kind human.",
  },
  {
    icon: IconAlert,
    title: "Two-tap report & block",
    body: "Within reach of every profile, chat and reel — reviewed quickly by real people.",
  },
  {
    icon: IconInfo,
    title: "AI, always disclosed",
    body: "Companions are labeled AI in every chat; AI content never masquerades as human.",
  },
] as const;

function SafetySection() {
  return (
    <section id="safety" className="relative scroll-mt-24 overflow-hidden bg-night-900">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 45% 40% at 12% 0%, rgba(245,166,35,0.16), transparent 70%), radial-gradient(ellipse 50% 45% at 92% 100%, rgba(123,30,58,0.35), transparent 70%)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 opacity-[0.05]"
        style={{
          backgroundImage: "radial-gradient(#fffbf5 1px, transparent 1.2px)",
          backgroundSize: "22px 22px",
        }}
      />
      <div className="relative mx-auto max-w-6xl px-6 py-20 sm:py-24">
        <Reveal className="max-w-2xl">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-marigold-300">
            सुरक्षा पहिले
          </p>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Safety, stitched in — not bolted on.
          </h2>
          <p className="mt-4 leading-relaxed text-night-300">
            Milan is 18+, verified and moderated. Every safeguard below ships on
            day one, because माया only grows where people feel safe.
          </p>
        </Reveal>

        <div className="mt-12 grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {SAFETY_ITEMS.map((item, i) => (
            <Reveal key={item.title} delay={i * 80}>
              <span className="grid h-11 w-11 place-items-center rounded-full border border-marigold-500/30 bg-marigold-500/10 text-marigold-400">
                <item.icon size={20} />
              </span>
              <h3 className="mt-4 font-display text-base font-semibold tracking-tight text-white">
                {item.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-night-300">{item.body}</p>
            </Reveal>
          ))}
        </div>

        <Reveal delay={120}>
          <Link
            href="/safety"
            className="mt-12 inline-flex items-center gap-1.5 text-sm font-semibold text-marigold-300 underline-offset-4 transition-colors hover:text-marigold-200 hover:underline"
          >
            Read the full safety promise
            <IconArrowRight size={15} />
          </Link>
        </Reveal>
      </div>
    </section>
  );
}

/* ── Marigold CTA band ────────────────────────────────────────────────── */

const GARLAND_COLORS = ["#E0920F", "#F5A623", "#7B1E3A", "#FBD9A0"];
const GARLAND_DROPS = [0, 6, 2, 8, 3, 5];

function CtaBand() {
  return (
    <section id="download" className="relative scroll-mt-24 overflow-hidden bg-marigold-500">
      {/* Dashain garland along the top edge */}
      <div aria-hidden="true" className="flex justify-between px-3 pt-2">
        {Array.from({ length: 52 }).map((_, i) => (
          <span
            key={i}
            className="h-2.5 w-2.5 shrink-0 rounded-full"
            style={{
              background: GARLAND_COLORS[i % GARLAND_COLORS.length],
              marginTop: GARLAND_DROPS[i % GARLAND_DROPS.length],
            }}
          />
        ))}
      </div>

      {/* Oversized watermark mark */}
      <div aria-hidden="true" className="pointer-events-none absolute -right-16 bottom-[-70px] opacity-[0.12]">
        <svg width="280" height="280" viewBox="0 0 64 64" fill="none">
          <circle cx="25.5" cy="37.5" r="11.5" stroke="#0B1520" strokeWidth="5" />
          <circle cx="38.5" cy="37.5" r="11.5" stroke="#0B1520" strokeWidth="5" />
          <circle cx="32" cy="17" r="5.5" fill="#0B1520" />
        </svg>
      </div>

      <div className="relative mx-auto max-w-3xl px-6 py-20 text-center sm:py-24">
        <Reveal>
          <h2 className="text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
            तपाईंको मान्छे मिलनमै हुन सक्छ।
            <span className="mt-2 block text-xl font-semibold text-ink-700 sm:text-2xl">
              Your person might already be here.
            </span>
          </h2>
          <p className="mx-auto mt-5 max-w-xl leading-relaxed text-ink-700">
            Free to download. A few minutes to verify. A whole festival season
            of hellos waiting on the other side.
          </p>
          <div className="mt-9 flex justify-center">
            <AndroidDownloadCta className="inline-flex min-h-13 items-center justify-center gap-2 rounded-full bg-night-900 px-9 py-4 font-semibold text-paper-0 shadow-[0_12px_32px_rgba(11,21,32,0.35)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-night-700 hover:shadow-[0_16px_40px_rgba(11,21,32,0.4)]" />
          </div>
          <p className="mt-4 text-xs font-medium text-ink-700/80">
            {APK_DOWNLOAD_URL
              ? 'Free · Android APK · iOS coming soon · 18+'
              : 'Android build coming soon · iOS coming soon · 18+'}
          </p>
        </Reveal>
      </div>
    </section>
  );
}

/* ── Page ─────────────────────────────────────────────────────────────── */

export default function HomePage() {
  return (
    <div>
      <HeroScene>
        <HeroCopy />
      </HeroScene>

      <MarqueeDivider />
      <FeatureTrio />
      <StatBand />
      <CompanionsSection />
      <SafetySection />
      <CtaBand />
    </div>
  );
}
