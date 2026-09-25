import Link from "next/link";
import { JunctionMark } from "@/components/icons";

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center bg-paper-100 px-6 text-center">
      <span className="text-marigold-600">
        <JunctionMark size={56} />
      </span>
      <p className="mt-6 font-mono text-sm tabular-nums text-ink-400">404</p>
      <h1 className="mt-2 font-display text-3xl font-bold tracking-tight text-ink-900">
        These paths don&apos;t meet
      </h1>
      <p className="mt-3 max-w-sm text-sm leading-relaxed text-ink-500">
        The page you&apos;re looking for doesn&apos;t exist — it may have moved,
        or the address might be off by a letter.
      </p>
      <Link
        href="/"
        className="mt-8 inline-flex min-h-11 items-center rounded-sm bg-marigold-500 px-6 py-3 text-sm font-semibold text-ink-900 transition-colors hover:bg-marigold-600"
      >
        Back to Milan
      </Link>
    </div>
  );
}
