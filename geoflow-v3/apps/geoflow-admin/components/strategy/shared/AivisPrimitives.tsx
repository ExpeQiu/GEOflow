"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";

/** 白色卡片容器，与全站 ring 主题一致 */
export const surfaceCardClass = "rounded-lg bg-white shadow-sm ring-1 ring-gray-200";

/** 表单控件描边 */
export const surfaceInputClass = "rounded-md border border-gray-300 px-3 py-2 text-sm";

const PLATFORM_LABELS: Record<string, string> = {
  doubao: "豆包",
  deepseek: "DeepSeek",
  tongyi: "通义千问",
  yuanbao: "元宝",
  wenxin: "文心一言",
  kimi: "Kimi",
};

export function platformLabel(platform: string) {
  return PLATFORM_LABELS[platform] || platform;
}

export function AivisKpiCard({
  label,
  value,
  sub,
  tone = "violet",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "violet" | "cyan" | "amber";
}) {
  const border = {
    violet: "border-violet-200 bg-violet-50/60",
    cyan: "border-cyan-200 bg-cyan-50/60",
    amber: "border-amber-200 bg-amber-50/60",
  }[tone];
  return (
    <div className={`rounded-lg border p-4 ${border}`}>
      <p className="text-xs font-semibold uppercase text-gray-600">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
      {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
    </div>
  );
}

export function GapPriorityBadge({ priority }: { priority: string }) {
  const cls =
    priority === "high"
      ? "bg-red-100 text-red-700"
      : priority === "medium"
        ? "bg-yellow-100 text-yellow-800"
        : "bg-green-100 text-green-700";
  const label = priority === "high" ? "高优先" : priority === "medium" ? "中优先" : "已覆盖";
  return <span className={`rounded px-2 py-0.5 text-xs ${cls}`}>{label}</span>;
}

export function PlatformBadge({ platform, count }: { platform: string; count?: number }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-violet-200 bg-white px-3 py-1 text-xs text-violet-800">
      {platformLabel(platform)}
      {count != null && <span className="text-gray-400">({count})</span>}
    </span>
  );
}

export function LayerSection({
  title,
  subtitle,
  children,
  collapsible = false,
  defaultCollapsed = false,
  open: openProp,
  onOpenChange,
  badge,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  collapsible?: boolean;
  /** 初始折叠；仅在非受控模式下生效 */
  defaultCollapsed?: boolean;
  /** 受控展开状态 */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  /** 折叠时在标题旁显示的摘要 */
  badge?: string | number;
}) {
  const [internalOpen, setInternalOpen] = useState(!defaultCollapsed);
  const open = openProp ?? internalOpen;

  function setOpen(next: boolean) {
    onOpenChange?.(next);
    if (openProp === undefined) setInternalOpen(next);
  }

  const headerContent = (
    <>
      <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      {subtitle && (open || !collapsible) && <p className="mt-0.5 text-sm text-gray-500">{subtitle}</p>}
    </>
  );

  return (
    <section className={`${surfaceCardClass} p-5`}>
      {collapsible ? (
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          className={`flex w-full items-start justify-between gap-3 text-left ${open ? "mb-4" : ""}`}
        >
          <div className="min-w-0">{headerContent}</div>
          <div className="flex shrink-0 items-center gap-2 pt-0.5">
            {!open && badge != null && (
              <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">{badge}</span>
            )}
            <ChevronDown
              className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${open ? "rotate-0" : "-rotate-90"}`}
            />
          </div>
        </button>
      ) : (
        <div className="mb-4">{headerContent}</div>
      )}
      {(!collapsible || open) && children}
    </section>
  );
}
