// Admin API client — role-gated server-side on every Flask call (doc 6 §2).
// The JWT issued at /auth/otp/verify carries the user's role claim; every
// /api/v1/admin/* route re-checks it server-side (moderator/admin/founder).
//
// Session model: the access JWT lives ~15 minutes, the refresh JWT 24 hours.
// Both are kept in cookies; a single-flight 401 interceptor exchanges the
// refresh token for a new access token and retries the original request once
// before any caller sees an auth failure.

export const API_BASE =
  process.env.MILAN_API_BASE_URL ?? "https://milanapi.pukarphulara.com.np/api/v1";

const ACCESS_COOKIE = "milan_admin_token";
const REFRESH_COOKIE = "milan_admin_refresh";

export interface AuthUser {
  id: string;
  phone: string;
  is_verified: boolean;
  has_profile: boolean;
}

/* ── Error type with a human message per backend error code ───────────── */

export class AdminApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, status: number, message: string) {
    super(message);
    this.code = code;
    this.status = status;
    this.name = "AdminApiError";
  }
}

const ERROR_MESSAGES: Record<string, string> = {
  invalid_or_expired_otp: "That code didn't match, or it has expired. Request a fresh one.",
  age_gate_18_plus: "Milan is strictly 18+. This phone isn't linked to an eligible account — sign up in the Milan app with your date of birth first, then return here.",
  account_suspended: "This account is suspended and can't sign in to the admin console.",
  invalid_phone: "That doesn't look like a Nepali mobile number. Try 98XXXXXXXX.",
  sms_send_failed: "We couldn't send the SMS right now. Try again in a moment.",
  invalid_date_format: "Date of birth must be YYYY-MM-DD.",
  invalid_action: "That action isn't valid for this case.",
  invalid_case_type: "Unknown case type.",
  invalid_status: "That account status isn't valid.",
  invalid_decision: "Decision must be approve or reject.",
  invalid_scheduled_at: "Pick a valid date and time for the room.",
  missing_fields: "Some required fields are missing.",
  key_exists: "A preset with this key already exists — pick another key.",
  not_found: "That record no longer exists.",
  forbidden: "Your role doesn't permit this action.",
  internal_error: "Something went wrong on our side. Try again.",
  network_error: "Can't reach the Milan API. Check that the backend is running.",
};

export function humanError(code: string, fallback = "Something went wrong. Try again."): string {
  return ERROR_MESSAGES[code] ?? fallback;
}

/* ── Cookie helpers (client-side) ─────────────────────────────────────── */

function setCookie(name: string, value: string, maxAgeSeconds: number) {
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; samesite=lax`;
}

function clearCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0`;
}

export function clearSession() {
  clearCookie(ACCESS_COOKIE);
  clearCookie(REFRESH_COOKIE);
}

function readCookie(name: string): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

/* ── OTP login flow ───────────────────────────────────────────────────── */

export async function requestOtp(phone: string): Promise<{ ok: boolean; error?: string; cooldownSeconds?: number }> {
  try {
    const res = await fetch(`${API_BASE}/auth/otp/request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone }),
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { error?: string };
      const code = body.error ?? (res.status === 429 ? "rate_limited" : "unknown");
      return {
        ok: false,
        error:
          res.status === 429
            ? "Too many code requests. Wait a minute and try again."
            : humanError(code),
      };
    }
    const body = (await res.json()) as { resend_cooldown_seconds?: number };
    return { ok: true, cooldownSeconds: body.resend_cooldown_seconds };
  } catch {
    return { ok: false, error: ERROR_MESSAGES.network_error };
  }
}

export interface VerifyResult {
  ok: boolean;
  error?: string;
  user?: AuthUser;
}

export async function verifyOtp(
  phone: string,
  code: string,
  dateOfBirth?: string,
): Promise<VerifyResult> {
  try {
    const payload: Record<string, string> = { phone, code };
    if (dateOfBirth) payload.date_of_birth = dateOfBirth;
    const res = await fetch(`${API_BASE}/auth/otp/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { error?: string };
      const code = body.error ?? (res.status === 429 ? "rate_limited" : "unknown");
      return {
        ok: false,
        error:
          res.status === 429
            ? "Too many attempts. Wait a minute and try again."
            : humanError(code),
      };
    }
    const data = (await res.json()) as {
      access_token: string;
      refresh_token: string;
      user: AuthUser;
    };
    if (!data.access_token || !data.refresh_token) {
      return { ok: false, error: "Login succeeded but no session was issued. Try again." };
    }
    // Access cookie matches the ~15 min JWT; refresh outlives it and powers
    // the silent 401 interceptor below.
    setCookie(ACCESS_COOKIE, data.access_token, 60 * 60 * 24);
    setCookie(REFRESH_COOKIE, data.refresh_token, 60 * 60 * 24);
    return { ok: true, user: data.user };
  } catch {
    return { ok: false, error: ERROR_MESSAGES.network_error };
  }
}

export function getAdminToken(): string {
  return readCookie(ACCESS_COOKIE);
}

/* ── Single-flight 401 → refresh → retry interceptor ──────────────────── */

let refreshInFlight: Promise<boolean> | null = null;

async function exchangeRefreshToken(): Promise<boolean> {
  const refreshToken = readCookie(REFRESH_COOKIE);
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { Authorization: `Bearer ${refreshToken}` },
    });
    if (!res.ok) return false;
    const data = (await res.json()) as { access_token?: string };
    if (!data.access_token) return false;
    setCookie(ACCESS_COOKIE, data.access_token, 60 * 60 * 24);
    return true;
  } catch {
    return false;
  }
}

function refreshAccessToken(): Promise<boolean> {
  refreshInFlight ??= exchangeRefreshToken().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

function handleSessionExpired(): never {
  clearSession();
  if (typeof window !== "undefined" && !window.location.pathname.startsWith("/admin/login")) {
    window.location.href = "/admin/login?expired=1";
  }
  throw new AdminApiError("session_expired", 401, "Your session has expired. Please sign in again.");
}

interface FetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
}

/** Authenticated fetch with one silent refresh-and-retry on 401. */
async function adminFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const init = (): RequestInit => {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${getAdminToken()}`,
    };
    let body: BodyInit | undefined;
    if (options.body !== undefined) {
      if (typeof FormData !== "undefined" && options.body instanceof FormData) {
        // Let the browser add the multipart boundary.
        body = options.body;
      } else {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(options.body);
      }
    }
    return {
      method: options.method ?? "GET",
      headers,
      body,
      cache: "no-store",
    };
  };

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init());
  } catch {
    throw new AdminApiError("network_error", 0, ERROR_MESSAGES.network_error);
  }

  if (res.status === 401) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) handleSessionExpired();
    try {
      res = await fetch(`${API_BASE}${path}`, init());
    } catch {
      throw new AdminApiError("network_error", 0, ERROR_MESSAGES.network_error);
    }
    if (res.status === 401) handleSessionExpired();
  }

  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    throw new AdminApiError(
      body.error ?? `http_${res.status}`,
      res.status,
      humanError(body.error ?? "", `Request failed (${res.status}).`),
    );
  }
  return (await res.json()) as T;
}

/* ── API surface ──────────────────────────────────────────────────────── */

export class AdminApi {
  moderationQueue() {
    return adminFetch<{ queue: ModerationCase[] }>("/admin/moderation/queue");
  }

  caseContext(caseType: string, caseId: string) {
    return adminFetch<CaseContext>(`/admin/moderation/cases/${caseType}/${caseId}`);
  }

  resolveCase(caseType: string, caseId: string, action: string, note?: string) {
    return adminFetch<{ resolved: boolean }>(
      `/admin/moderation/cases/${caseType}/${caseId}/resolve`,
      { method: "POST", body: { action, note } },
    );
  }

  users(page = 1) {
    return adminFetch<UsersPage>(`/admin/users?page=${page}&per_page=25`);
  }

  userDetail(userId: string) {
    return adminFetch<UserDetail>(`/admin/users/${userId}`);
  }

  setUserStatus(userId: string, accountStatus: string) {
    return adminFetch<{ ok: boolean }>(`/admin/users/${userId}/status`, {
      method: "POST",
      body: { account_status: accountStatus },
    });
  }

  verificationQueue() {
    return adminFetch<{ queue: VerificationItem[] }>("/admin/verification-queue");
  }

  resolveVerification(checkId: string, decision: "approve" | "reject") {
    return adminFetch<{ resolved: boolean }>(
      `/admin/verification-queue/${checkId}/resolve`,
      { method: "POST", body: { decision } },
    );
  }

  circles() {
    return adminFetch<{ circles: CircleRow[] }>("/admin/circles");
  }

  featureCircle(circleId: string, featured: boolean) {
    return adminFetch<{ is_featured: boolean }>(`/admin/circles/${circleId}/feature`, {
      method: "POST",
      body: { featured },
    });
  }

  scheduleRoom(circleId: string, title: string, scheduledAt: string) {
    return adminFetch<{ id: string }>(`/admin/circles/${circleId}/rooms`, {
      method: "POST",
      body: { title, scheduled_at: scheduledAt },
    });
  }

  presets() {
    return adminFetch<{ presets: PresetRow[] }>("/admin/personalization/presets");
  }

  createPreset(preset: Omit<PresetRow, "id" | "is_active"> & { sort_order?: number }) {
    return adminFetch<{ id: string }>("/admin/personalization/presets", {
      method: "POST",
      body: preset,
    });
  }

  retirePreset(presetId: string) {
    return adminFetch<{ retired: boolean }>(`/admin/personalization/presets/${presetId}`, {
      method: "DELETE",
    });
  }

  analyticsOverview() {
    return adminFetch<AnalyticsOverview>("/admin/analytics/overview");
  }

  analyticsHistory() {
    return adminFetch<{ series: HistoryPoint[] }>("/admin/analytics/history");
  }

  saathiAnalytics() {
    return adminFetch<SaathiAnalytics>("/admin/analytics/saathi");
  }

  auditLog() {
    return adminFetch<{ events: AuditEvent[] }>("/admin/audit-log");
  }
}

/** Shared instance — the token is read from the cookie per request. */

/* ── Payments (Phase-1 manual QR verification queue) ───────────────────── */

export interface PaymentSubmission {
  id: string;
  user_id: string;
  user_email: string | null;
  tier: string;
  amount_npr: number;
  method: string;
  reference_id: string;
  screenshot_url: string | null;
  note: string | null;
  status: string;
  fraud_flags: string[];
  submitted_at: string;
}

export async function listSubmissions(
  status: "pending" | "approved" | "rejected" | "all" = "pending",
): Promise<PaymentSubmission[]> {
  const res = await adminFetch<{ submissions: PaymentSubmission[] }>(
    `/billing/admin/submissions?status=${status}`,
  );
  return res.submissions;
}

export async function reviewSubmission(
  id: string,
  decision: "approve" | "reject",
  reason?: string,
): Promise<{ id: string; status: string }> {
  return adminFetch<{ id: string; status: string }>(
    `/billing/admin/submissions/${id}/review`,
    { method: "POST", body: { decision, reason } },
  );
}

export async function uploadPaymentQr(
  method: string,
  file: File,
  accountLabel?: string,
): Promise<{ method: string; image_url: string }> {
  const form = new FormData();
  form.append("image", file);
  if (accountLabel) form.append("account_label", accountLabel);
  return adminFetch<{ method: string; image_url: string }>(
    `/billing/admin/qr/${method}`,
    { method: "POST", body: form },
  );
}

export const adminApi = new AdminApi();

/* ── Response shapes ──────────────────────────────────────────────────── */

export interface ModerationCase {
  case_type: string;
  id: string;
  severity: string;
  reason?: string;
  patterns?: string[];
  confidence?: number;
  target_id?: string;
  reporter_id?: string;
  flagged_user_id?: string | null;
  created_at: string;
}

export interface CaseContext {
  case_type: string;
  case_id: string;
  reason?: string;
  details?: string | null;
  status?: string;
  patterns?: string[];
  confidence?: number;
  risk_level?: string;
  target?: {
    id: string;
    account_status: string;
    is_verified: boolean;
    reports_against: number;
  } | null;
  thread_preview?: { sender_id: string; body: string | null; created_at: string }[];
}

export interface AdminUserRow {
  id: string;
  phone_masked: string;
  is_verified: boolean;
  account_status: string;
  role: string;
  created_at: string;
}

export interface UsersPage {
  users: AdminUserRow[];
  total: number;
  page: number;
  pages: number;
}

export interface UserDetail {
  user: {
    id: string;
    phone_masked: string;
    account_status: string;
    role: string;
    is_verified: boolean;
    intent_mode: string;
    created_at: string;
  };
  profile: { display_name: string | null; bio: string | null; photo_count: number };
  reports_filed: number;
  reports_against: number;
  has_face_embedding: boolean;
}

export interface VerificationItem {
  id: string;
  user_id: string;
  display_name?: string | null;
  status: string;
  passed: boolean | null;
  failure_reason: string | null;
  created_at: string;
}

export interface CircleRow {
  id: string;
  name: string;
  category: string;
  description?: string | null;
  is_featured: boolean;
  member_count: number;
}

export interface PresetRow {
  id: string;
  key: string;
  pack: string;
  name: string;
  wallpaper_type: string;
  wallpaper_value: string;
  bubble_color_sent: string;
  bubble_color_received: string;
  is_active: boolean;
}

export interface AnalyticsOverview {
  dau: number;
  wau: number;
  mau: number;
  matches_7d: number;
  match_rate_7d: number;
  revenue_npr_total: number;
}

export interface HistoryPoint {
  date: string;
  signups: number;
  matches: number;
  revenue_npr: number;
}

export interface SaathiAnalytics {
  total_sessions: number;
  proactive_opt_in_count: number;
  paused_count: number;
  crisis_flagged_sessions_aggregate: number;
  sessions_hitting_daily_cap_today: number;
}

export interface AuditEvent {
  id: string;
  subject_type: string;
  subject_id: string | null;
  source: string;
  action: string;
  categories: string[];
  actor_id: string | null;
  created_at: string;
}
