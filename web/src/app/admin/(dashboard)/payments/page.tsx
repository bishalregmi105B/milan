"use client";

import { useCallback, useEffect, useState } from "react";
import {
  adminApi,
  listSubmissions,
  reviewSubmission,
  uploadPaymentQr,
  type PaymentSubmission,
} from "@/lib/admin-api";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  PageHeader,
  Table,
  TableSkeleton,
  THead,
  TD,
  statusBadge,
  useToast,
} from "@/components/ui";

// Phase-1 manual payment verification: the revenue lifeline. Users pay via
// static QR in their wallet app and submit the transaction reference here;
// NOTHING unlocks until a human approves — every decision is audit-logged
// server-side.
export default function PaymentsPage() {
  const [items, setItems] = useState<PaymentSubmission[] | null>(null);
  const [statusFilter, setStatusFilter] = useState<
    "pending" | "approved" | "rejected" | "all"
  >("pending");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState<PaymentSubmission | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const { success, error: toastError } = useToast();

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setItems(await listSubmissions(statusFilter));
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to load payments.");
    }
  }, [statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const decide = async (
    submission: PaymentSubmission,
    decision: "approve" | "reject",
  ) => {
    if (decision === "reject" && !rejectReason.trim()) {
      toastError("A rejection reason is required.");
      return;
    }
    setBusyId(submission.id);
    try {
      await reviewSubmission(submission.id, decision, rejectReason.trim() || undefined);
      success(
        decision === "approve"
          ? `Approved — ${submission.tier.toUpperCase()} pass is live for ${submission.user_email ?? submission.user_id}.`
          : "Rejected and the user has been notified.",
      );
      setRejecting(null);
      setRejectReason("");
      await load();
    } catch (err) {
      toastError(err instanceof Error ? err.message : "Review failed.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <PageHeader
        title="Payment Queue"
        description="Manual QR verification — approve only what the screenshot and reference ID support. Approval activates the pass immediately."
      />

      <div className="mb-4 flex gap-2">
        {(["pending", "approved", "rejected", "all"] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`rounded-full border px-3 py-1.5 text-sm capitalize ${
              statusFilter === s
                ? "border-dhaka-500 bg-dhaka-500/10 text-dhaka-600"
                : "border-line-200 text-ink-500"
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {loadError !== null ? (
        <ErrorState message={loadError} onRetry={() => void load()} />
      ) : items === null ? (
        <TableSkeleton rows={4} cols={6} />
      ) : items.length === 0 ? (
        <EmptyState
          title="Nothing in the queue"
          description="No payment submissions with this status."
        />
      ) : (
        <Table>
          <THead
            columns={[
              "User",
              "Tier / Amount",
              "Method",
              "Reference",
              "Proof",
              "Submitted",
              "Status",
              "",
            ]}
          />
          <tbody>
            {items.map((s) => (
              <tr key={s.id} className="align-top">
                <TD>
                  <div className="font-medium">{s.user_email ?? s.user_id}</div>
                  {s.note ? (
                    <div className="mt-1 max-w-56 text-xs text-ink-400">“{s.note}”</div>
                  ) : null}
                </TD>
                <TD>
                  <span className="font-semibold capitalize">{s.tier}</span>
                  <div className="text-xs text-ink-500">NPR {s.amount_npr}</div>
                </TD>
                <TD className="capitalize">{s.method}</TD>
                <TD>
                  <code className="rounded bg-paper-100 px-1.5 py-0.5 text-xs">
                    {s.reference_id}
                  </code>
                  {s.fraud_flags.length > 0 ? (
                    <div className="mt-1 flex flex-col gap-0.5">
                      {s.fraud_flags.map((flag) => (
                        <Badge key={flag} variant="warning">
                          ⚠ {flag.replaceAll("_", " ")}
                        </Badge>
                      ))}
                    </div>
                  ) : null}
                </TD>
                <TD>
                  {s.screenshot_url ? (
                    <a
                      href={s.screenshot_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-dhaka-600 underline"
                    >
                      View proof
                    </a>
                  ) : (
                    <span className="text-xs text-ink-400">none</span>
                  )}
                </TD>
                <TD className="whitespace-nowrap text-xs text-ink-500">
                  {new Date(s.submitted_at).toLocaleString()}
                </TD>
                <TD>{statusBadge(s.status)}</TD>
                <TD>
                  {s.status === "pending" ? (
                    <div className="flex flex-col gap-1.5">
                      <Button
                        size="sm"
                        onClick={() => void decide(s, "approve")}
                        disabled={busyId === s.id}
                      >
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setRejecting(s);
                          setRejectReason("");
                        }}
                        disabled={busyId === s.id}
                      >
                        Reject
                      </Button>
                    </div>
                  ) : (
                    <span className="text-xs text-ink-400">reviewed</span>
                  )}
                </TD>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {rejecting ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-6">
          <div className="w-full max-w-md rounded-xl bg-paper-0 p-6 shadow-xl">
            <h3 className="mb-1 font-semibold">Reject payment</h3>
            <p className="mb-4 text-sm text-ink-500">
              {rejecting.user_email ?? rejecting.user_id} — {rejecting.tier} · NPR{" "}
              {rejecting.amount_npr} · ref {rejecting.reference_id}
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              placeholder="Reason shown to the user (required) — e.g. reference ID not found in eSewa statement"
              className="mb-4 w-full rounded-lg border border-line-200 p-3 text-sm"
            />
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={() => setRejecting(null)}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={() => void decide(rejecting, "reject")}
                disabled={busyId === rejecting.id}
              >
                Reject payment
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      <QrUploader />
    </div>
  );
}

function QrUploader() {
  const [method, setMethod] = useState("esewa");
  const [file, setFile] = useState<File | null>(null);
  const [label, setLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const { success, error: toastError } = useToast();

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    try {
      await uploadPaymentQr(method, file, label || undefined);
      success("QR updated — live in the app checkout.");
      setFile(null);
    } catch (err) {
      toastError(err instanceof Error ? err.message : "QR upload failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-8 rounded-xl border border-line-200 p-5">
      <h3 className="mb-1 font-semibold">Upload a payment QR</h3>
      <p className="mb-4 text-sm text-ink-500">
        The QR shown on the app checkout for each wallet. Replace anytime —
        changes are live immediately.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value)}
          className="rounded-lg border border-line-200 px-3 py-2 text-sm capitalize"
        >
          {["esewa", "khalti", "fonepay", "connectips"].map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Account label (e.g. Milan — 98XXXXXXXX)"
          className="w-64 rounded-lg border border-line-200 px-3 py-2 text-sm"
        />
        <Button onClick={() => void upload()} disabled={!file || busy}>
          {busy ? "Uploading…" : "Upload QR"}
        </Button>
      </div>
    </div>
  );
}
