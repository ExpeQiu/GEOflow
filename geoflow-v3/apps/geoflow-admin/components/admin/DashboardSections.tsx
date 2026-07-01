"use client";

import Link from "next/link";
import { Activity, BarChart3, FileText, RadioTower } from "lucide-react";
import { StatCard } from "@/components/admin/StatCard";
import { zh } from "@/lib/i18n/zh";
import type { DashboardPayload } from "@/lib/dashboard-types";

export function DashboardHealthCards({ stats }: { stats: DashboardPayload["stats"] }) {
  return (
    <section className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <StatCard
        title={zh.dashboard.health.taskTitle}
        value={`${stats.running_jobs} / ${stats.total_tasks}`}
        meta={zh.dashboard.health.taskMeta(stats.running_jobs, stats.pending_jobs, stats.failed_jobs)}
        icon={Activity}
        tone={stats.failed_jobs > 0 ? "red" : "amber"}
      />
      <StatCard
        title={zh.dashboard.health.contentTitle}
        value={stats.total_articles}
        meta={zh.dashboard.health.contentMeta(stats.published_articles, stats.draft_articles, stats.pending_review)}
        icon={FileText}
        tone="blue"
      />
      <StatCard
        title={zh.dashboard.health.distributionTitle}
        value={stats.channels_active}
        meta={zh.dashboard.health.distributionMeta(
          stats.channels_active,
          stats.distribution_pending,
          stats.distribution_failed,
        )}
        icon={RadioTower}
        tone={stats.distribution_failed > 0 ? "red" : "green"}
      />
      <StatCard
        title={zh.dashboard.health.feedbackTitle}
        value={stats.today_views}
        meta={zh.dashboard.health.feedbackMeta(stats.today_views, stats.ai_used_today)}
        icon={BarChart3}
        tone="violet"
      />
    </section>
  );
}

export function QuickStartPanel() {
  const materialLinks = [
    { label: zh.dashboard.quickStart.knowledge, href: "/production/knowledge/new", className: "border-orange-100 bg-orange-50 text-orange-700 hover:bg-orange-100" },
    { label: zh.dashboard.quickStart.titles, href: "/production/materials/titles", className: "border-green-100 bg-green-50 text-green-700 hover:bg-green-100" },
    { label: zh.dashboard.quickStart.keywords, href: "/production/materials/keywords", className: "border-blue-100 bg-blue-50 text-blue-700 hover:bg-blue-100" },
    { label: zh.dashboard.quickStart.images, href: "/production/materials/images", className: "border-purple-100 bg-purple-50 text-purple-700 hover:bg-purple-100" },
    { label: zh.dashboard.quickStart.authors, href: "/production/materials/authors", className: "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100" },
  ];

  return (
    <section className="mb-8 overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
      <div className="flex flex-col gap-4 border-b border-gray-100 px-6 py-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-600">{zh.dashboard.quickStart.eyebrow}</p>
          <h2 className="mt-2 text-xl font-semibold text-gray-900">{zh.dashboard.quickStart.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-500">{zh.dashboard.quickStart.subtitle}</p>
        </div>
        <span className="inline-flex w-fit items-center rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
          <span className="mr-2 h-1.5 w-1.5 rounded-full bg-current" />
          {zh.dashboard.quickStart.basicReady}
        </span>
      </div>

      <div className="grid grid-cols-1 divide-y divide-gray-100 lg:grid-cols-3 lg:divide-x lg:divide-y-0">
        <QuickStartStep
          step="1"
          title={zh.dashboard.quickStart.apiTitle}
          desc={zh.dashboard.quickStart.apiDesc}
          action={{ href: "/production/ai_config", label: zh.dashboard.quickStart.apiButton }}
        />
        <div className="px-6 py-5">
          <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">2</div>
          <h3 className="mt-2 text-base font-semibold text-gray-900">{zh.dashboard.quickStart.materialTitle}</h3>
          <p className="mt-2 text-sm leading-6 text-gray-500">{zh.dashboard.quickStart.materialDesc}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {materialLinks.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                className={`rounded-md border px-3 py-1.5 text-xs font-medium transition ${link.className}`}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
        <QuickStartStep
          step="3"
          title={zh.dashboard.quickStart.taskTitle}
          desc={zh.dashboard.quickStart.taskDesc}
          action={{ href: "/operations/tasks/new", label: zh.dashboard.quickStart.taskButton, primary: true }}
        />
      </div>
    </section>
  );
}

function QuickStartStep({
  step,
  title,
  desc,
  action,
}: {
  step: string;
  title: string;
  desc: string;
  action: { href: string; label: string; primary?: boolean };
}) {
  return (
    <div className="px-6 py-5">
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-400">{step}</div>
      <h3 className="mt-2 text-base font-semibold text-gray-900">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-gray-500">{desc}</p>
      <Link
        href={action.href}
        className={
          action.primary
            ? "mt-4 inline-flex h-9 items-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700"
            : "mt-4 inline-flex h-9 items-center rounded-lg border border-gray-300 bg-white px-4 text-sm font-semibold text-gray-700 hover:bg-gray-50"
        }
      >
        {action.label}
      </Link>
    </div>
  );
}
