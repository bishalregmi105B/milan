// The Milan mark — two overlapping rings (two people, two paths) meeting
// beneath a marigold dot (the chautari gathering tree in miniature, and the
// Dashain garland in one bead). Extends the Junction Mark idea into a
// ownable, rounded identity tile.
//
// Pure SVG + text — no hooks — so it renders identically in server and
// client components ("client-safe" by construction).

type MilanLogoProps = {
  /** Edge length of the square mark in px. */
  size?: number;
  /** Render the "Milan" wordmark beside the mark. */
  wordmark?: boolean;
  className?: string;
};

export function MilanLogo({ size = 30, wordmark = false, className = "" }: MilanLogoProps) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        fill="none"
        role="img"
        aria-label="Milan logo"
        className="shrink-0"
      >
        {/* Ink tile */}
        <rect width="64" height="64" rx="16" fill="#0B1520" />
        {/* Two paths / two people — overlapping rings */}
        <circle cx="25.5" cy="37.5" r="11.5" stroke="#FFFBF5" strokeWidth="5" />
        <circle cx="38.5" cy="37.5" r="11.5" stroke="#FFFBF5" strokeWidth="5" />
        {/* The marigold — the moment they meet, under the gathering tree */}
        <circle cx="32" cy="17" r="5.5" fill="#F5A623" />
      </svg>
      {wordmark && (
        <span className="font-display text-xl font-bold tracking-tight text-night-900">
          Milan
        </span>
      )}
    </span>
  );
}
