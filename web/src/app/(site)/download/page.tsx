import type { Metadata } from "next";
import { cookies } from "next/headers";
import { getDictionary } from "@/lib/i18n";
import { DownloadClient } from "./download-client";

export const metadata: Metadata = {
  title: "Download",
  description:
    "Get Milan on your phone — free to download, 18+, Nepali & English. App Store and Google Play, coming soon.",
};

export default async function DownloadPage() {
  const jar = await cookies();
  const dict = getDictionary(jar.get("milan_lang")?.value);
  const locale = jar.get("milan_lang")?.value === "ne" ? "ne" : "en";
  return <DownloadClient initialLocale={locale} nav={dict.nav} />;
}
