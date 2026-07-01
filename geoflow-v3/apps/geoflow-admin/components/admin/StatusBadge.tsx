import { cn } from "@/lib/cn";

export type StatusKind = "ready" | "running" | "warning" | "error" | "available";

const LABELS: Record<StatusKind, string> = {
  ready: "已就绪",
  running: "运行中",
  warning: "待处理",
  error: "异常",
  available: "可查看",
};

const STYLES: Record<StatusKind, string> = {
  ready: "bg-emerald-100 text-emerald-700",
  running: "bg-blue-100 text-blue-700",
  warning: "bg-amber-100 text-amber-700",
  error: "bg-red-100 text-red-700",
  available: "bg-violet-100 text-violet-700",
};

export function StatusBadge({ status, className }: { status: StatusKind; className?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", STYLES[status], className)}>
      {LABELS[status]}
    </span>
  );
}
