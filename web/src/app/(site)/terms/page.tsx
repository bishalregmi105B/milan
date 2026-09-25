import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "Age requirement, community rules, Saathi AI terms, and subscription terms for Milan.",
};

export default function TermsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-marigold-700">
        Legal
      </p>
      <h1 className="mb-10 text-4xl font-bold tracking-tight">Terms of Service</h1>
      <div className="space-y-8 text-sm leading-relaxed text-ink-600">
        <section className="rounded-md border border-line200 bg-paper-50 p-6 shadow-raised">
          <h2 className="font-display text-base font-semibold text-ink-900">
            1. Age requirement
          </h2>
          <p className="mt-2">
            Milan is strictly 18+. AI companion features (Saathi) require
            verified age confirmation. Accounts found to be underage are
            suspended.
          </p>
        </section>
        <section className="rounded-md border border-line200 bg-paper-50 p-6 shadow-raised">
          <h2 className="font-display text-base font-semibold text-ink-900">
            2. Community rules
          </h2>
          <p className="mt-2">
            Harassment, hate speech, threats, sexual content involving minors or
            ambiguous ages, and financial exploitation result in immediate
            moderation action. Every message thread is moderated by default.
          </p>
        </section>
        <section className="rounded-md border border-line200 bg-paper-50 p-6 shadow-raised">
          <h2 className="font-display text-base font-semibold text-ink-900">3. Saathi AI</h2>
          <p className="mt-2">
            Saathi is an AI practice companion, not a human. It is never a
            romantic or sexual service. Do not treat its output as medical,
            legal, or crisis counseling.
          </p>
        </section>
        <section className="rounded-md border border-line200 bg-paper-50 p-6 shadow-raised">
          <h2 className="font-display text-base font-semibold text-ink-900">
            4. Subscriptions
          </h2>
          <p className="mt-2">
            Premium tiers renew monthly in NPR until cancelled. Payments are
            processed by eSewa, Khalti, Fonepay, or ConnectIPS; Milan stores only
            provider transaction references.
          </p>
        </section>
      </div>
    </div>
  );
}
