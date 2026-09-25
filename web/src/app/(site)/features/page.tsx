import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Features",
  description:
    "AI-curated matching, Jhalak video discovery, Saathi AI conversation practice, and safety built in — everything inside Milan.",
};

const sections = [
  {
    title: "Discovery & matching",
    points: [
      "Conversational onboarding interview instead of filter forms",
      "AI-curated daily matches with a grounded 'why you matched' explainer",
      "Serious / Casual modes; opt-in Kundali Mode as a fun cultural signal",
    ],
  },
  {
    title: "Jhalak — video & social discovery",
    points: [
      "15–60s video intros as first-class profile citizens",
      "Vertical prompt-response reels; duet replies between matches",
      "24-hour 'aaja ko vibe' stories and interest-based Circles",
    ],
  },
  {
    title: "Saathi AI",
    points: [
      "A conversation-confidence companion to practice with — never a romantic substitute",
      "Curated personas, memory you can see and delete, voice mode",
      "Clearly labeled AI everywhere, 18+ only, Llama Guard moderated",
    ],
  },
  {
    title: "Safety & trust",
    points: [
      "Liveness verification and duplicate-face detection at signup",
      "Report/block within two taps of any profile, chat or reel",
      "Share My Date, scam-pattern warnings, in-app panic button",
    ],
  },
];

export default function FeaturesPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-20">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-marigold-700">
        Inside the app
      </p>
      <h1 className="mb-12 text-4xl font-bold tracking-tight">Everything inside Milan</h1>
      <div className="space-y-10">
        {sections.map((s) => (
          <section key={s.title}>
            <h2 className="mb-4 font-display text-xl font-semibold tracking-tight text-dhaka-500">
              {s.title}
            </h2>
            <ul className="space-y-2.5">
              {s.points.map((p) => (
                <li key={p} className="flex gap-3 text-sm leading-relaxed text-ink-600">
                  <span aria-hidden="true" className="mt-1 text-marigold-500">
                    ◆
                  </span>
                  {p}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
