export const APK_DOWNLOAD_URL = process.env.NEXT_PUBLIC_MILAN_APK_URL?.trim() ?? "";

export function hasApkDownload(): boolean {
  return APK_DOWNLOAD_URL.length > 0;
}
