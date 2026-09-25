import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Safety",
  description:
    "Verification, reporting, Share My Date, and scam-awareness education on Milan. Trust is the product.",
};

export default function SafetyPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-20">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-marigold-700">
        Safety & trust
      </p>
      <h1 className="text-4xl font-bold tracking-tight">Trust is the product</h1>
      <p className="mt-5 max-w-2xl leading-relaxed text-ink-500">
        Every profile passes a live-selfie check before it reaches anyone&apos;s
        deck. Moderation runs on every message thread by default — not only the
        reported ones.
      </p>

      <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2">
        {[
          {
            title: "Liveness verification",
            body: "A quick live selfie at signup verifies your photos are really you. The selfie itself is processed for verification and then discarded — never kept.",
          },
          {
            title: "Report & block in two taps",
            body: "From any profile, chat thread, or reel. Reports go to human moderation; blocking is immediate and mutual.",
          },
          {
            title: "Share My Date",
            body: "Send who, when, and where — plus live location if you choose — to a trusted contact before meeting up.",
          },
          {
            title: "Scam-pattern warnings",
            body: "Milan watches for romance-scam patterns — especially money requests and 'stuck abroad' stories — and warns recipients before harm is done.",
          },
        ].map((c) => (
          <div
            key={c.title}
            className="rounded-md border border-line200 bg-paper-50 p-7 shadow-raised"
          >
            <h3 className="mb-2 font-display text-lg font-semibold tracking-tight text-ink-900">
              {c.title}
            </h3>
            <p className="text-sm leading-relaxed text-ink-500">{c.body}</p>
          </div>
        ))}
      </div>

      <div className="mt-10 rounded-md border border-warning/40 bg-warning-100/60 p-7">
        <h3 className="font-display text-lg font-semibold tracking-tight text-warning">
          Never send money
        </h3>
        <p className="mt-2 text-sm leading-relaxed text-ink-600">
          No genuine connection will ask you to send money, gift cards, or bank
          details. If someone does, report them immediately — Milan will never
          ask for money inside chat either.
        </p>
      </div>
    </div>
  );
}
