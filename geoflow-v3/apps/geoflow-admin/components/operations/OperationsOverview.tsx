import Link from "next/link";
import { zh } from "@/lib/i18n/zh";
import type { OpsStats } from "@/lib/operations-types";

export function OperationsOverview({ stats }: { stats: OpsStats }) {
  return (
    <>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <OverviewCard
          label={zh.operations.tabs.tasks}
          value={stats.total_tasks}
          meta={zh.operations.overview.activeTasks(stats.active_tasks)}
          href="/operations/tasks"
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
          meta={zh.operations.overview.distributionPending(stats.distribution_pending)}
          href="/operations/distribution"
          tone="violet"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-900">{zh.operations.overview.queueHealth}</h2>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <Metric label={zh.operations.overview.runningJobs} value={stats.running_jobs} />
            <Metric label={zh.operations.overview.pendingJobs} value={stats.pending_jobs} />
            <Metric label={zh.operations.overview.failedJobs} value={stats.failed_jobs} tone="red" />
            <Metric label={zh.operations.overview.publishedArticles} value={stats.published_articles} />
          </dl>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-gray-900">{zh.operations.overview.distributionHealth}</h2>
          <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
            <Metric label={zh.operations.overview.channelsTotal} value={stats.channels_total} />
            <Metric label={zh.operations.overview.distributionFailed} value={stats.distribution_failed} tone="red" />
          </dl>
          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              href="/operations/tasks"
              className="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              {zh.dashboard.newTask}
            </Link>
            <Link
              href="/operations/distribution"
              className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {zh.operations.tabs.distribution}
            </Link>
          </div>
        </div>
      </div>
    </>
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

function Metric({ label, value, tone }: { label: string; value: number; tone?: "red" }) {
  return (
    <div>
      <dt className="text-gray-500">{label}</dt>
      <dd className={`mt-1 text-xl font-semibold ${tone === "red" ? "text-red-600" : "text-gray-900"}`}>{value}</dd>
    </div>
  );
}
