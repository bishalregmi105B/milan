import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Priced for Nepal — local pricing in NPR with eSewa, Khalti, Fonepay, and ConnectIPS. Basic, Plus, and Premium tiers.",
};

const tiers = [
  {
    name: "Basic",
    price: "NPR 299",
    period: "/month",
    features: [
      "See who liked you",
      "5 daily superlikes",
      "Rewind last swipe",
      "Ad-free browsing",
    ],
    highlight: false,
  },
  {
    name: "Plus",
    price: "NPR 699",
    period: "/month",
    features: [
      "Everything in Basic",
      "Unlimited likes & rewinds",
      "Boost every month",
      "Incognito mode",
    ],
    highlight: true,
  },
  {
    name: "Premium",
    price: "NPR 1,299",
    period: "/month",
    features: [
      "Everything in Plus",
      "Saathi AI extended voice sessions",
      "Priority in discovery queue",
      "Early access to new features",
    ],
    highlight: false,
  },
];

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-20">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-marigold-700">
        Pricing
      </p>
      <h1 className="text-4xl font-bold tracking-tight">Priced for Nepal</h1>
      <p className="mt-4 max-w-xl text-ink-500">
        Local pricing, local payments — eSewa, Khalti, Fonepay, and ConnectIPS.
      </p>

      <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-3">
        {tiers.map((t) => (
          <div
            key={t.name}
            className={`flex flex-col rounded-md p-8 ${
              t.highlight
                ? "border border-dhaka-600 bg-dhaka-500 text-paper-0 shadow-floating"
                : "border border-line200 bg-paper-50 text-ink-600 shadow-raised"
            }`}
          >
            <div className="flex items-center justify-between">
              <h3 className="font-display text-lg font-bold tracking-tight">{t.name}</h3>
              {t.highlight && (
                <span className="rounded-full bg-marigold-500 px-2.5 py-0.5 text-[11px] font-semibold text-ink-900">
                  Popular
                </span>
              )}
            </div>
            <p className="mb-7 mt-4">
              <span className="font-display text-3xl font-bold tabular-nums tracking-tight">
                {t.price}
              </span>
              <span className={`text-sm ${t.highlight ? "text-paper-0/75" : "text-ink-400"}`}>
                {t.period}
              </span>
            </p>
            <ul className="flex-1 space-y-2.5 text-sm">
              {t.features.map((f) => (
                <li key={f} className="flex gap-2.5">
                  <span
                    aria-hidden="true"
                    className={t.highlight ? "text-marigold-500" : "text-pine-500"}
                  >
                    ✓
                  </span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
