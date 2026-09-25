"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi, type SaathiAnalytics as SaathiAnalyticsData } from "@/lib/admin-api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ErrorState,
  PageHeader,
  Skeleton,
  Stat,
} from "@/components/ui";
import { IconAlert } from "@/components/icons";

// Ethics-drift watchtower (doc 6 §2): cap-hit rate is a signal to revisit the
// cap or messaging — NOT an engagement metric to celebrate. Crisis counts are
// aggregate-only; no individual transcript browsing from this view.
export default function SaathiAnalyticsPage() {
  const [data, setData] = useState<SaathiAnalyticsData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setData(await adminApi.saathiAnalytics());
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load Saathi health.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loadError) {
    return (
      <div>
        <PageHeader title="Saathi health" />
        <ErrorState
          title="Couldn't load Saathi health"
          message={loadError}
          onRetry={() => void load()}
        />
      </div>
    );
  }

  const capHitRate = data && data.total_sessions > 0
    ? (data.sessions_hitting_daily_cap_today / data.total_sessions) * 100
    : 0;
  const capConcern = capHitRate > 50;

  return (
    <div>
      <PageHeader
        title="Saathi health"
        description="Watch for the proactive-message daily cap being hit constantly — that is a product/ethics signal, not engagement. Crisis indicators are aggregates only; no transcript is viewable from here."
      />

      {!data ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true" aria-label="Loading Saathi health">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-md" />
          ))}
        </div>
      ) : (
        <>
          {capConcern && (
            <div
              role="alert"
              className="mb-6 flex items-start gap-3 rounded-md border border-warning/40 bg-warning-100 px-4 py-3.5 text-sm text-ink-700"
            >
              <IconAlert size={20} className="mt-0.5 shrink-0 text-warning" />
              <p>
                <strong className="font-semibold">More than half of active sessions hit the daily proactive cap today.</strong>{" "}
                Review whether the cap or the messaging needs adjustment — this is a wellbeing signal, not an engagement win.
              </p>
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Stat
              label="Total sessions"
              value={data.total_sessions.toLocaleString()}
              context="All Saathi conversations ever opened"
            />
            <Stat
              label="Proactive opt-ins"
              value={data.proactive_opt_in_count.toLocaleString()}
              context="Users who asked for daily check-ins"
            />
            <Stat
              label="Paused sessions"
              value={data.paused_count.toLocaleString()}
              context="Users who put Saathi on hold"
            />
            <Stat
              label="Cap hits · today"
              value={data.sessions_hitting_daily_cap_today.toLocaleString()}
              context="Sessions that reached the daily proactive cap"
              tone={capConcern ? "danger" : "default"}
            />
            <Stat
              label="Cap-hit rate · today"
              value={`${capHitRate.toFixed(1)}%`}
              context="Share of active sessions hitting the cap"
              tone={capConcern ? "danger" : "success"}
            />
            <Stat
              label="Crisis-flagged · aggregate"
              value={data.crisis_flagged_sessions_aggregate.toLocaleString()}
              context="Aggregate count only — never individual transcripts"
              tone="warning"
            />
          </div>

          <Card className="mt-8">
            <CardHeader>
              <CardTitle>Reading these numbers</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="list-inside list-disc space-y-1.5 text-sm leading-relaxed text-ink-500">
                <li>A high opt-in rate with a low cap-hit rate is the healthy pattern.</li>
                <li>A consistently high cap-hit rate means the cap or the proactive copy needs revisiting.</li>
                <li>Crisis flags route to the safety runbook — aggregates here are for staffing, not review.</li>
              </ul>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
