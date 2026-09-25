"use client";

import { useRouter } from "next/navigation";
import { JunctionMark } from "@/components/icons";
import { APK_DOWNLOAD_URL, hasApkDownload } from "@/lib/download-config";

// Primary install path: the direct APK. Store badges stay honest
// "coming soon" placeholders.
function StoreBadge({ store }: { store: "App Store" | "Google Play" }) {
  return (
    <div
      aria-label={`${store} — coming soon`}
      className="flex min-h-16 w-full cursor-not-allowed select-none items-center justify-center gap-3 rounded-md border border-line300 bg-paper-100 px-8 py-4 text-ink-400 opacity-80 sm:w-56"
    >
      <div className="text-left">
        <p className="text-[11px] uppercase tracking-wider text-ink-400/70">{store}</p>
        <p className="font-display text-base font-semibold">Coming soon</p>
      </div>
    </div>
  );
}

function ApkBadge() {
  if (!hasApkDownload()) {
    return (
      <div
        aria-label="Android build coming soon"
        aria-disabled="true"
        className="flex min-h-16 w-full cursor-not-allowed select-none items-center justify-center gap-3 rounded-md border border-line300 bg-paper-100 px-8 py-4 text-ink-500 opacity-80 sm:w-72"
      >
        <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M17.6 9.48l1.84-3.18c.16-.31.04-.69-.26-.85-.29-.15-.65-.06-.83.22l-1.88 3.24a11.43 11.43 0 0 0-8.94 0L5.65 5.67c-.19-.29-.58-.38-.87-.2-.28.18-.37.54-.22.83L6.4 9.48A10.81 10.81 0 0 0 1 18h22a10.81 10.81 0 0 0-5.4-8.52M7 15.25a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5m10 0a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5" />
        </svg>
        <div className="text-left">
          <p className="text-[11px] uppercase tracking-wider text-ink-500/70">Android</p>
          <p className="font-display text-base font-semibold">Build coming soon</p>
        </div>
      </div>
    );
  }

  return (
    <a
      href={APK_DOWNLOAD_URL}
      download
      aria-label="Download Milan Android APK"
      className="flex min-h-16 w-full select-none items-center justify-center gap-3 rounded-md border border-line300 bg-ink-900 px-8 py-4 text-paper-0 shadow-[0_6px_24px_rgba(31,27,22,0.35)] transition-all hover:-translate-y-0.5 hover:bg-ink-800 sm:w-72"
    >
      <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M17.6 9.48l1.84-3.18c.16-.31.04-.69-.26-.85-.29-.15-.65-.06-.83.22l-1.88 3.24a11.43 11.43 0 0 0-8.94 0L5.65 5.67c-.19-.29-.58-.38-.87-.2-.28.18-.37.54-.22.83L6.4 9.48A10.81 10.81 0 0 0 1 18h22a10.81 10.81 0 0 0-5.4-8.52M7 15.25a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5m10 0a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5" />
      </svg>
      <div className="text-left">
        <p className="text-[11px] uppercase tracking-wider text-paper-0/60">Android</p>
        <p className="font-display text-base font-semibold">Download APK</p>
      </div>
    </a>
  );
}

export function DownloadClient({
  initialLocale,
  nav,
}: {
  initialLocale: "en" | "ne";
  nav: Record<"download", string>;
}) {
  const router = useRouter();

  function setLocale(locale: "en" | "ne") {
    document.cookie = `milan_lang=${locale}; path=/; max-age=31536000; samesite=lax`;
    router.refresh();
  }

  return (
    <div className="relative overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 65% 50% at 50% 0%, rgba(245,166,35,0.15), transparent 65%)",
        }}
      />
      <div className="relative mx-auto max-w-3xl px-6 py-24 text-center">
        <span className="mb-8 inline-block text-marigold-600">
          <JunctionMark size={52} />
        </span>

        {/* Language toggle — segmented control with aria-pressed */}
        <div
          role="group"
          aria-label="Language"
          className="mb-10 inline-flex rounded-full border border-line300 bg-paper-50 p-1"
        >
          {(["en", "ne"] as const).map((loc) => {
            const active = initialLocale === loc;
            return (
              <button
                key={loc}
                type="button"
                aria-pressed={active}
                onClick={() => setLocale(loc)}
                className={`min-h-9 rounded-full px-5 text-sm font-semibold transition-colors ${
                  active
                    ? "bg-marigold-500 text-ink-900"
                    : "text-ink-500 hover:text-ink-900"
                }`}
              >
                {loc === "en" ? "English" : "नेपाली"}
              </button>
            );
          })}
        </div>

        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          {nav.download} Milan
        </h1>
        <p className="mx-auto mt-5 max-w-md leading-relaxed text-ink-500">
          Free to download · 18+ · Nepali &amp; English
        </p>

        <div className="mt-12 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <ApkBadge />
          <StoreBadge store="App Store" />
        </div>

        <p className="mt-10 text-xs text-ink-400">
          Direct install: allow &ldquo;install from unknown sources&rdquo; when
          prompted. iOS app in review — this page will carry the store link the
          day it ships.
        </p>
      </div>
    </div>
  );
}
