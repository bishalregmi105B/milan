"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi, type CircleRow } from "@/lib/admin-api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  PageHeader,
  Skeleton,
  useToast,
} from "@/components/ui";
import { IconCalendar, IconCircles } from "@/components/icons";

// Manage Circles: feature/unfeature + schedule live audio rooms (doc 6 §2).
export default function AdminCirclesPage() {
  const [circles, setCircles] = useState<CircleRow[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [roomFor, setRoomFor] = useState<CircleRow | null>(null);
  const [roomTitle, setRoomTitle] = useState("");
  const [roomAt, setRoomAt] = useState("");
  const [scheduling, setScheduling] = useState(false);
  const { success, error: toastError } = useToast();

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      setCircles((await adminApi.circles()).circles);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load circles.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleFeature(circle: CircleRow) {
    setBusyId(circle.id);
    try {
      await adminApi.featureCircle(circle.id, !circle.is_featured);
      success(
        circle.is_featured ? "Removed from featured" : "Circle featured",
        `${circle.name} ${circle.is_featured ? "no longer appears in featured shelves." : "now appears in featured shelves."}`,
      );
      await load();
    } catch (e) {
      toastError(
        "Couldn't update circle",
        e instanceof Error ? e.message : "Please try again.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function scheduleRoom(e: React.FormEvent) {
    e.preventDefault();
    if (!roomFor || !roomAt) return;
    setScheduling(true);
    try {
      await adminApi.scheduleRoom(roomFor.id, roomTitle, new Date(roomAt).toISOString());
      success(
        "Room scheduled",
        `“${roomTitle || "Live room"}” in ${roomFor.name} at ${new Date(roomAt).toLocaleString()}.`,
      );
      setRoomFor(null);
      setRoomTitle("");
      setRoomAt("");
    } catch (err) {
      toastError(
        "Couldn't schedule room",
        err instanceof Error ? err.message : "Please try again.",
      );
    } finally {
      setScheduling(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Circles"
        description="Interest communities across Jhalak. Featuring a circle promotes it to the featured shelf; scheduled rooms appear in the circle's room list."
      />

      {loadError && (
        <ErrorState
          title="Couldn't load circles"
          message={loadError}
          onRetry={() => void load()}
        />
      )}

      {!loadError && !circles && (
        <div className="space-y-3" aria-busy="true" aria-label="Loading circles">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-md" />
          ))}
        </div>
      )}

      {!loadError && circles && circles.length === 0 && (
        <EmptyState
          icon={<IconCircles size={24} />}
          title="No circles yet"
          description="Circles appear here once users create them in the app. Featuring and room scheduling unlock from this page."
        />
      )}

      {!loadError && circles && circles.length > 0 && (
        <div className="grid gap-3 lg:grid-cols-2">
          {circles.map((c) => (
            <Card key={c.id} className="flex items-center justify-between gap-4 px-5 py-4">
              <div className="min-w-0">
                <p className="flex items-center gap-2 truncate font-semibold text-ink-900">
                  {c.name}
                  {c.is_featured && (
                    <Badge variant="accent">
                      featured
                    </Badge>
                  )}
                </p>
                <p className="mt-0.5 text-xs text-ink-500">
                  {c.category} · <span className="tabular-nums">{c.member_count}</span> members
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  aria-pressed={c.is_featured}
                  loading={busyId === c.id}
                  disabled={busyId !== null}
                  onClick={() => void toggleFeature(c)}
                >
                  {c.is_featured ? "Unfeature" : "Feature"}
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => setRoomFor(c)}
                  disabled={busyId !== null}
                >
                  <IconCalendar size={14} />
                  Room
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={roomFor !== null}
        onClose={() => setRoomFor(null)}
        title={`New live room — ${roomFor?.name ?? ""}`}
        description="Members of this circle will see the room on its schedule."
        footer={
          <>
            <Button variant="ghost" onClick={() => setRoomFor(null)} disabled={scheduling}>
              Cancel
            </Button>
            <Button type="submit" form="schedule-room-form" loading={scheduling} disabled={!roomAt}>
              Schedule
            </Button>
          </>
        }
      >
        <form id="schedule-room-form" onSubmit={scheduleRoom} className="space-y-4">
          <Field label="Room title" htmlFor="room-title" hint="Optional — defaults to the circle name.">
            <Input
              id="room-title"
              value={roomTitle}
              onChange={(e) => setRoomTitle(e.target.value)}
              placeholder="e.g. Saturday mtg planning"
              maxLength={120}
            />
          </Field>
          <Field label="Scheduled at" htmlFor="room-at" error={!roomAt && scheduling ? "Pick a date and time." : undefined}>
            <Input
              id="room-at"
              type="datetime-local"
              value={roomAt}
              onChange={(e) => setRoomAt(e.target.value)}
              required
            />
          </Field>
        </form>
      </Modal>
    </div>
  );
}
