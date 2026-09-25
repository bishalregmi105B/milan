"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { adminApi, type CaseContext } from "@/lib/admin-api";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ConfirmDialog,
  ErrorState,
  Skeleton,
  severityBadge,
  useToast,
} from "@/components/ui";

// Case detail: full thread context + user history + one-click resolve (doc 6 §2).
export default function CaseDetailPage() {
  const params = useParams<{ caseId: string }>();
  const searchParams = useSearchParams();
  const caseId = params.caseId;
  const caseType = searchParams.get("type") ?? "report";

  const [context, setContext] = useState<CaseContext | null>(null);
  const [resolved, setResolved] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [confirmSuspend, setConfirmSuspend] = useState(false);
  const { success, error: toastError } = useToast();

  const load = useCallback(async () => {
    if (!caseId) return;
    setLoadError(null);
    try {
      setContext(await adminApi.caseContext(caseType, caseId));
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load this case.");
    }
  }, [caseId, caseType]);

  useEffect(() => {
    void load();
  }, [load]);

  async function resolve(action: string) {
    if (!caseId) return;
    setBusyAction(action);
    try {
      await adminApi.resolveCase(caseType, caseId, action);
      setResolved(action);
      success(`Case ${action.replace("_", " ")}d`, "The decision is recorded in the audit log.");
    } catch (e) {
      toastError("Couldn't resolve case", e instanceof Error ? e.message : "Please try again.");
    } finally {
      setBusyAction(null);
      setConfirmSuspend(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <Link
        href="/admin/moderation"
        className="text-sm font-medium text-dhaka-500 underline-offset-2 hover:underline"
      >
        ← Back to queue
      </Link>

      <h1 className="mt-4 font-display text-2xl font-bold tracking-tight text-ink-900">
        Case · {caseType}{" "}
        <span className="font-mono text-base font-normal text-ink-400">
          {caseId.slice(0, 8)}…
        </span>
      </h1>

      {loadError && (
        <div className="mt-6">
          <ErrorState
            title="Couldn't load this case"
            message={loadError}
            onRetry={() => void load()}
          />
        </div>
      )}

      {!loadError && !context && (
        <div className="mt-6 space-y-4">
          <Skeleton className="h-44 w-full rounded-md" />
          <Skeleton className="h-28 w-full rounded-md" />
        </div>
      )}

      {resolved && (
        <Card className="mt-6 border-pine-200 bg-pine-100/60">
          <CardContent className="flex items-center gap-3 pt-4">
            <Badge variant="success">resolved</Badge>
            <p className="text-sm text-pine-700">
              Action taken: <strong className="font-semibold">{resolved.replace("_", " ")}</strong>
            </p>
          </CardContent>
        </Card>
      )}

      {!loadError && context && !resolved && (
        <div className="mt-6 space-y-5">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-2.5 text-sm">
                {context.reason && (
                  <div className="flex gap-2">
                    <dt className="w-20 shrink-0 text-ink-400">Reason</dt>
                    <dd className="font-medium text-ink-900">{context.reason}</dd>
                  </div>
                )}
                {context.details && (
                  <div className="flex gap-2">
                    <dt className="w-20 shrink-0 text-ink-400">Reported</dt>
                    <dd className="text-ink-600">{context.details}</dd>
                  </div>
                )}
                {context.risk_level && (
                  <div className="flex items-center gap-2">
                    <dt className="w-20 shrink-0 text-ink-400">Risk</dt>
                    <dd>
                      <Badge variant={severityBadge(context.risk_level)}>{context.risk_level}</Badge>
                    </dd>
                  </div>
                )}
                {context.status && (
                  <div className="flex items-center gap-2">
                    <dt className="w-20 shrink-0 text-ink-400">Status</dt>
                    <dd>
                      <Badge variant="outline">{context.status}</Badge>
                    </dd>
                  </div>
                )}
                {context.patterns && context.patterns.length > 0 && (
                  <div className="flex gap-2">
                    <dt className="w-20 shrink-0 text-ink-400">Patterns</dt>
                    <dd className="text-ink-600">{context.patterns.join(", ")}</dd>
                  </div>
                )}
                {context.confidence != null && (
                  <div className="flex gap-2">
                    <dt className="w-20 shrink-0 text-ink-400">Confidence</dt>
                    <dd className="font-mono tabular-nums text-ink-600">
                      {(context.confidence * 100).toFixed(0)}%
                    </dd>
                  </div>
                )}
                {context.target && (
                  <div className="flex items-center gap-2 border-t border-line100 pt-3">
                    <dt className="w-20 shrink-0 text-ink-400">Target</dt>
                    <dd>
                      <Link
                        href={`/admin/users/${context.target.id}`}
                        className="font-medium text-dhaka-500 underline-offset-2 hover:underline"
                      >
                        View user →
                      </Link>
                      <span className="ml-2 text-xs text-ink-500">
                        status {context.target.account_status} ·{" "}
                        <span className="tabular-nums">{context.target.reports_against}</span>{" "}
                        reports against
                      </span>
                    </dd>
                  </div>
                )}
              </dl>
            </CardContent>
          </Card>

          {context.thread_preview && context.thread_preview.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Thread preview</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="max-h-80 space-y-3 overflow-y-auto pr-1">
                  {context.thread_preview.map((m, i) => (
                    <div key={i} className="flex gap-3 text-sm">
                      <span className="w-16 shrink-0 pt-0.5 font-mono text-[10px] text-ink-400">
                        {m.sender_id.slice(0, 8)}
                      </span>
                      <span className="text-ink-600">{m.body}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="flex flex-wrap gap-2.5 border-t border-line200 pt-5">
            {["dismiss", "warn_user", "suspend", "escalate"].map((a) =>
              a === "suspend" ? (
                <Button
                  key={a}
                  variant="destructive"
                  loading={busyAction === a}
                  disabled={busyAction !== null}
                  onClick={() => setConfirmSuspend(true)}
                >
                  Suspend user
                </Button>
              ) : (
                <Button
                  key={a}
                  variant={a === "warn_user" ? "secondary" : "outline"}
                  loading={busyAction === a}
                  disabled={busyAction !== null}
                  onClick={() => void resolve(a)}
                >
                  {a.replace("_", " ")}
                </Button>
              ),
            )}
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmSuspend}
        onClose={() => setConfirmSuspend(false)}
        onConfirm={() => void resolve("suspend")}
        title="Suspend this account?"
        description="The target account will be deactivated immediately and the decision recorded in the audit log with your actor ID. You can reactivate the user later from the Users page."
        confirmLabel="Suspend account"
        destructive
        busy={busyAction === "suspend"}
      />
    </div>
  );
}
