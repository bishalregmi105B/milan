"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { adminApi, type AuditEvent } from "@/lib/admin-api";
import {
  Badge,
  EmptyState,
  ErrorState,
  Input,
  PageHeader,
  Table,
  TableSkeleton,
  THead,
  TD,
} from "@/components/ui";
import { IconSearch, IconScroll } from "@/components/icons";

// Immutable decision trail — every moderation/admin action lands here with
// actor + timestamp (doc 6 §2). Read-only: nothing in the log is editable.
export default function AuditLogPage() {
  const [events, setEvents] = useState<AuditEvent[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setEvents((await adminApi.auditLog()).events);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load the audit log.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(
    () =>
      (events ?? []).filter((e) =>
        query
          ? `${e.action} ${e.subject_type} ${e.source} ${e.actor_id ?? ""}`
              .toLowerCase()
              .includes(query.toLowerCase())
          : true,
      ),
    [events, query],
  );

  const sourceVariant = (source: string) => {
    switch (source) {
      case "media_moderation":
        return "neutral" as const;
      case "admin":
        return "accent" as const;
      default:
        return "outline" as const;
    }
  };

  return (
    <div>
      <PageHeader
        title="Audit log"
        description="The last 200 recorded actions across moderation, media, and admin tooling — who did what, and when. This log is append-only."
        actions={
          <div className="relative">
            <IconSearch
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400"
            />
            <Input
              type="search"
              placeholder="Filter by action, source…"
              aria-label="Filter audit events"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-9 sm:w-64"
            />
          </div>
        }
      />

      {loadError && (
        <ErrorState
          title="Couldn't load the audit log"
          message={loadError}
          onRetry={() => void load()}
        />
      )}

      {!loadError && !events && <TableSkeleton rows={8} cols={5} />}

      {!loadError && events && filtered.length === 0 && (
        <EmptyState
          icon={<IconScroll size={24} />}
          title={query ? "No events match" : "No events recorded yet"}
          description={
            query
              ? `Nothing matches “${query}”. Clear the filter to see the full log.`
              : "Actions taken across moderation and admin tooling will appear here."
          }
          action={
            query ? (
              <button
                onClick={() => setQuery("")}
                className="text-sm font-semibold text-dhaka-500 underline-offset-2 hover:underline"
              >
                Clear filter
              </button>
            ) : undefined
          }
        />
      )}

      {!loadError && events && filtered.length > 0 && (
        <Table>
          <THead columns={["When", "Subject", "Action", "Source", "Actor"]} />
          <tbody>
            {filtered.map((e) => (
              <tr key={e.id} className="transition-colors hover:bg-paper-100/60">
                <TD className="whitespace-nowrap text-xs text-ink-500">
                  {new Date(e.created_at).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </TD>
                <TD>
                  <span className="font-medium capitalize text-ink-900">{e.subject_type}</span>
                  {e.subject_id && (
                    <span className="ml-2 font-mono text-[11px] text-ink-400" title={e.subject_id}>
                      {e.subject_id.slice(0, 8)}
                    </span>
                  )}
                  {e.categories && e.categories.length > 0 && (
                    <span className="ml-2 inline-flex gap-1">
                      {e.categories.slice(0, 3).map((c) => (
                        <Badge key={c} variant="outline">
                          {c}
                        </Badge>
                      ))}
                    </span>
                  )}
                </TD>
                <TD className="whitespace-nowrap font-mono text-xs text-ink-600">{e.action}</TD>
                <TD>
                  <Badge variant={sourceVariant(e.source)}>{e.source.replace(/_/g, " ")}</Badge>
                </TD>
                <TD className="font-mono text-xs text-ink-500">
                  {e.actor_id ? e.actor_id.slice(0, 8) : <span className="text-ink-300">system</span>}
                </TD>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
