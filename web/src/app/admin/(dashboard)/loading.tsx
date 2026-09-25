import { Skeleton } from "@/components/ui";

// Route-level loading for the admin dashboard — brand-tinted skeletons that
// mirror the page-header + table layout, never a raw "Loading…" string.
export default function AdminLoading() {
  return (
    <div aria-busy="true" aria-label="Loading page">
      <div className="mb-6 space-y-3">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-80 max-w-full" />
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <Skeleton className="h-24 rounded-md" />
        <Skeleton className="h-24 rounded-md" />
        <Skeleton className="h-24 rounded-md" />
      </div>
      <Skeleton className="mt-6 h-72 w-full rounded-md" />
    </div>
  );
}
