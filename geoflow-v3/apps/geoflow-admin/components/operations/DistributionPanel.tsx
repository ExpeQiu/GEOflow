import Link from "next/link";
import { Plus, RadioTower } from "lucide-react";
import { zh } from "@/lib/i18n/zh";
import type { DistributionChannelRow, DistributionJobRow, DistributionStats } from "@/lib/operations-types";

export function DistributionPanel({
  stats,
  channels,
  recentJobs,
}: {
  stats: DistributionStats;
  channels: DistributionChannelRow[];
  recentJobs: DistributionJobRow[];
}) {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <MiniStat label={zh.distribution.statsTotal} value={stats.total} />
        <MiniStat label={zh.distribution.statsActive} value={stats.active} tone="green" />
        <MiniStat label={zh.distribution.statsPending} value={stats.pending} tone="blue" />
        <MiniStat label={zh.distribution.statsFailed} value={stats.failed} tone="red" />
      </div>

      <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <div className="flex flex-col gap-3 border-b border-gray-200 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-medium text-gray-900">{zh.distribution.channelsTitle}</h2>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/operations/distribution/new"
              className="inline-flex h-9 items-center rounded-lg bg-blue-600 px-3 text-sm font-semibold text-white hover:bg-blue-700"
            >
              <Plus className="mr-2 h-4 w-4" />
              {zh.distribution.createButton}
            </Link>
            <Link
              href="/operations/distribution/tasks"
              className="inline-flex h-9 items-center rounded-lg border border-blue-200 bg-blue-50 px-3 text-sm font-medium text-blue-700 hover:bg-blue-100"
            >
              {zh.distribution.tasksTab}
            </Link>
          </div>
        </div>
        {channels.length === 0 ? (
          <div className="px-6 py-10 text-center text-sm text-gray-500">
            <RadioTower className="mx-auto mb-3 h-10 w-10 text-gray-400" />
            <div className="font-medium text-gray-900">{zh.distribution.emptyChannels}</div>
            <Link href="/operations/distribution/new" className="mt-4 inline-flex text-sm font-medium text-blue-600 hover:text-blue-700">
              {zh.distribution.createButton}
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {[zh.distribution.columnName, zh.distribution.columnType, zh.distribution.columnStatus, zh.distribution.columnQueue].map(
                    (h) => (
                      <th key={h} className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {channels.map((ch) => (
                  <tr key={ch.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      <Link href={`/operations/distribution/${ch.id}`} className="text-blue-700 hover:text-blue-800">{ch.name}</Link>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{ch.channel_type}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className={ch.status === "active" ? "text-green-700" : "text-gray-500"}>{ch.status}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      待处理 {ch.pending} · 失败 {ch.failed} · 已同步 {ch.synced}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-medium text-gray-900">{zh.distribution.jobsTitle}</h2>
          <Link href="/operations/distribution/jobs" className="text-sm font-medium text-blue-600 hover:text-blue-700">查看全部</Link>
        </div>
        {recentJobs.length === 0 ? (
          <div className="px-6 py-8 text-center text-sm text-gray-500">暂无分发记录</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {[zh.distribution.columnArticle, "Theme", "渠道", zh.distribution.columnJobStatus, zh.distribution.columnError].map(
                    (h) => (
                      <th key={h} className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {recentJobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-sm text-gray-900">#{job.article_id}</td>
                    <td className="px-6 py-3 text-sm">
                      {job.theme_id ? (
                        <div>
                          <Link
                            href={`/production/themes?id=${job.theme_id}`}
                            className="text-blue-700 hover:underline"
                          >
                            {job.theme_title || `#${job.theme_id}`}
                          </Link>
                          {job.theme_gate_hint && (
                            <span className="ml-2 inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                              {job.theme_gate_hint}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-6 py-3 text-sm text-gray-600">#{job.channel_id}</td>
                    <td className="px-6 py-3 text-sm">
                      <span className={job.status === "failed" ? "text-red-600" : "text-gray-700"}>{job.status}</span>
                    </td>
                    <td className="max-w-xs truncate px-6 py-3 text-sm text-gray-500">{job.error_message || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function MiniStat({ label, value, tone }: { label: string; value: number; tone?: "green" | "blue" | "red" }) {
  const valueClass =
    tone === "green" ? "text-green-700" : tone === "blue" ? "text-blue-700" : tone === "red" ? "text-red-700" : "text-gray-900";
  return (
    <div className="rounded-lg bg-white p-5 shadow-sm ring-1 ring-gray-200">
      <div className="text-sm font-medium text-gray-500">{label}</div>
      <div className={`mt-2 text-2xl font-semibold ${valueClass}`}>{value}</div>
    </div>
  );
}
