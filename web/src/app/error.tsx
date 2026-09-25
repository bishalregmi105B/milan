"use client";

import { JunctionMark } from "@/components/icons";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-paper-100 px-6 text-center">
      <span className="text-marigold-600">
        <JunctionMark size={56} />
      </span>
      <h1 className="mt-6 font-display text-3xl font-bold tracking-tight text-ink-900">
        Something broke on our side
      </h1>
      <p className="mt-3 max-w-sm text-sm leading-relaxed text-ink-500">
        An unexpected error interrupted this page. Trying again usually fixes
        it — if it keeps happening, the team can look up this reference:
      </p>
      {error.digest && (
        <p className="mt-3 font-mono text-xs tabular-nums text-ink-400">
          ref {error.digest}
        </p>
      )}
      <button
        type="button"
        onClick={reset}
        className="mt-8 inline-flex min-h-11 items-center rounded-sm bg-marigold-500 px-6 py-3 text-sm font-semibold text-ink-900 transition-colors hover:bg-marigold-600"
      >
        Try again
      </button>
    </div>
  );
}
