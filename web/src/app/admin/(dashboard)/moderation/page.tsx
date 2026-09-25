"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { adminApi, type ModerationCase } from "@/lib/admin-api";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  PageHeader,
  severityBadge,
  Table,
  TableSkeleton,
  THead,
  TD,
  useToast,
} from "@/components/ui";
import { IconInbox, IconShield } from "@/components/icons";

// Severity-first sort is already applied server-side (doc 6 §2); we preserve it.
export default function ModerationQueuePage() {
  const [cases, setCases] = useState<ModerationCase[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const { success, error: toastError } = useToast();

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setCases((await adminApi.moderationQueue()).queue);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load the queue.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function resolve(c: ModerationCase, action: string) {
    setBusyId(c.id);
    try {
      await adminApi.resolveCase(c.case_type, c.id, action);
      success(
        `Case ${action.replace("_", " ")}d`,
        `${c.case_type} case resolved — written to the audit log.`,
      );
      await load();
    } catch (e) {
      toastError(
        "Couldn't resolve case",
        e instanceof Error ? e.message : "Please try again.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Moderation queue"
        description="Reports and scam flags awaiting a decision, highest severity first. Every action writes to the audit log with actor + timestamp."
      />

      {loadError && (
        <ErrorState
          title="Couldn't load the queue"
          message={loadError}
          onRetry={() => void load()}
        />
      )}

      {!loadError && !cases && <TableSkeleton rows={4} cols={5} />}

      {!loadError && cases && cases.length === 0 && (
        <EmptyState
          icon={<IconInbox size={24} />}
          title="Queue is clear"
          description="No open reports or unreviewed scam flags right now. New cases appear here the moment users flag them."
        />
      )}

      {!loadError && cases && cases.length > 0 && (
        <Table>
          <THead columns={["Severity", "Type", "Detail", "Received", "Actions"]} />
          <tbody>
            {cases.map((c) => (
              <tr key={`${c.case_type}-${c.id}`} className="transition-colors hover:bg-paper-100/60">
                <TD>
                  <Badge variant={severityBadge(c.severity)}>{c.severity}</Badge>
                </TD>
                <TD className="whitespace-nowrap font-medium text-ink-900">{c.case_type}</TD>
                <TD className="max-w-xs">
                  <Link
                    href={{
                      pathname: `/admin/moderation/${c.id}`,
                      query: { type: c.case_type, target: c.target_id ?? c.flagged_user_id ?? "" },
                    }}
                    className="font-medium text-dhaka-500 underline-offset-2 hover:underline"
                  >
                    {c.reason ?? c.patterns?.join(", ") ?? c.id.slice(0, 8)}
                  </Link>
                  {c.confidence != null && (
                    <span className="ml-2 font-mono text-xs tabular-nums text-ink-400">
                      {(c.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </TD>
                <TD className="whitespace-nowrap text-xs text-ink-500">
                  {new Date(c.created_at).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </TD>
                <TD className="whitespace-nowrap">
                  <div className="flex justify-end gap-1.5">
                    {["dismiss", "warn_user", "suspend", "escalate"].map((a) => (
                      <Button
                        key={a}
                        size="sm"
                        variant={a === "suspend" ? "destructive" : "outline"}
                        loading={busyId === c.id && a === "suspend"}
                        disabled={busyId !== null}
                        onClick={() => void resolve(c, a)}
                        title={a === "suspend" ? "Suspend the flagged account" : undefined}
                      >
                        {a.replace("_", " ")}
                      </Button>
                    ))}
                  </div>
                </TD>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {cases && cases.length > 0 && (
        <p className="mt-4 flex items-center gap-2 text-xs text-ink-400">
          <IconShield size={14} />
          Suspending also deactivates the target account immediately.
        </p>
      )}
    </div>
  );
}
