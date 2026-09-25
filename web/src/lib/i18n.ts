// Shared bilingual dictionary (doc 6 §1) — same string source shape as the
// Flutter ARBs where practical. Locale resolved from cookie `milan_lang`.
export const dictionaries = {
  en: {
    nav: {
      features: "Features",
      safety: "Safety",
      saathi: "Saathi AI",
      pricing: "Pricing",
      download: "Download",
    },
    home: {
      tagline: "Where two paths meet.",
      subtagline:
        "Milan is the dating and connection app built for Nepal — AI-curated matches, video-first profiles, liveness verification, and Saathi, an AI companion to practice with.",
      ctaPrimary: "Download Milan",
      ctaSecondary: "How it works",
    },
    footer: { privacy: "Privacy", terms: "Terms" },
  },
  ne: {
    nav: {
      features: "फिचरहरू",
      safety: "सुरक्षा",
      saathi: "साथी एआई",
      pricing: "मूल्य",
      download: "डाउनलोड",
    },
    home: {
      tagline: "जहाँ दुई बाटो भेट्छन्।",
      subtagline:
        "मिलन नेपालका लागि बनेको डेटिङ र सम्बन्ध जोड्ने एप हो — एआई-आधारित मिलान, भिडियो प्रोफाइल, लाइभनेस प्रमाणीकरण, र अभ्यास गर्न मिल्ने साथी।",
      ctaPrimary: "मिलन डाउनलोड",
      ctaSecondary: "कसरी काम गर्छ",
    },
    footer: { privacy: "गोपनीयता", terms: "सर्तहरू" },
  },
} as const;

export type Locale = keyof typeof dictionaries;

export function getDictionary(locale?: string | null) {
  return dictionaries[(locale === "ne" ? "ne" : "en") as Locale];
}
