"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ExternalLink, RefreshCw, X } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import type {
  ArticleCitationDetail,
  DistributedArticleCitation,
  DistributionCitationOverview,
} from "@/lib/operations-types";

type StatusFilter = "all" | "indexed" | "not_indexed" | "pending_scan";

function resolveLoadError(err: unknown): string {
  const message = err instanceof Error ? err.message : "";
  if (message.includes("404")) return zh.distributionCitations.apiNotReady;
  if (message.includes("401") || message.includes("403")) return zh.distributionCitations.apiUnauthorized;
  return zh.distributionCitations.loadError;
}

const STATUS_STYLES: Record<string, string> = {
  indexed: "bg-emerald-100 text-emerald-800",
  not_indexed: "bg-red-100 text-red-800",
  pending_scan: "bg-amber-100 text-amber-800",
  not_distributed: "bg-gray-100 text-gray-600",
};

function formatDelta(delta: number | null | undefined): string | null {
  if (delta == null || Number.isNaN(delta)) return null;
  if (delta === 0) return "0";
  return delta > 0 ? `+${delta}` : `${delta}`;
}

export function DistributionCitationPanel() {
  const [overview, setOverview] = useState<DistributionCitationOverview | null>(null);
  const [articles, setArticles] = useState<DistributedArticleCitation[]>([]);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [detail, setDetail] = useState<ArticleCitationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [ovResult, listResult] = await Promise.allSettled([
        apiGet<DistributionCitationOverview>("/api/admin/distribution/citations/overview?days=7", token),
        apiGet<{ articles: DistributedArticleCitation[] }>(
          `/api/admin/distribution/citations/articles?status=${filter}`,
          token,
        ),
      ]);

      if (ovResult.status === "fulfilled") {
        setOverview(ovResult.value);
      }
      if (listResult.status === "fulfilled") {
        setArticles(listResult.value.articles);
      }

      const failed = [ovResult, listResult].find((r) => r.status === "rejected");
      if (failed?.status === "rejected") {
        setError(resolveLoadError(failed.reason));
      } else {
        setError(null);
      }
    } catch (err) {
      setError(resolveLoadError(err));
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRefresh() {
    const token = getToken();
    if (!token) return;
    setRefreshing(true);
    setError(null);
    try {
      await apiPost("/api/admin/distribution/citations/refresh", token);
      await load();
    } catch {
      setError(zh.distributionCitations.loadError);
    } finally {
      setRefreshing(false);
    }
  }

  async function openDetail(articleId: number) {
    const token = getToken();
    if (!token) return;
    setDetailLoading(true);
    try {
      const data = await apiGet<ArticleCitationDetail>(
        `/api/admin/distribution/citations/articles/${articleId}`,
        token,
      );
      if (data.status === "not_found") {
        setError("文章不存在");
        return;
      }
      setDetail(data);
    } catch (err) {
      setError(resolveLoadError(err));
    } finally {
      setDetailLoading(false);
    }
  }

  if (loading && !overview) {
    return <FlashAlert variant="info">{zh.common.loading}</FlashAlert>;
  }

  if (error && !overview && articles.length === 0) {
    return <FlashAlert variant="error">{error}</FlashAlert>;
  }

  const kpis = overview?.kpis;
  const deltas = overview?.kpis_delta ?? {};
  const maxDomain = Math.max(...(overview?.domain_chart.map((d) => d.count) ?? [1]), 1);
  const notIndexedAlert = overview?.alerts?.find((a) => a.type === "distribution_not_indexed");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm text-gray-500">
          {overview?.last_refreshed_at
            ? zh.distributionCitations.lastRefreshed(
                new Date(overview.last_refreshed_at).toLocaleString("zh-CN"),
              )
            : overview?.cache_ready
              ? zh.distributionCitations.periodLabel
              : "尚未生成匹配缓存，可手动刷新或运行监测扫描"}
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? zh.distributionCitations.refreshing : zh.distributionCitations.refresh}
        </button>
      </div>

      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {!overview?.has_probe_data && (
        <FlashAlert variant="info">{zh.distributionCitations.noProbeData}</FlashAlert>
      )}
      <p className="text-xs text-gray-500">
        证据口径：L1 = open_api 答文抽链；L2 = C 端「相关资料」块（cend_ui）。corpus 伪引用为 L0，不计入可信索引。
      </p>

      {notIndexedAlert && (
        <div className="flex flex-col gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-2 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{zh.distributionCitations.notIndexedAlert(notIndexedAlert.count ?? kpis?.not_indexed_count ?? 0)}</span>
          </div>
          <button
            type="button"
            onClick={() => setFilter("not_indexed")}
            className="text-sm font-medium text-amber-800 hover:underline"
          >
            {zh.distributionCitations.goNotIndexed}
          </button>
        </div>
      )}

      {kpis && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <KpiCard
            label={zh.distributionCitations.kpis.monitoredQuestions}
            value={String(kpis.monitored_questions)}
            delta={formatDelta(deltas.monitored_questions)}
          />
          <KpiCard
            label={zh.distributionCitations.kpis.visibility}
            value={`${kpis.visibility_pct}%`}
            delta={formatDelta(deltas.visibility_pct)}
            suffix="%"
          />
          <KpiCard
            label={zh.distributionCitations.kpis.citationSources}
            value={String(kpis.citation_source_count)}
            delta={formatDelta(deltas.citation_source_count)}
          />
          <KpiCard
            label={zh.distributionCitations.kpis.articleCited}
            value={String(kpis.article_cited_count)}
            delta={formatDelta(deltas.article_cited_count)}
          />
          <KpiCard
            label={zh.distributionCitations.kpis.positiveRate}
            value={kpis.positive_rate_pct != null ? `${kpis.positive_rate_pct}%` : "—"}
            delta={formatDelta(deltas.positive_rate_pct)}
            suffix="%"
          />
          <KpiCard
            label={zh.distributionCitations.kpis.negativeRate}
            value={kpis.negative_rate_pct != null ? `${kpis.negative_rate_pct}%` : "—"}
            delta={formatDelta(deltas.negative_rate_pct)}
            suffix="%"
            invertDelta
          />
        </div>
      )}

      {overview && (
        <div className="grid gap-4 lg:grid-cols-3">
          <section className="rounded-lg bg-white p-5 shadow-sm ring-1 ring-gray-200 lg:col-span-1">
            <h3 className="text-sm font-semibold text-gray-900">{zh.distributionCitations.contribution.title}</h3>
            <dl className="mt-4 space-y-3 text-sm">
              <Row label={zh.distributionCitations.contribution.citedArticles} value={overview.contribution.cited_articles} />
              <Row label={zh.distributionCitations.contribution.citationSources} value={overview.contribution.citation_sources} />
              <Row label={zh.distributionCitations.contribution.platformCoverage} value={overview.contribution.platform_coverage} />
            </dl>
          </section>

          <section className="rounded-lg bg-white p-5 shadow-sm ring-1 ring-gray-200 lg:col-span-2">
            <h3 className="mb-4 text-sm font-semibold text-gray-900">{zh.distributionCitations.domainChart}</h3>
            {overview.domain_chart.length === 0 ? (
              <p className="text-sm text-gray-500">暂无引用来源数据</p>
            ) : (
              <div className="space-y-2">
                {overview.domain_chart.map((item) => (
                  <div key={item.domain} className="flex items-center gap-3 text-sm">
                    <span className="w-36 shrink-0 truncate text-gray-600" title={item.domain}>
                      {item.domain}
                    </span>
                    <div className="h-5 flex-1 rounded bg-gray-100">
                      <div
                        className="h-5 rounded bg-blue-500"
                        style={{ width: `${Math.max(4, (item.count / maxDomain) * 100)}%` }}
                      />
                    </div>
                    <span className="w-10 text-right text-gray-700">{item.count}</span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}

      <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <div className="flex flex-col gap-3 border-b border-gray-200 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-lg font-medium text-gray-900">{zh.distributionCitations.tableTitle}</h2>
          <div className="flex flex-wrap gap-2">
            {(["all", "indexed", "not_indexed", "pending_scan"] as StatusFilter[]).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setFilter(key)}
                className={`rounded-md px-3 py-1.5 text-sm ${
                  filter === key ? "bg-blue-100 text-blue-800" : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                {zh.distributionCitations.filters[key]}
              </button>
            ))}
          </div>
        </div>

        {articles.length === 0 ? (
          <div className="px-6 py-10 text-center text-sm text-gray-500">{zh.distributionCitations.empty}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {[
                    zh.distributionCitations.columns.article,
                    zh.distributionCitations.columns.sceneQuestions,
                    zh.distributionCitations.columns.citations,
                    zh.distributionCitations.columns.platforms,
                    zh.distributionCitations.columns.status,
                    zh.distributionCitations.columns.action,
                  ].map((h) => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-medium uppercase text-gray-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {articles.map((row) => (
                  <tr key={row.article_id} className="hover:bg-gray-50">
                    <td className="max-w-xs px-6 py-4">
                      <div className="line-clamp-2 text-sm font-medium text-gray-900">{row.title}</div>
                      {row.primary_url && (
                        <a
                          href={row.primary_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-1 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
                        >
                          <ExternalLink className="h-3 w-3" />
                          <span className="truncate">{row.primary_url}</span>
                        </a>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-700">{row.scene_question_count}</td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{row.citation_count}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {row.platform_labels.length > 0 ? row.platform_labels.join("、") : "—"}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <StatusBadge status={row.index_status} />
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        type="button"
                        onClick={() => openDetail(row.article_id)}
                        className="font-medium text-blue-600 hover:text-blue-800"
                        disabled={detailLoading}
                      >
                        {zh.distributionCitations.view}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {detail && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center">
          <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white shadow-xl">
            <div className="sticky top-0 flex items-start justify-between border-b border-gray-200 bg-white px-6 py-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{zh.distributionCitations.detailTitle}</h3>
                <p className="mt-1 text-sm text-gray-600">{detail.article.title}</p>
              </div>
              <button type="button" onClick={() => setDetail(null)} className="rounded p-1 text-gray-500 hover:bg-gray-100">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="space-y-4 px-6 py-4">
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={detail.index_status} />
                <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-xs text-violet-800">
                  {detail.stats.citation_count} 次引用
                </span>
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-700">
                  {detail.stats.scene_question_count} 个场景问题
                </span>
              </div>

              {detail.distributions.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-900">分发渠道</h4>
                  <ul className="mt-2 space-y-2 text-sm text-gray-600">
                    {detail.distributions.map((d) => (
                      <li key={d.distribution_id} className="rounded-md bg-gray-50 px-3 py-2">
                        <span className="font-medium text-gray-800">{d.channel_name}</span>
                        {d.remote_url && (
                          <a
                            href={d.remote_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="ml-2 text-blue-600 hover:underline"
                          >
                            {d.remote_url}
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {(detail.citations?.length ?? 0) > 0 ? (
                <div>
                  <h4 className="text-sm font-medium text-gray-900">匹配引用</h4>
                  <ul className="mt-2 space-y-2">
                    {detail.citations?.map((c) => (
                      <li key={c.id} className="rounded-md border border-gray-200 px-3 py-2 text-sm">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-700">{c.platform_label}</span>
                          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                            {zh.distributionCitations.matchType[c.match_type as keyof typeof zh.distributionCitations.matchType] ??
                              c.match_type}
                          </span>
                        </div>
                        <a
                          href={c.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-1 block font-medium text-violet-700 hover:underline"
                        >
                          {c.title || c.url}
                        </a>
                        {c.question_text && <p className="mt-1 text-xs text-gray-500">场景问题：{c.question_text}</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-sm text-gray-500">暂无匹配的 AI 引用记录</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function KpiCard({
  label,
  value,
  delta,
  suffix,
  invertDelta,
}: {
  label: string;
  value: string;
  delta?: string | null;
  suffix?: string;
  invertDelta?: boolean;
}) {
  const deltaNum = delta != null ? parseFloat(delta) : null;
  const positive = deltaNum != null && (invertDelta ? deltaNum < 0 : deltaNum > 0);
  const negative = deltaNum != null && (invertDelta ? deltaNum > 0 : deltaNum < 0);

  return (
    <div className="rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
      <div className="text-xs font-medium text-gray-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-gray-900">{value}</div>
      {delta != null && (
        <div
          className={`mt-1 text-xs ${
            positive ? "text-emerald-600" : negative ? "text-red-600" : "text-gray-500"
          }`}
        >
          {zh.distributionCitations.wowLabel} {delta}
          {suffix ?? ""}
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-gray-500">{label}</dt>
      <dd className="font-semibold text-gray-900">{value}</dd>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const label = zh.distributionCitations.status[status as keyof typeof zh.distributionCitations.status] ?? status;
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_STYLES[status] ?? STATUS_STYLES.not_distributed}`}
    >
      {label}
    </span>
  );
}
