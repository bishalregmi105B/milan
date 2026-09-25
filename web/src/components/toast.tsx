"use client";

// Toast system — context provider + useToast hook.
// Success/info auto-dismiss after 5s; errors persist until dismissed
// (per component-patterns reference) but the stack is capped.
// aria-live="polite" for success/info, "assertive" for errors.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { IconAlert, IconCheckCircle, IconClose, IconInfo } from "./icons";

type ToastKind = "success" | "error" | "info";

interface Toast {
  id: number;
  kind: ToastKind;
  title: string;
  description?: string;
}

interface ToastContextValue {
  toast: (kind: ToastKind, title: string, description?: string) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const MAX_STACK = 3;
const AUTO_DISMISS_MS = 5000;

const kindStyles: Record<ToastKind, string> = {
  success: "border-pine-200",
  error: "border-milanerror/40",
  info: "border-line300",
};

const kindIcons: Record<ToastKind, typeof IconInfo> = {
  success: IconCheckCircle,
  error: IconAlert,
  info: IconInfo,
};

const kindIconColors: Record<ToastKind, string> = {
  success: "text-pine-500",
  error: "text-milanerror",
  info: "text-marigold-600",
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const toast = useCallback(
    (kind: ToastKind, title: string, description?: string) => {
      const id = nextId.current++;
      setToasts((prev) => [...prev.slice(-(MAX_STACK - 1)), { id, kind, title, description }]);
      // Errors persist until dismissed so failures are never missed.
      if (kind !== "error") {
        timers.current.set(
          id,
          setTimeout(() => dismiss(id), AUTO_DISMISS_MS),
        );
      }
    },
    [dismiss],
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      toast,
      success: (title, description) => toast("success", title, description),
      error: (title, description) => toast("error", title, description),
      info: (title, description) => toast("info", title, description),
    }),
    [toast],
  );

  useEffect(() => {
    const pending = timers.current;
    return () => {
      pending.forEach((timer) => clearTimeout(timer));
      pending.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        aria-label="Notifications"
        className="fixed bottom-4 right-4 z-[80] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2"
      >
        {toasts.map((t) => (
          <ToastCard key={t.id} toast={t} onDismiss={() => dismiss(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastCard({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const ToastIcon = kindIcons[toast.kind];
  return (
    <div
      role={toast.kind === "error" ? "alert" : "status"}
      aria-live={toast.kind === "error" ? "assertive" : "polite"}
      className={`pointer-events-auto flex items-start gap-3 rounded-md border bg-paper-50 p-3.5 shadow-floating ${kindStyles[toast.kind]}`}
      style={{ animation: "milan-toast-in 200ms var(--ease-out-milan)" }}
    >
      <ToastIcon size={20} className={`mt-0.5 shrink-0 ${kindIconColors[toast.kind]}`} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-ink-900">{toast.title}</p>
        {toast.description && (
          <p className="mt-0.5 text-xs leading-relaxed text-ink-500">{toast.description}</p>
        )}
      </div>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="-m-1.5 shrink-0 rounded-sm p-1.5 text-ink-400 transition-colors hover:bg-paper-100 hover:text-ink-700"
      >
        <IconClose size={16} />
      </button>
    </div>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
}
