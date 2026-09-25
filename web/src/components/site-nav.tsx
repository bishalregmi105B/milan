"use client";

// Client nav for the marketing chrome — active-link highlighting needs
// usePathname, so the interactive header lives here while the server layout
// supplies the dictionary.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { MilanLogo } from "./milan-logo";
import { IconClose, IconMenu } from "./icons";

const LINKS = [
  { href: "/features", key: "features" },
  { href: "/safety", key: "safety" },
  { href: "/saathi", key: "saathi" },
  { href: "/pricing", key: "pricing" },
] as const;

export function SiteNav({
  dict,
}: {
  dict: Record<(typeof LINKS)[number]["key"], string> & { download: string };
}) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  // Close the sheet whenever the route changes.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header className="sticky top-0 z-40 border-b border-line200/80 bg-paper-0/85 backdrop-blur-md">
      <nav
        aria-label="Main"
        className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-6"
      >
        <Link
          href="/"
          className="flex items-center gap-2.5 rounded-sm"
          aria-label="Milan — home"
        >
          <MilanLogo size={30} wordmark />
          <span className="mt-0.5 hidden text-sm text-ink-400 sm:inline" aria-hidden="true">
            मिलन
          </span>
        </Link>

        <div className="hidden items-center gap-7 sm:flex">
          {LINKS.map(({ href, key }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={`relative rounded-sm py-1 text-sm font-medium transition-colors ${
                  active ? "text-ink-900" : "text-ink-500 hover:text-ink-900"
                }`}
              >
                {dict[key]}
                {active && (
                  <span
                    aria-hidden="true"
                    className="absolute -bottom-[21px] left-0 right-0 h-[2.5px] rounded-full bg-marigold-500"
                  />
                )}
              </Link>
            );
          })}
          <Link
            href="/download"
            className="inline-flex min-h-10 items-center rounded-sm bg-marigold-500 px-4 py-2 text-sm font-semibold text-ink-900 transition-colors hover:bg-marigold-600 active:bg-marigold-700"
          >
            {dict.download}
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? "Close menu" : "Open menu"}
          className="flex h-11 w-11 items-center justify-center rounded-sm text-ink-700 transition-colors hover:bg-paper-100 sm:hidden"
        >
          {open ? <IconClose size={22} /> : <IconMenu size={22} />}
        </button>
      </nav>

      {/* Mobile sheet */}
      {open && (
        <div id="mobile-nav" className="border-t border-line200 bg-paper-0 sm:hidden">
          <div className="space-y-1 px-4 py-4">
            {LINKS.map(({ href, key }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={`block rounded-sm px-3 py-3 text-base font-medium transition-colors ${
                    active
                      ? "bg-paper-100 text-ink-900"
                      : "text-ink-600 hover:bg-paper-100 hover:text-ink-900"
                  }`}
                >
                  {dict[key]}
                </Link>
              );
            })}
            <Link
              href="/download"
              className="mt-2 block rounded-sm bg-marigold-500 px-3 py-3 text-center text-base font-semibold text-ink-900 transition-colors hover:bg-marigold-600"
            >
              {dict.download}
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
