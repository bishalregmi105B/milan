"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { adminApi, type UserDetail as UserDetailData } from "@/lib/admin-api";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  ErrorState,
  PageHeader,
  Skeleton,
  statusBadge,
} from "@/components/ui";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-2 py-1.5">
      <dt className="w-44 shrink-0 text-xs font-semibold uppercase tracking-wider text-ink-400">
        {label}
      </dt>
      <dd className="text-sm text-ink-600">{children}</dd>
    </div>
  );
}

// User detail: profile + verification history + report counts (doc 6 §2).
export default function AdminUserDetailPage() {
  const [detail, setDetail] = useState<UserDetailData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const params = useParams<{ id: string }>();

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setDetail(await adminApi.userDetail(params.id));
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load this user.");
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loadError) {
    return (
      <div className="max-w-3xl">
        <Link
          href="/admin/users"
          className="text-sm font-medium text-dhaka-500 underline-offset-2 hover:underline"
        >
          ← All users
        </Link>
        <div className="mt-6">
          <ErrorState
            title="Couldn't load this user"
            message={loadError}
            onRetry={() => void load()}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl">
      <Link
        href="/admin/users"
        className="text-sm font-medium text-dhaka-500 underline-offset-2 hover:underline"
      >
        ← All users
      </Link>

      {!detail ? (
        <div className="mt-6 space-y-4">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-64 w-full rounded-md" />
        </div>
      ) : (
        <>
          <PageHeader
            title={detail.profile.display_name ?? "Unnamed user"}
            description={`Joined ${new Date(detail.user.created_at).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })}`}
            actions={
              <Badge variant={statusBadge(detail.user.account_status)}>
                {detail.user.account_status}
              </Badge>
            }
          />

          <Card>
            <CardHeader>
              <CardTitle>Account</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="divide-y divide-line100">
                <Row label="Phone">
                  <span className="font-mono tabular-nums">{detail.user.phone_masked}</span>
                </Row>
                <Row label="Verified">
                  {detail.user.is_verified ? (
                    <Badge variant="success">verified</Badge>
                  ) : (
                    <Badge variant="outline">not verified</Badge>
                  )}
                </Row>
                <Row label="Role">
                  <span className="capitalize">{detail.user.role}</span>
                </Row>
                <Row label="Intent mode">
                  <span className="capitalize">{detail.user.intent_mode}</span>
                </Row>
                <Row label="Photos">
                  <span className="tabular-nums">{detail.profile.photo_count}</span>
                </Row>
                <Row label="Face embedding">
                  {detail.has_face_embedding
                    ? "on file (duplicate-detection only)"
                    : "none"}
                </Row>
                <Row label="Reports filed">
                  <span className="tabular-nums">{detail.reports_filed}</span>
                </Row>
                <Row label="Reports against">
                  <span className="tabular-nums">{detail.reports_against}</span>
                </Row>
              </dl>
            </CardContent>
          </Card>

          {detail.profile.bio && (
            <Card className="mt-5">
              <CardHeader>
                <CardTitle>Bio</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm leading-relaxed text-ink-600">{detail.profile.bio}</p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
