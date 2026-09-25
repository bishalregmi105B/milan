"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { requestOtp, verifyOtp } from "@/lib/admin-api";
import { Button, Field, Input } from "@/components/ui";
import { IconInfo, JunctionMark } from "@/components/icons";

type Step = "phone" | "code";

export default function AdminLoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginCard />
    </Suspense>
  );
}

function LoginCard() {
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("+977");
  const [code, setCode] = useState("");
  const [dob, setDob] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const codeInputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionExpired = searchParams.get("expired") === "1";

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  async function request(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    const result = await requestOtp(phone);
    setBusy(false);
    if (!result.ok) {
      setError(result.error ?? "Couldn't send the code.");
      return;
    }
    setStep("code");
    setCooldown(result.cooldownSeconds ?? 60);
    requestAnimationFrame(() => codeInputRef.current?.focus());
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const result = await verifyOtp(phone, code, dob || undefined);
    if (!result.ok) {
      setBusy(false);
      setError(result.error ?? "Login failed.");
      return;
    }
    router.push("/admin/moderation");
  }

  return (
    <div className="relative flex min-h-dvh flex-col items-center justify-center bg-paper-100 px-4 py-12">
      {/* Himalayan dawn wash — a whisper of marigold behind the card */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 60% 45% at 50% 0%, rgba(245,166,35,0.14), transparent 70%)",
        }}
      />

      <main className="relative w-full max-w-md">
        <div className="rounded-lg border border-line200 bg-paper-50 p-8 shadow-floating sm:p-10">
          <div className="mb-8 flex flex-col items-center text-center">
            <span className="text-marigold-600">
              <JunctionMark size={44} />
            </span>
            <h1 className="mt-4 font-display text-2xl font-bold tracking-tight text-ink-900">
              Milan Admin
            </h1>
            <p className="mt-1.5 text-sm text-ink-500">
              Moderator · admin · founder access
            </p>
          </div>

          {sessionExpired && step === "phone" && (
            <div
              role="status"
              className="mb-5 flex items-start gap-2.5 rounded-sm border border-line300 bg-paper-100 px-3.5 py-3 text-sm text-ink-600"
            >
              <IconInfo size={17} className="mt-0.5 shrink-0 text-marigold-600" />
              Your session expired. Sign in again to continue.
            </div>
          )}

          {step === "phone" ? (
            <form onSubmit={request} className="space-y-5" aria-label="Request a sign-in code">
              <Field
                label="Phone number"
                htmlFor="phone"
                hint="We'll send a 6-digit code by SMS."
                error={error ?? undefined}
              >
                <Input
                  id="phone"
                  name="phone"
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+977 98XXXXXXXX"
                  aria-invalid={!!error}
                  aria-describedby={error ? "phone-error" : undefined}
                  required
                />
              </Field>
              <Button type="submit" size="lg" loading={busy} className="w-full">
                {busy ? "Sending…" : "Send code"}
              </Button>
            </form>
          ) : (
            <form onSubmit={verify} className="space-y-5" aria-label="Verify sign-in code">
              <div className="flex items-start gap-2.5 rounded-sm border border-line300 bg-paper-100 px-3.5 py-3 text-sm text-ink-600">
                <IconInfo size={17} className="mt-0.5 shrink-0 text-marigold-600" />
                <p>
                  Code sent to <span className="font-semibold">{phone}</span>.{" "}
                  <button
                    type="button"
                    onClick={() => {
                      setStep("phone");
                      setError(null);
                      setCode("");
                    }}
                    className="font-semibold text-dhaka-500 underline-offset-2 hover:underline"
                  >
                    Change number
                  </button>
                </p>
              </div>

              <Field
                label="Verification code"
                htmlFor="code"
                error={error ?? undefined}
              >
                <Input
                  ref={codeInputRef}
                  id="code"
                  name="code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]*"
                  maxLength={6}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                  placeholder="••••••"
                  className="text-center font-mono text-lg tracking-[0.4em]"
                  aria-invalid={!!error}
                  required
                />
              </Field>

              <Field
                label="Date of birth"
                htmlFor="dob"
                hint="Only needed the first time this number signs in."
              >
                <Input
                  id="dob"
                  name="dob"
                  type="date"
                  value={dob}
                  onChange={(e) => setDob(e.target.value)}
                  max={new Date(Date.now() - 1000 * 60 * 60 * 24 * 365 * 18).toISOString().slice(0, 10)}
                />
              </Field>

              <Button type="submit" size="lg" loading={busy} className="w-full">
                {busy ? "Signing in…" : "Sign in"}
              </Button>

              <button
                type="button"
                disabled={cooldown > 0 || resending}
                onClick={async () => {
                  setResending(true);
                  const result = await requestOtp(phone);
                  setResending(false);
                  if (result.ok) {
                    setCooldown(result.cooldownSeconds ?? 60);
                    setError(null);
                  } else {
                    setError(result.error ?? "Couldn't resend.");
                  }
                }}
                className="w-full text-center text-xs font-medium text-ink-500 transition-colors hover:text-ink-900 disabled:opacity-50"
              >
                {cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}
              </button>
            </form>
          )}
        </div>

        <p className="mx-auto mt-6 max-w-sm text-center text-xs leading-relaxed text-ink-400">
          Codes are delivered through the configured SMS provider and are never
          written to server logs. Local testing requires a test-only delivery
          adapter.
        </p>

        <p className="mt-4 text-center text-xs">
          <Link href="/" className="text-ink-400 underline-offset-2 transition-colors hover:text-ink-700 hover:underline">
            ← Back to milan.com.np
          </Link>
        </p>
      </main>
    </div>
  );
}
