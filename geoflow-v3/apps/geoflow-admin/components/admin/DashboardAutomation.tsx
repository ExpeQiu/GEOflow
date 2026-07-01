"use client";

import Link from "next/link";
import {
  Activity,
  BadgeCheck,
  BarChart3,
  ChartNoAxesCombined,
  Cpu,
  Database,
  DatabaseZap,
  FilePlus2,
  FileText,
  ListChecks,
  MessageSquareText,
  PlusCircle,
  RadioTower,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  TriangleAlert,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { StatusBadge, type StatusKind } from "@/components/admin/StatusBadge";
import { cn } from "@/lib/cn";
import type { DashboardAutomationPayload } from "@/lib/dashboard-types";
import { zh } from "@/lib/i18n/zh";

const ICONS: Record<string, LucideIcon> = {
  cpu: Cpu,
  database: Database,
  "message-square-text": MessageSquareText,
  workflow: Workflow,
  "file-plus-2": FilePlus2,
  "badge-check": BadgeCheck,
  "shield-check": ShieldCheck,
  "radio-tower": RadioTower,
  "bar-chart-3": BarChart3,
  "chart-no-axes-combined": ChartNoAxesCombined,
  "shield-alert": ShieldAlert,
  "triangle-alert": TriangleAlert,
  "database-zap": DatabaseZap,
  activity: Activity,
  "file-text": FileText,
  "plus-circle": PlusCircle,
  "list-checks": ListChecks,
};

const TONE_STYLES: Record<string, string> = {
  blue: "bg-blue-100 text-blue-700",
  green: "bg-emerald-100 text-emerald-700",
  violet: "bg-violet-100 text-violet-700",
  amber: "bg-amber-100 text-amber-700",
  cyan: "bg-cyan-100 text-cyan-700",
  red: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<StatusKind, string> = {
  ready: zh.dashboard.automation.status.ready,
  running: zh.dashboard.automation.status.running,
  warning: zh.dashboard.automation.status.warning,
  error: zh.dashboard.automation.status.error,
  available: zh.dashboard.automation.status.available,
};

const STATUS_STYLES: Record<StatusKind, string> = {
  ready: "bg-emerald-100 text-emerald-700",
  running: "bg-blue-100 text-blue-700",
  warning: "bg-amber-100 text-amber-700",
  error: "bg-red-100 text-red-700",
  available: "bg-violet-100 text-violet-700",
};

const LANE_TITLES: Record<string, string> = {
  single: zh.dashboard.lanes.singleTitle,
  multi: zh.dashboard.lanes.multiTitle,
  feedback: zh.dashboard.lanes.feedbackTitle,
};

const LANE_DESCS: Record<string, string> = {
  single: zh.dashboard.lanes.singleDesc,
  multi: zh.dashboard.lanes.multiDesc,
  feedback: zh.dashboard.lanes.feedbackDesc,
};

export function DashboardAutomation({ automation }: { automation: DashboardAutomationPayload }) {
  return (
    <section className="mb-8 overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
      <div className="flex flex-col gap-4 border-b border-gray-100 px-6 py-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{zh.dashboard.automation.title}</h2>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-gray-500">{zh.dashboard.automation.desc}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {automation.running_badge_count > 0 && (
            <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700">
              <span className="mr-2 h-1.5 w-1.5 rounded-full bg-current" />
              {zh.dashboard.automation.runningBadge(automation.running_badge_count)}
            </span>
          )}
          {automation.attention_badge_count > 0 && (
            <span className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
              <span className="mr-2 h-1.5 w-1.5 rounded-full bg-current" />
              {zh.dashboard.automation.attentionBadge(automation.attention_badge_count)}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 p-5 2xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-w-0">
          <div className="mb-5 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h3 className="text-base font-semibold text-gray-900">{zh.dashboard.automation.flowTitle}</h3>
              <p className="mt-1 text-sm leading-6 text-gray-500">{zh.dashboard.automation.flowDesc}</p>
            </div>
            <Link
              href="/settings/site"
              className="inline-flex h-9 w-fit items-center rounded-lg border border-gray-300 bg-white px-3 text-sm font-semibold text-gray-700 hover:bg-gray-50"
            >
              <Settings2 className="mr-2 h-4 w-4" />
              {zh.dashboard.automation.settingsLink}
            </Link>
          </div>

          <div className="relative grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="pointer-events-none absolute left-[8%] right-[8%] top-[42px] hidden h-0.5 bg-gradient-to-r from-blue-200 via-emerald-200 to-red-200 xl:block" />
            {automation.flow_nodes.map((node) => {
              const Icon = ICONS[node.icon] ?? Cpu;
              const status = node.status as StatusKind;
              return (
                <article key={node.key} className="relative z-10 flex min-h-[178px] flex-col rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <div className={cn("flex h-10 w-10 shrink-0 items-center justify-center rounded-lg", TONE_STYLES[node.tone] ?? "bg-slate-100 text-slate-700")}>
                      <Icon className="h-5 w-5" />
                    </div>
                    <span className={cn("inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold", STATUS_STYLES[status])}>
                      <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-current" />
                      {STATUS_LABELS[status]}
                    </span>
                  </div>
                  <h3 className="mt-4 text-base font-semibold text-gray-900">{node.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-gray-500">{node.desc}</p>
                  <div className="mt-auto flex flex-wrap gap-2 pt-4">
                    {node.metrics.map((metric) => (
                      <span key={metric} className="rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs font-semibold text-gray-600">
                        {metric}
                      </span>
                    ))}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {node.actions.map((action) => (
                      <Link
                        key={`${node.key}-${action.label}`}
                        href={action.href}
                        className={cn(
                          "inline-flex h-8 items-center rounded-lg px-3 text-xs font-semibold",
                          action.primary
                            ? "bg-blue-600 text-white hover:bg-blue-700"
                            : action.warning
                              ? "border border-orange-200 bg-orange-50 text-orange-700 hover:bg-orange-100"
                              : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50",
                        )}
                      >
                        {action.label}
                      </Link>
                    ))}
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <aside className="flex flex-col gap-3">
          <div>
            <h3 className="text-base font-semibold text-gray-900">{zh.dashboard.automation.recommendationsTitle}</h3>
            <p className="mt-1 text-sm leading-6 text-gray-500">{zh.dashboard.automation.recommendationsDesc}</p>
          </div>
          {automation.recommendations.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 p-4 text-sm text-gray-500">
              {zh.dashboard.automation.recommendationsEmpty}
            </div>
          ) : (
            automation.recommendations.map((rec) => {
              const Icon = ICONS[rec.icon] ?? TriangleAlert;
              return (
                <div key={rec.title} className={cn("rounded-lg border p-4", rec.style)}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/80">
                        <Icon className="h-4 w-4 text-gray-700" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{rec.title}</p>
                        <p className="mt-1 text-xs leading-5 text-gray-600">{rec.desc}</p>
                      </div>
                    </div>
                    <StatusBadge status={rec.badge as StatusKind} />
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span className="text-lg font-bold text-gray-900">{rec.count}</span>
                    <Link
                      href={rec.href}
                      className="inline-flex h-8 items-center rounded-lg border border-gray-300 bg-white px-3 text-xs font-semibold text-gray-700 hover:bg-gray-50"
                    >
                      {rec.button}
                    </Link>
                  </div>
                </div>
              );
            })
          )}
        </aside>
      </div>
    </section>
  );
}

export function DashboardNavigationLanes({ lanes }: { lanes: DashboardAutomationPayload["lanes"] }) {
  return (
    <section className="mb-8 grid grid-cols-1 gap-4 xl:grid-cols-3">
      {lanes.map((lane) => (
        <div key={lane.title_key} className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="text-base font-semibold text-gray-900">{LANE_TITLES[lane.title_key] ?? lane.title_key}</h3>
          <p className="mt-1 text-sm text-gray-500">{LANE_DESCS[lane.title_key] ?? ""}</p>
          <div className="mt-4 space-y-2">
            {lane.rows.map((row) => {
              const Icon = ICONS[row.icon] ?? FileText;
              return (
                <Link
                  key={`${lane.title_key}-${row.title}`}
                  href={row.href}
                  className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 px-3 py-2.5 transition hover:border-gray-200 hover:bg-white"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-white text-gray-600 ring-1 ring-gray-200">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{row.title}</p>
                      <p className="text-xs text-gray-500">{row.desc}</p>
                    </div>
                  </div>
                  <span className="text-sm font-bold text-gray-700">{row.count}</span>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </section>
  );
}
