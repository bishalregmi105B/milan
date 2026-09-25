import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Milan Companions",
  description:
    "Milan's AI companions practice conversations with you, remember your week, and text you first — always clearly an AI, always bridging you to real love. 18+.",
};

// This page is genuine trust documentation for app-store review (doc 6 §1).
export default function SaathiPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-20">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-dhaka-500">
        Clearly labeled AI · 18+ · Moderated
      </p>
      <h1 className="max-w-2xl text-4xl font-bold tracking-tight">
        Honest AI, real connection
      </h1>
      <p className="mt-6 max-w-2xl leading-relaxed text-ink-500">
        Milan&apos;s companions (Saathi, साथी — &quot;companion&quot;) do two jobs:
        they help you build dating confidence by practicing conversations, and
        between matches they keep you company — texting first, remembering
        your week, celebrating your wins. They are always clearly an AI, never
        a real person, and they are built to hand you back to real people,
        not replace them. Romance stays warm and verbal — never explicit —
        and only for verified adults on paid passes.
      </p>

      <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2">
        {[
          ["What companions ARE", "AI practice partners and companionship between matches: openers, banter, date debriefs, good-morning texts, memory that spans months — with warm (never sexual) romance for verified adults."],
          ["What companions ARE NOT", "Not humans and never pretend to be. No explicit content, ever. No claims of exclusivity, no guilt trips, no jealousy games — and they celebrate when you thrive with real people."],
          ["A persona shaped by you", "Nothing about how your companion acts is preset. Paste any past chat history to teach it a vibe, or just talk — it keeps learning how you text, the topics you love, the inside jokes you share."],
          ["Texts that feel real", "Presence rhythms, read-and-typing delays, message bursts, statuses, a diary, duo quests, sealed capsules and a yearly recap — all AI-labeled, never a real-photo imitation."],
          ["Your memory, your control", "You can see, edit, pin and delete everything your companion remembers — item by item, or all of it at once. Style learning from your other chats is one switch."],
          ["Bounded by design", "Proactive texts are opt-in, capped by your pass tier, respect quiet hours (11pm–7am), and route through the same limits as every other notification."],
        ].map(([title, body]) => (
          <div
            key={title}
            className="rounded-md border border-line200 bg-paper-50 p-7 shadow-raised"
          >
            <h3 className="mb-2 font-display text-lg font-semibold tracking-tight text-ink-900">
              {title}
            </h3>
            <p className="text-sm leading-relaxed text-ink-500">{body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
