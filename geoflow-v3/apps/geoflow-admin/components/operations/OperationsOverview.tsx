import Link from "next/link";
import { zh } from "@/lib/i18n/zh";
import type { OpsStats } from "@/lib/operations-types";

export function OperationsOverview({ stats }: { stats: OpsStats }) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      <OverviewCard
        label={zh.distribution.tasksTab}
        value={stats.distribution_pending}
        meta={zh.operations.overview.distributionPending(stats.distribution_pending)}
        href="/operations/distribution/tasks"
        tone="blue"
      />
      <OverviewCard
        label={zh.operations.tabs.articles}
        value={stats.total_articles}
        meta={zh.operations.overview.pendingReview(stats.pending_review)}
        href="/operations/articles"
        tone="emerald"
      />
      <OverviewCard
        label={zh.operations.tabs.distribution}
        value={stats.channels_active}
        meta={`${zh.operations.overview.channelsTotal} · ${zh.operations.overview.distributionFailed} ${stats.distribution_failed}`}
        href="/operations/distribution"
        tone="violet"
      />
    </div>
  );
}

function OverviewCard({
  label,
  value,
  meta,
  href,
  tone,
}: {
  label: string;
  value: number;
  meta: string;
  href: string;
  tone: "blue" | "emerald" | "violet";
}) {
  const styles = {
    blue: "border-blue-200 bg-blue-50/60 text-blue-700",
    emerald: "border-emerald-200 bg-emerald-50/60 text-emerald-700",
    violet: "border-violet-200 bg-violet-50/60 text-violet-700",
  }[tone];
  const linkColor = {
    blue: "text-blue-800",
    emerald: "text-emerald-800",
    violet: "text-violet-800",
  }[tone];

  return (
    <div className={`rounded-lg border p-5 ${styles}`}>
      <p className="text-xs font-semibold uppercase">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="mt-1 text-xs text-gray-500">{meta}</p>
      <Link href={href} className={`mt-3 inline-block text-sm hover:underline ${linkColor}`}>
        {zh.operations.viewDetail}
      </Link>
    </div>
  );
}
