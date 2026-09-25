// Cookie helpers for admin pages.
// Both JWTs are written client-side by `verifyOtp` in lib/admin-api.ts after a
// successful /auth/otp/verify exchange; the Flask side re-checks the role claim
// on every /api/v1/admin/* call regardless of what these cookies hold.
// The 401 interceptor in admin-api.ts silently rotates the access token using
// the refresh cookie, and clears both when the refresh itself fails.
export const COOKIES = {
  ACCESS: "milan_admin_token",
  REFRESH: "milan_admin_refresh",
} as const;

export const cookies = {
  async getAdminToken(): Promise<string> {
    if (typeof document === "undefined") return "";
    const match = document.cookie.match(
      /(?:^|;\s*)milan_admin_token=([^;]*)/,
    );
    return match ? decodeURIComponent(match[1]) : "";
  },
  async getRefreshToken(): Promise<string> {
    if (typeof document === "undefined") return "";
    const match = document.cookie.match(
      /(?:^|;\s*)milan_admin_refresh=([^;]*)/,
    );
    return match ? decodeURIComponent(match[1]) : "";
  },
  clearSession() {
    if (typeof document === "undefined") return;
    document.cookie = `${COOKIES.ACCESS}=; path=/; max-age=0`;
    document.cookie = `${COOKIES.REFRESH}=; path=/; max-age=0`;
  },
};
