import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

type Tone = "blue" | "green" | "amber" | "red" | "violet";

const TONE_ICON: Record<Tone, string> = {
  blue: "bg-blue-50 text-blue-600",
  green: "bg-emerald-50 text-emerald-600",
  amber: "bg-amber-50 text-amber-600",
  red: "bg-red-50 text-red-600",
  violet: "bg-violet-50 text-violet-600",
};

export function StatCard({
  title,
  value,
  meta,
  icon: Icon,
  tone = "blue",
  className,
}: {
  title: string;
  value: string | number;
  meta?: string;
  icon: LucideIcon;
  tone?: Tone;
  className?: string;
}) {
  return (
    <div className={cn("rounded-lg bg-white p-5 shadow-sm ring-1 ring-gray-200", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-2 text-2xl font-bold text-gray-900">{value}</p>
          {meta && <p className="mt-2 text-xs leading-5 text-gray-500">{meta}</p>}
        </div>
        <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", TONE_ICON[tone])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}
