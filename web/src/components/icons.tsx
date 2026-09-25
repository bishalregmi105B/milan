// Minimal stroke-based icons — 1.5px strokes, currentColor, no icon library.
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Icon({ size = 20, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

/** The Junction Mark — two paths meeting. Milan's signature. */
export function JunctionMark({ size = 24, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <path d="M3 12h6.5" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" />
      <path d="M20.5 12H14" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" />
      <circle cx="12" cy="12" r="4.25" stroke="currentColor" strokeWidth={2.5} />
    </svg>
  );
}

export const IconMenu = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Icon>
);

export const IconClose = (p: IconProps) => (
  <Icon {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Icon>
);

export const IconShield = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 3l7 3v5c0 4.6-3 8.4-7 10-4-1.6-7-5.4-7-10V6l7-3z" />
  </Icon>
);

export const IconUsers = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="9" cy="8" r="3.25" />
    <path d="M3.5 19c.7-2.9 2.9-4.5 5.5-4.5s4.8 1.6 5.5 4.5" />
    <path d="M15.5 5.4a3.25 3.25 0 010 5.2M17.5 14.9c1.6.7 2.7 2.1 3.2 4.1" />
  </Icon>
);

export const IconBadgeCheck = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 3l2.1 1.9 2.8-.3 1 2.7 2.5 1.4-.7 2.8.7 2.8-2.5 1.4-1 2.7-2.8-.3L12 21l-2.1-1.9-2.8.3-1-2.7-2.5-1.4.7-2.8-.7-2.8 2.5-1.4 1-2.7 2.8.3L12 3z" />
    <path d="M9.2 12.2l2 2 3.6-4" />
  </Icon>
);

export const IconCircles = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="9.5" cy="9.5" r="5.25" />
    <circle cx="14.5" cy="14.5" r="5.25" />
  </Icon>
);

export const IconPalette = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 3a9 9 0 100 18c1.5 0 2.3-.9 2.3-2 0-.6-.3-1.1-.6-1.5-.3-.4-.6-.9-.6-1.4 0-1.1.9-2 2-2H17a4 4 0 004-4c0-4-4-7.1-9-7.1z" />
    <circle cx="7.5" cy="11" r="0.9" fill="currentColor" stroke="none" />
    <circle cx="10" cy="7.3" r="0.9" fill="currentColor" stroke="none" />
    <circle cx="14.5" cy="7.3" r="0.9" fill="currentColor" stroke="none" />
  </Icon>
);

export const IconChart = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 20h16" />
    <path d="M6.5 16v-5M11 16V7M15.5 16v-7M20 16v-3" />
  </Icon>
);

export const IconHeartPulse = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 20s-7-4.3-7-9.5C5 7.5 7 5.5 9.5 5.5c1.4 0 2.1.6 2.5 1.2.4-.6 1.1-1.2 2.5-1.2C17 5.5 19 7.5 19 10.5c0 5.2-7 9.5-7 9.5z" />
    <path d="M7.5 12h2l1-1.8 1.6 3.4 1.2-1.6h3.2" />
  </Icon>
);

export const IconScroll = (p: IconProps) => (
  <Icon {...p}>
    <path d="M7 4h11a1.5 1.5 0 011.5 1.5V17" />
    <path d="M7 4a2 2 0 00-2 2v12.5A1.5 1.5 0 006.5 20H17a2 2 0 002-2v-1.5H8.5A1.5 1.5 0 017 15V4z" />
    <path d="M10 9h6M10 12.5h4" />
  </Icon>
);

export const IconLogout = (p: IconProps) => (
  <Icon {...p}>
    <path d="M14 4H7a2 2 0 00-2 2v12a2 2 0 002 2h7" />
    <path d="M17 8l4 4-4 4M21 12h-11" />
  </Icon>
);

export const IconChevronLeft = (p: IconProps) => (
  <Icon {...p}>
    <path d="M14.5 6l-6 6 6 6" />
  </Icon>
);

export const IconChevronRight = (p: IconProps) => (
  <Icon {...p}>
    <path d="M9.5 6l6 6-6 6" />
  </Icon>
);

export const IconAlert = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 4L2.8 19.5a1 1 0 00.9 1.5h16.6a1 1 0 00.9-1.5L12 4z" />
    <path d="M12 10v4.5" />
    <circle cx="12" cy="17.5" r="0.9" fill="currentColor" stroke="none" />
  </Icon>
);

export const IconCheckCircle = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M8.5 12.2l2.4 2.4 4.6-5" />
  </Icon>
);

export const IconXCircle = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M9.2 9.2l5.6 5.6M14.8 9.2l-5.6 5.6" />
  </Icon>
);

export const IconInfo = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 11v5" />
    <circle cx="12" cy="8" r="0.9" fill="currentColor" stroke="none" />
  </Icon>
);

export const IconInbox = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 13l2.4-7.1A1.5 1.5 0 017.8 5h8.4a1.5 1.5 0 011.4 0.9L20 13v4.5a1.5 1.5 0 01-1.5 1.5h-13A1.5 1.5 0 014 17.5V13z" />
    <path d="M4 13h4.5l1.2 2h4.6l1.2-2H20" />
  </Icon>
);

export const IconRefresh = (p: IconProps) => (
  <Icon {...p}>
    <path d="M20 11a8 8 0 10-2.3 6.3" />
    <path d="M20 5v6h-6" />
  </Icon>
);

export const IconCalendar = (p: IconProps) => (
  <Icon {...p}>
    <rect x="4" y="5.5" width="16" height="15" rx="2" />
    <path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
  </Icon>
);

export const IconPlus = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);

export const IconSearch = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M20 20l-4.2-4.2" />
  </Icon>
);

export const IconArrowRight = (p: IconProps) => (
  <Icon {...p}>
    <path d="M4 12h16M13 5l7 7-7 7" />
  </Icon>
);

export const IconExternal = (p: IconProps) => (
  <Icon {...p}>
    <path d="M14 5h5v5M19 5l-8 8" />
    <path d="M19 14v4a2 2 0 01-2 2H7a2 2 0 01-2-2V8a2 2 0 012-2h4" />
  </Icon>
);

export const IconSend = (p: IconProps) => (
  <Icon {...p}>
    <path d="M20.5 3.5L10 14M20.5 3.5L14 20.5l-4-6.5-6.5-4 17-6.5z" />
  </Icon>
);

export const IconWallet = (p: IconProps) => (
  <svg viewBox="0 0 24 24" width={p.size ?? 24} height={p.size ?? 24} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden {...p}>
    <path d="M3 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v1" />
    <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2H5a2 2 0 0 1-2-2Z" />
    <circle cx="16" cy="14" r="1.4" fill="currentColor" stroke="none" />
  </svg>
);
