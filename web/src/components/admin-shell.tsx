"use client";

// Admin shell — dark ink sidebar with marigold active indicator, mobile
// slide-over, logout, and identity decoded from the session JWT's role claim.
// Sidebar text stays ≥4.5:1 against ink-900 (white at 65–95% opacity).

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { clearSession, getAdminToken } from "@/lib/admin-api";
import { ToastProvider } from "./toast";
import {
  IconBadgeCheck,
  IconChart,
  IconCircles,
  IconClose,
  IconHeartPulse,
  IconWallet,
  IconLogout,
  IconMenu,
  IconPalette,
  IconScroll,
  IconShield,
  IconUsers,
  JunctionMark,
} from "./icons";

const NAV = [
  { href: "/admin/moderation", label: "Moderation", icon: IconShield },
  { href: "/admin/users", label: "Users", icon: IconUsers },
  { href: "/admin/payments", label: "Payments", icon: IconWallet },
  { href: "/admin/verification-queue", label: "Verification", icon: IconBadgeCheck },
  { href: "/admin/circles", label: "Circles", icon: IconCircles },
  { href: "/admin/personalization", label: "Theme Catalog", icon: IconPalette },
  { href: "/admin/analytics", label: "Analytics", icon: IconChart },
  { href: "/admin/analytics/saathi", label: "Saathi Health", icon: IconHeartPulse },
  { href: "/admin/audit-log", label: "Audit Log", icon: IconScroll },
] as const;

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const b64 = part.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(b64 + "=".repeat((4 - (b64.length % 4)) % 4)));
  } catch {
    return null;
  }
}

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Admin sections" className="flex-1 space-y-0.5 px-3 text-sm">
      {NAV.map(({ href, label, icon: NavIcon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={`relative flex items-center gap-3 rounded-sm px-3 py-2.5 transition-colors duration-150 ${
              active
                ? "bg-white/10 font-semibold text-paper-0"
                : "text-paper-0/65 hover:bg-white/5 hover:text-paper-0/90"
            }`}
          >
            {active && (
              <span
                aria-hidden="true"
                className="absolute inset-y-1.5 left-0 w-[3px] rounded-full bg-marigold-500"
              />
            )}
            <NavIcon size={18} className={active ? "text-marigold-500" : ""} />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarBody({ onNavigate, identity }: { onNavigate?: () => void; identity: { role: string; phone: string } | null }) {
  const router = useRouter();

  const logout = useCallback(() => {
    clearSession();
    router.push("/admin/login");
  }, [router]);

  return (
    <>
      <div className="flex items-center gap-3 px-6 pb-6 pt-7">
        <span className="text-marigold-500">
          <JunctionMark size={26} />
        </span>
        <div className="leading-tight">
          <p className="font-display text-base font-bold tracking-tight text-paper-0">
            Milan Admin
          </p>
          <p className="text-xs text-paper-0/65" aria-hidden="true">
            मिलन · संचालन
          </p>
        </div>
      </div>

      <NavItems onNavigate={onNavigate} />

      <div className="border-t border-white/10 px-4 py-4">
        {identity && (
          <div className="mb-3 px-1">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-paper-0/65">
              Signed in
            </p>
            <p className="mt-0.5 font-mono text-xs tabular-nums text-paper-0/85">
              {identity.phone}
            </p>
            <p className="mt-0.5 text-xs capitalize text-marigold-500">{identity.role}</p>
          </div>
        )}
        <button
          type="button"
          onClick={logout}
          className="flex min-h-11 w-full items-center gap-2.5 rounded-sm px-3 text-sm font-medium text-paper-0/65 transition-colors hover:bg-white/5 hover:text-paper-0"
        >
          <IconLogout size={17} />
          Sign out
        </button>
      </div>
    </>
  );
}

export function AdminShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [identity, setIdentity] = useState<{ role: string; phone: string } | null>(null);

  useEffect(() => {
    const token = getAdminToken();
    const payload = decodeJwtPayload(token);
    if (!payload) return;
    setIdentity({
      role: typeof payload.role === "string" ? payload.role : "staff",
      phone: typeof payload.sub === "string" ? `…${payload.sub.slice(-8)}` : "",
    });
  }, []);

  // Close the mobile drawer on route change.
  const pathname = usePathname();
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <ToastProvider>
      <div className="min-h-dvh bg-paper-100">
        {/* Mobile top bar */}
        <div className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-line200 bg-ink-900 px-4 lg:hidden">
          <div className="flex items-center gap-2.5">
            <span className="text-marigold-500">
              <JunctionMark size={22} />
            </span>
            <span className="font-display text-sm font-bold text-paper-0">Milan Admin</span>
          </div>
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation menu"
            aria-expanded={mobileOpen}
            className="flex h-11 w-11 items-center justify-center rounded-sm text-paper-0/80 transition-colors hover:bg-white/10"
          >
            <IconMenu size={22} />
          </button>
        </div>

        <div className="lg:grid lg:grid-cols-[16rem_1fr]">
          {/* Desktop sidebar — same canvas family as content, border between */}
          <aside className="sticky top-0 hidden h-dvh flex-col border-r border-ink-700 bg-ink-900 lg:flex">
            <SidebarBody identity={identity} />
          </aside>

          {/* Mobile slide-over */}
          {mobileOpen && (
            <div className="fixed inset-0 z-50 lg:hidden">
              <div
                className="absolute inset-0 bg-ink-900/50"
                aria-hidden="true"
                onClick={() => setMobileOpen(false)}
              />
              <aside
                role="dialog"
                aria-modal="true"
                aria-label="Admin navigation"
                className="absolute inset-y-0 left-0 flex w-72 flex-col bg-ink-900 shadow-floating"
                style={{ animation: "milan-slide-in-right 250ms var(--ease-out-milan)" }}
              >
                <button
                  type="button"
                  onClick={() => setMobileOpen(false)}
                  aria-label="Close navigation menu"
                  className="absolute right-3 top-3 flex h-11 w-11 items-center justify-center rounded-sm text-paper-0/70 transition-colors hover:bg-white/10"
                >
                  <IconClose size={20} />
                </button>
                <SidebarBody
                  identity={identity}
                  onNavigate={() => setMobileOpen(false)}
                />
              </aside>
            </div>
          )}

          <main className="min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-9">{children}</main>
        </div>
      </div>
    </ToastProvider>
  );
}
