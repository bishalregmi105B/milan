"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { adminApi, type AdminUserRow } from "@/lib/admin-api";
import {
  Badge,
  Button,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  Input,
  PageHeader,
  Pagination,
  Table,
  TableSkeleton,
  THead,
  TD,
  statusBadge,
  useToast,
} from "@/components/ui";
import { IconSearch, IconUsers } from "@/components/icons";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUserRow[] | null>(null);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState<number | undefined>(undefined);
  const [query, setQuery] = useState("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [confirmTarget, setConfirmTarget] = useState<AdminUserRow | null>(null);
  const { success, error: toastError } = useToast();

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const body = await adminApi.users(page);
      setUsers(body.users);
      setPages(body.pages || 1);
      setTotal(body.total);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load users.");
    }
  }, [page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function setStatus(u: AdminUserRow, status: string) {
    setBusyId(u.id);
    try {
      await adminApi.setUserStatus(u.id, status);
      success(
        status === "active" ? "User reactivated" : `User ${status}`,
        `${u.phone_masked} is now ${status}.`,
      );
      await load();
    } catch (e) {
      toastError(
        "Couldn't update status",
        e instanceof Error ? e.message : "Please try again.",
      );
    } finally {
      setBusyId(null);
      setConfirmTarget(null);
    }
  }

  const filtered = (users ?? []).filter((u) =>
    query
      ? `${u.phone_masked} ${u.role} ${u.account_status}`.toLowerCase().includes(query.toLowerCase())
      : true,
  );

  return (
    <div>
      <PageHeader
        title="Users"
        description="Every Milan account, newest first. Suspension and reactivation are audited with your actor ID."
        actions={
          <div className="relative">
            <IconSearch
              size={16}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-400"
            />
            <Input
              type="search"
              placeholder="Search phone, role, status…"
              aria-label="Search users"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-9 sm:w-64"
            />
          </div>
        }
      />

      {loadError && (
        <ErrorState
          title="Couldn't load users"
          message={loadError}
          onRetry={() => void load()}
        />
      )}

      {!loadError && !users && <TableSkeleton rows={6} cols={5} />}

      {!loadError && users && filtered.length === 0 && (
        <EmptyState
          icon={<IconUsers size={24} />}
          title={query ? "No users match" : "No users yet"}
          description={
            query
              ? `Nothing matches “${query}”. Clear the search to see all ${total ?? ""} users.`
              : "New accounts appear here as people join Milan."
          }
          action={
            query ? (
              <Button variant="outline" size="sm" onClick={() => setQuery("")}>
                Clear search
              </Button>
            ) : undefined
          }
        />
      )}

      {!loadError && users && filtered.length > 0 && (
        <>
          <Table>
            <THead columns={["Phone", "Verified", "Status", "Role", "Actions"]} />
            <tbody>
              {filtered.map((u) => (
                <tr key={u.id} className="transition-colors hover:bg-paper-100/60">
                  <TD className="whitespace-nowrap">
                    <Link
                      href={`/admin/users/${u.id}`}
                      className="font-mono text-xs tabular-nums text-dhaka-500 underline-offset-2 hover:underline"
                    >
                      {u.phone_masked}
                    </Link>
                  </TD>
                  <TD>
                    {u.is_verified ? (
                      <Badge variant="success">verified</Badge>
                    ) : (
                      <Badge variant="outline">unverified</Badge>
                    )}
                  </TD>
                  <TD>
                    <Badge variant={statusBadge(u.account_status)}>{u.account_status}</Badge>
                  </TD>
                  <TD>
                    {u.role === "user" ? (
                      <span className="text-ink-500">{u.role}</span>
                    ) : (
                      <Badge variant="accent">{u.role}</Badge>
                    )}
                  </TD>
                  <TD className="whitespace-nowrap">
                    <div className="flex justify-end gap-1.5">
                      <Link
                        href={`/admin/users/${u.id}`}
                        className="inline-flex min-h-9 items-center rounded-sm px-3 text-xs font-semibold text-ink-600 transition-colors hover:bg-paper-100 hover:text-ink-900 active:bg-paper-200"
                      >
                        Detail
                      </Link>
                      {u.account_status === "active" ? (
                        <Button
                          size="sm"
                          variant="destructive"
                          loading={busyId === u.id}
                          disabled={busyId !== null}
                          onClick={() => setConfirmTarget(u)}
                        >
                          Suspend
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="outline"
                          loading={busyId === u.id}
                          disabled={busyId !== null}
                          onClick={() => void setStatus(u, "active")}
                        >
                          Reactivate
                        </Button>
                      )}
                    </div>
                  </TD>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pagination page={page} pages={pages} total={total} onChange={setPage} />
        </>
      )}

      <ConfirmDialog
        open={confirmTarget !== null}
        onClose={() => setConfirmTarget(null)}
        onConfirm={() => confirmTarget && void setStatus(confirmTarget, "suspended")}
        title="Suspend this user?"
        description={`${confirmTarget?.phone_masked ?? "This user"} will be signed out and unable to access Milan until reactivated. The action is recorded in the audit log.`}
        confirmLabel="Suspend user"
        destructive
        busy={busyId === confirmTarget?.id}
      />
    </div>
  );
}
