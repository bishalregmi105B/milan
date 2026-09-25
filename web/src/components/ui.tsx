// Milan design-system primitives (doc 6 §4) — built on the warm paper &
// marigold token world in globals.css. Borders-first depth; states for every
// interactive element: default / hover / active / focus-visible / disabled.

import { forwardRef } from "react";
import { IconChevronLeft, IconChevronRight, IconRefresh } from "./icons";

export { ToastProvider, useToast } from "./toast";
export { Modal, ConfirmDialog } from "./modal";

/* ── Button ───────────────────────────────────────────────────────────── */

const buttonVariants = {
  primary:
    "bg-dhaka-500 text-paper-0 hover:bg-dhaka-600 active:bg-dhaka-700",
  secondary:
    "bg-action-500 text-ink-900 hover:bg-action-600 active:bg-action-700",
  outline:
    "border border-line300 bg-transparent text-ink-600 hover:border-line400 hover:bg-paper-100 hover:text-ink-900 active:bg-paper-200",
  ghost:
    "bg-transparent text-ink-600 hover:bg-paper-100 hover:text-ink-900 active:bg-paper-200",
  destructive:
    "bg-milanerror text-paper-0 hover:bg-[#a53026] active:bg-[#8c291f]",
} as const;

const buttonSizes = {
  sm: "min-h-9 px-3 py-1.5 text-xs",
  md: "min-h-10 px-4 py-2 text-sm",
  lg: "min-h-12 px-6 py-3 text-sm",
} as const;

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof buttonVariants;
  size?: keyof typeof buttonSizes;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { className = "", variant = "primary", size = "md", loading = false, disabled, children, ...props },
    ref,
  ) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`inline-flex select-none items-center justify-center gap-2 rounded-sm font-semibold tracking-tight transition-all duration-150 focus-visible:outline-2 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-45 ${buttonSizes[size]} ${buttonVariants[variant]} ${className}`}
      {...props}
    >
      {loading && <Spinner size={14} className="border-current border-t-transparent" />}
      {children}
    </button>
  ),
);
Button.displayName = "Button";

/* ── Form fields ──────────────────────────────────────────────────────── */

const controlClasses =
  "w-full rounded-sm border border-line300 bg-paper-200 px-3 py-2.5 text-sm text-ink-900 transition-[border-color,box-shadow] duration-150 placeholder:text-ink-400 hover:border-line400 focus:border-action-500 focus:bg-paper-0 focus:outline-none focus:ring-[3px] focus:ring-action-500/20 disabled:cursor-not-allowed disabled:opacity-55 aria-[invalid=true]:border-milanerror aria-[invalid=true]:ring-milanerror/15";

export const Input = forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className = "", ...props }, ref) => (
  <input ref={ref} className={`${controlClasses} ${className}`} {...props} />
));
Input.displayName = "Input";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className = "", ...props }, ref) => (
  <textarea ref={ref} className={`${controlClasses} min-h-24 resize-y ${className}`} {...props} />
));
Textarea.displayName = "Textarea";

export const Select = forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className = "", ...props }, ref) => (
  <select
    ref={ref}
    className={`${controlClasses} appearance-none bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%236b6355%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpath%20d%3D%22M6%209l6%206%206-6%22%2F%3E%3C%2Fsvg%3E')] bg-[position:right_0.75rem_center] bg-no-repeat pr-10 ${className}`}
    {...props}
  />
));
Select.displayName = "Select";

/** Field wrapper — label + control + hint/error, wired for a11y. */
export function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
  className = "",
}: {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <label htmlFor={htmlFor} className="text-sm font-semibold text-ink-700">
        {label}
      </label>
      {children}
      {error ? (
        <p id={`${htmlFor}-error`} role="alert" className="text-xs font-medium text-milanerror">
          {error}
        </p>
      ) : hint ? (
        <p id={`${htmlFor}-hint`} className="text-xs text-ink-500">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

/* ── Card family ──────────────────────────────────────────────────────── */

export function Card({
  className = "",
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-md border border-line200 bg-paper-50 shadow-raised ${className}`}
      {...props}
    />
  );
}

export function CardHeader(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div className="px-6 pt-5 pb-2" {...props} />;
}

export function CardTitle(props: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className="font-display text-base font-semibold tracking-tight text-ink-900"
      {...props}
    />
  );
}

export function CardContent(props: React.HTMLAttributes<HTMLDivElement>) {
  return <div className="px-6 pb-5 pt-2" {...props} />;
}

/* ── Badge — semantic + severity mapping ──────────────────────────────── */

const badgeVariants = {
  success: "bg-pine-100 text-pine-700",
  warning: "bg-warning-100 text-warning",
  danger: "bg-milanerror-100 text-milanerror",
  neutral: "bg-paper-200 text-ink-600",
  outline: "border border-line300 text-ink-500",
  accent: "bg-action-100 text-action-700",
} as const;

export type BadgeVariant = keyof typeof badgeVariants;

export function Badge({
  variant = "neutral",
  children,
  className = "",
}: {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold leading-5 ${badgeVariants[variant]} ${className}`}
    >
      {children}
    </span>
  );
}

/** Severity → badge variant, used consistently across queue pages. */
export function severityBadge(severity: string): BadgeVariant {
  switch (severity) {
    case "high":
      return "danger";
    case "low":
      return "warning";
    case "critical":
      return "danger";
    default:
      return "neutral";
  }
}

export function statusBadge(status: string): BadgeVariant {
  switch (status) {
    case "active":
    case "approved":
    case "complete":
      return "success";
    case "suspended":
    case "banned":
    case "rejected":
    case "failed":
      return "danger";
    case "pending":
    case "open":
    case "escalated":
      return "warning";
    default:
      return "neutral";
  }
}

/* ── Data table ───────────────────────────────────────────────────────── */

export function Table({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`overflow-x-auto rounded-md border border-line200 bg-paper-50 shadow-raised ${className}`}>
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  );
}

export function THead({ columns }: { columns: string[] }) {
  return (
    <thead>
      <tr className="border-b border-line300 bg-paper-100/60 text-left">
        {columns.map((c, i) => (
          <th
            key={c || i}
            scope="col"
            className={`px-4 py-3 text-xs font-semibold uppercase tracking-wider text-ink-500 ${i === columns.length - 1 ? "text-right" : ""}`}
          >
            {c}
          </th>
        ))}
      </tr>
    </thead>
  );
}

export function TD({
  className = "",
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={`border-b border-line100 px-4 py-3 align-middle text-ink-600 last:border-0 ${className}`}
      {...props}
    />
  );
}

/* ── Loading ──────────────────────────────────────────────────────────── */

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden="true" className={`skeleton ${className}`} />;
}

export function Spinner({
  size = 20,
  className = "border-marigold-500 border-t-transparent",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={`inline-block shrink-0 rounded-full border-2 ${className}`}
      style={{
        width: size,
        height: size,
        animation: "milan-spin 0.9s linear infinite",
      }}
    />
  );
}

/** Skeleton rows that mirror a table layout. */
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div aria-busy="true" aria-label="Loading content" className="rounded-md border border-line200 bg-paper-50 p-1 shadow-raised">
      <div className="flex gap-4 border-b border-line300 px-4 py-3.5">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex items-center gap-4 border-b border-line100 px-4 py-4 last:border-0">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className={`h-4 flex-1 ${c === 0 ? "max-w-24" : ""}`} />
          ))}
        </div>
      ))}
    </div>
  );
}

/* ── Empty / Error states ─────────────────────────────────────────────── */

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-md border border-dashed border-line300 bg-paper-50 px-6 py-16 text-center">
      {icon && (
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-paper-100 text-ink-400">
          {icon}
        </div>
      )}
      <p className="font-display text-base font-semibold text-ink-900">{title}</p>
      {description && (
        <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-ink-500">{description}</p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center rounded-md border border-milanerror/30 bg-milanerror-100/50 px-6 py-14 text-center"
    >
      <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-milanerror-100 text-milanerror">
        <IconRefresh size={22} />
      </span>
      <p className="font-display text-base font-semibold text-ink-900">{title}</p>
      {message && (
        <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-ink-500">{message}</p>
      )}
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-5" onClick={onRetry}>
          <IconRefresh size={15} />
          Try again
        </Button>
      )}
    </div>
  );
}

/* ── Stat card ────────────────────────────────────────────────────────── */

export function Stat({
  label,
  value,
  context,
  tone = "default",
}: {
  label: string;
  value: string | number;
  context?: string;
  tone?: "default" | "accent" | "success" | "warning" | "danger";
}) {
  const toneClasses = {
    default: "text-ink-900",
    accent: "text-marigold-700",
    success: "text-pine-600",
    warning: "text-warning",
    danger: "text-milanerror",
  } as const;
  return (
    <Card className="p-5">
      <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-500">
        {label}
      </p>
      <p
        className={`mt-2 font-display text-3xl font-bold tracking-tight tabular-nums ${toneClasses[tone]}`}
      >
        {value}
      </p>
      {context && <p className="mt-1 text-xs leading-snug text-ink-400">{context}</p>}
    </Card>
  );
}

/* ── Pagination ───────────────────────────────────────────────────────── */

export function Pagination({
  page,
  pages,
  total,
  onChange,
}: {
  page: number;
  pages: number;
  total?: number;
  onChange: (page: number) => void;
}) {
  if (pages <= 1 && total === undefined) return null;
  return (
    <nav aria-label="Pagination" className="mt-4 flex items-center justify-between text-sm">
      <p className="text-xs text-ink-500">
        Page <span className="font-semibold text-ink-700 tabular-nums">{page}</span> of{" "}
        <span className="tabular-nums">{pages}</span>
        {total !== undefined && (
          <>
            {" · "}
            <span className="tabular-nums">{total}</span> total
          </>
        )}
      </p>
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label="Previous page"
        >
          <IconChevronLeft size={15} />
          Prev
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
          aria-label="Next page"
        >
          Next
          <IconChevronRight size={15} />
        </Button>
      </div>
    </nav>
  );
}

/* ── Avatar — initials fallback ───────────────────────────────────────── */

const avatarPalette = [
  "bg-marigold-100 text-marigold-700",
  "bg-dhaka-100 text-dhaka-700",
  "bg-pine-100 text-pine-700",
  "bg-paper-200 text-ink-600",
] as const;

export function Avatar({
  name,
  size = 40,
  className = "",
}: {
  name: string | null | undefined;
  size?: number;
  className?: string;
}) {
  const initials = (name ?? "?")
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("") || "?";
  const paletteIndex =
    (name ?? "?").split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0) %
    avatarPalette.length;
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 select-none items-center justify-center rounded-full font-display font-semibold ${avatarPalette[paletteIndex]} ${className}`}
      style={{ width: size, height: size, fontSize: size * 0.36 }}
    >
      {initials}
    </span>
  );
}

/* ── Page header pattern ──────────────────────────────────────────────── */

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-ink-900">
          {title}
        </h1>
        {description && (
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ink-500">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2.5">{actions}</div>}
    </div>
  );
}
