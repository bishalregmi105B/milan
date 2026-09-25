import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy",
  description:
    "How Milan handles biometric data, chats and themes, Saathi memory, and ephemeral snaps.",
};

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-marigold-700">
        Privacy
      </p>
      <h1 className="mb-10 text-4xl font-bold tracking-tight">Privacy at Milan</h1>
      <div className="space-y-8 text-sm leading-relaxed text-ink-600">
        <section className="rounded-md border border-line200 bg-paper-50 p-6 shadow-raised">
          <h2 className="font-display text-base font-semibold text-ink-900">Biometric data</h2>
          <p className="mt-2">
            Your liveness selfie is processed to verify your profile and then
            discarded. Only a pass/fail result and a duplicate-detection
            embedding are retained — never the image itself.
          </p>
        </section>
        <section className="rounded-md border border-line200 bg-paper-50 p-6 shadow-raised">
          <h2 className="font-display text-base font-semibold text-ink-900">
            Your chats &amp; themes
          </h2>
          <p className="mt-2">
            Chat themes, wallpapers, and bubble colors are private per viewer —
            the person you&apos;re chatting with never sees your choices.
            Custom wallpaper uploads are moderated like all user media but never
            shown to anyone else.
          </p>
        </section>
        <section className="rounded-md border border-line200 bg-paper-50 p-6 shadow-raised">
          <h2 className="font-display text-base font-semibold text-ink-900">Saathi AI</h2>
          <p className="mt-2">
            Everything Saathi remembers about you is visible on the
            &quot;What Saathi Remembers&quot; screen and individually deletable.
            Deleting an item removes it from what feeds future conversations.
          </p>
        </section>
        <section className="rounded-md border border-line200 bg-paper-50 p-6 shadow-raised">
          <h2 className="font-display text-base font-semibold text-ink-900">Ephemeral snaps</h2>
          <p className="mt-2">
            Disappearing snaps are purged from our servers on expiry — not just
            hidden. If a recipient screenshots one, you&apos;ll be notified.
          </p>
        </section>
      </div>
    </div>
  );
}
