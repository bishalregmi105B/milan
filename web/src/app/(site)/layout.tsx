import { getDictionary } from "@/lib/i18n";
import { cookies } from "next/headers";
import Link from "next/link";
import { SiteNav } from "@/components/site-nav";
import { MilanLogo } from "@/components/milan-logo";

export default async function SiteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Locale from cookie set by the language toggle on /download.
  const jar = await cookies();
  const dict = getDictionary(jar.get("milan_lang")?.value);

  return (
    <div className="flex min-h-dvh flex-col">
      <SiteNav dict={dict.nav} />

      <main className="flex-1">{children}</main>

      <footer className="mt-24 border-t border-line200 bg-paper-100/50">
        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-10 px-6 py-14 sm:grid-cols-3">
          <div>
            <div className="flex items-center gap-2.5">
              <MilanLogo size={26} wordmark />
              <span className="font-body text-sm text-ink-400">(मिलन)</span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink-500">
              Union. Meeting. Confluence — where two paths meet.
            </p>
          </div>
          <div className="space-y-2.5 text-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-ink-400">
              Legal
            </p>
            <Link
              href="/privacy"
              className="block text-ink-500 transition-colors hover:text-ink-900"
            >
              {dict.footer.privacy}
            </Link>
            <Link
              href="/terms"
              className="block text-ink-500 transition-colors hover:text-ink-900"
            >
              {dict.footer.terms}
            </Link>
          </div>
          <div className="space-y-2.5 text-sm">
            <p className="text-xs font-semibold uppercase tracking-wider text-ink-400">
              Company
            </p>
            <Link
              href="/admin/login"
              className="block text-ink-500 underline-offset-2 transition-colors hover:text-ink-900 hover:underline"
            >
              Admin
            </Link>
            <p className="text-ink-500">Made for Nepal 🇳🇵</p>
          </div>
        </div>
        <div className="border-t border-line200">
          <p className="mx-auto max-w-6xl px-6 py-4 text-xs text-ink-400">
            © {new Date().getFullYear()} Milan · 18+ · Kathmandu
          </p>
        </div>
      </footer>
    </div>
  );
}
