"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { adminApi, type AnalyticsOverview, type HistoryPoint } from "@/lib/admin-api";
import { Card, CardContent, CardHeader, CardTitle, ErrorState, PageHeader, Skeleton, Stat } from "@/components/ui";

// Chart series colors mirror the brand tokens (marigold / dhaka / pine) —
// hardcoded to the exact token hexes so recharts renders without DOM reads.
const SERIES = { signups: "#F5A623", matches: "#7B1E3A", revenue: "#1F6F54" } as const;
const AXIS_TICK = { fontSize: 11, fill: "#6B6355" } as const;

export default function AdminAnalyticsPage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [series, setSeries] = useState<HistoryPoint[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const [o, h] = await Promise.all([adminApi.analyticsOverview(), adminApi.analyticsHistory()]);
      setOverview(o);
      setSeries(h.series);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load analytics.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loadError) {
    return (
      <div>
        <PageHeader title="Analytics" />
        <ErrorState
          title="Couldn't load analytics"
          message={loadError}
          onRetry={() => void load()}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Analytics"
        description="Platform health at a glance — engagement, matching, and revenue in NPR."
      />

      {!overview ? (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3" aria-busy="true" aria-label="Loading analytics">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-md" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          <Stat label="DAU" value={overview.dau.toLocaleString()} context="Active in the last 24 hours" />
          <Stat label="WAU" value={overview.wau.toLocaleString()} context="Active in the last 7 days" />
          <Stat label="MAU" value={overview.mau.toLocaleString()} context="Active in the last 30 days" />
          <Stat
            label="Matches · 7d"
            value={overview.matches_7d.toLocaleString()}
            context="New connections this week"
            tone="accent"
          />
          <Stat
            label="Match rate · 7d"
            value={`${(overview.match_rate_7d * 100).toFixed(1)}%`}
            context="Matches per swipe pair"
          />
          <Stat
            label="Revenue · total"
            value={`रू ${overview.revenue_npr_total.toLocaleString()}`}
            context="Completed payments, NPR"
            tone="success"
          />
        </div>
      )}

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Last 30 days</CardTitle>
        </CardHeader>
        <CardContent>
          {!series ? (
            <Skeleton className="h-72 w-full" />
          ) : (
            <div style={{ width: "100%", height: 300 }}>
              <ResponsiveContainer>
                <LineChart data={series} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E8E1D3" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={AXIS_TICK}
                    tickFormatter={(d: string) => d.slice(5)}
                    axisLine={{ stroke: "#D9CFBA" }}
                    tickLine={false}
                    minTickGap={24}
                  />
                  <YAxis
                    yAxisId="left"
                    tick={AXIS_TICK}
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                    width={36}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={AXIS_TICK}
                    allowDecimals={false}
                    axisLine={false}
                    tickLine={false}
                    width={44}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#FFFDF9",
                      border: "1px solid #D9CFBA",
                      borderRadius: 8,
                      fontSize: 12,
                      boxShadow: "0 4px 12px rgba(123,30,58,0.1)",
                    }}
                    labelStyle={{ color: "#1F1B16", fontWeight: 600 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="plainline" />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="signups"
                    name="Signups"
                    stroke={SERIES.signups}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                  <Line
                    yAxisId="left"
                    type="monotone"
                    dataKey="matches"
                    name="Matches"
                    stroke={SERIES.matches}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="revenue_npr"
                    name="Revenue NPR"
                    stroke={SERIES.revenue}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
