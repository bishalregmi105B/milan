import type { Metadata, Viewport } from "next";
import { Sora, Manrope, Noto_Sans_Devanagari } from "next/font/google";
import { cookies } from "next/headers";
import { getDictionary } from "@/lib/i18n";
import "./globals.css";

const sora = Sora({
  subsets: ["latin"],
  variable: "--font-sora",
  display: "swap",
});

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
  display: "swap",
});

// Devanagari fallback so नेपाली copy renders with the same weight and
// discipline as the Latin wordmark.
const notoDeva = Noto_Sans_Devanagari({
  subsets: ["devanagari", "latin"],
  variable: "--font-deva",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Milan — Where two paths meet",
    template: "%s — Milan",
  },
  description:
    "AI-curated matches, video-first profiles, liveness verification, and Saathi AI conversation practice. Built for Nepal.",
  openGraph: {
    title: "Milan — Where two paths meet",
    description: "The dating app built for Nepal.",
    locale: "en_NP",
    alternateLocale: "ne_NP",
    siteName: "Milan",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#fffbf5",
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const jar = await cookies();
  const locale = jar.get("milan_lang")?.value === "ne" ? "ne" : "en";
  getDictionary(locale); // warm the dictionary — lang must match visible copy

  return (
    <html lang={locale} className={`${sora.variable} ${manrope.variable} ${notoDeva.variable}`}>
      <body>
        {/* Marks JS availability before first paint — scroll-reveal styles in
            globals.css only hide content when this class is present. */}
        <script
          dangerouslySetInnerHTML={{
            __html: "document.documentElement.classList.add('js');",
          }}
        />
        {children}
      </body>
    </html>
  );
}
