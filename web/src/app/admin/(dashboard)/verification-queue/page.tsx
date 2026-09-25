"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi, type VerificationItem } from "@/lib/admin-api";
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
import { IconBadgeCheck } from "@/components/icons";

// Manual review for liveness edge cases the automated pass didn't resolve.
export default function VerificationQueuePage() {
  const [items, setItems] = useState<VerificationItem[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const { success, error: toastError } = useToast();

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setItems((await adminApi.verificationQueue()).queue);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load the queue.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function resolve(item: VerificationItem, decision: "approve" | "reject") {
    setBusyId(item.id);
    try {
      await adminApi.resolveVerification(item.id, decision);
      success(
        decision === "approve" ? "Verification approved" : "Verification rejected",
        item.display_name
          ? `${item.display_name} ${decision === "approve" ? "is now verified" : "remains unverified"}.`
          : "The reviewer decision is recorded in the audit log.",
      );
      await load();
    } catch (e) {
      toastError(
        "Couldn't record decision",
        e instanceof Error ? e.message : "Please try again.",
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Verification queue"
        description="Liveness checks the automated pass couldn't cleanly resolve. Approving marks the account as verified; rejecting leaves it unverified."
      />

      {loadError && (
        <ErrorState
          title="Couldn't load the queue"
          message={loadError}
          onRetry={() => void load()}
        />
      )}

      {!loadError && !items && <TableSkeleton rows={4} cols={5} />}

      {!loadError && items && items.length === 0 && (
        <EmptyState
          icon={<IconBadgeCheck size={24} />}
          title="No pending liveness reviews"
          description="The automated verification pass is keeping up. Edge cases land here for a human decision."
        />
      )}

      {!loadError && items && items.length > 0 && (
        <Table>
          <THead columns={["User", "Status", "Reason", "Submitted", "Actions"]} />
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="transition-colors hover:bg-paper-100/60">
                <TD className="font-medium text-ink-900">
                  {item.display_name ?? (
                    <span className="font-mono text-xs">{item.user_id.slice(0, 8)}</span>
                  )}
                </TD>
                <TD>
                  <Badge variant={item.passed === false ? "warning" : statusBadge(item.status)}>
                    {item.status}
                  </Badge>
                </TD>
                <TD className="text-ink-500">{item.failure_reason ?? "—"}</TD>
                <TD className="whitespace-nowrap text-xs text-ink-500">
                  {new Date(item.created_at).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </TD>
                <TD className="whitespace-nowrap">
                  <div className="flex justify-end gap-1.5">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busyId !== null}
                      onClick={() => void resolve(item, "approve")}
                    >
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      loading={busyId === item.id}
                      disabled={busyId !== null}
                      onClick={() => void resolve(item, "reject")}
                    >
                      Reject
                    </Button>
                  </div>
                </TD>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
