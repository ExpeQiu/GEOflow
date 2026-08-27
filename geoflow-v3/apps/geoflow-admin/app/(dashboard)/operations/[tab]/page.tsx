"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { DashboardAutomation } from "@/components/admin/DashboardAutomation";
import { QuickStartPanel } from "@/components/admin/DashboardSections";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { ArticlesPanel } from "@/components/operations/ArticlesPanel";
import { DistributionCitationPanel } from "@/components/operations/DistributionCitationPanel";
import { DistributionPanel } from "@/components/operations/DistributionPanel";
import { DistributionSubNav } from "@/components/operations/DistributionSubNav";
import { OperationsOverview } from "@/components/operations/OperationsOverview";
import { AnalyticsPanel } from "@/components/strategy/AnalyticsPanel";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import type { DashboardAutomationPayload } from "@/lib/dashboard-types";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";
import { useRouteParams } from "@/lib/use-route-params";
import type {
  AdminArticle,
  ArticleStats,
  DistributionChannelRow,
  DistributionJobRow,
  DistributionStats,
  OpsStats,
} from "@/lib/operations-types";
import type { AnalyticsSnapshot, MonitorInsight, MonitorSnapshot, TrendPoint } from "@/lib/strategy-types";

export default function OperationsPage({ params }: { params: Promise<{ tab: string }> }) {
  const { tab } = useRouteParams(params);
  const token = useAuthGuard();
  const [stats, setStats] = useState<OpsStats | null>(null);
  const [automation, setAutomation] = useState<DashboardAutomationPayload | null>(null);
  const [articles, setArticles] = useState<AdminArticle[]>([]);
  const [articleStats, setArticleStats] = useState<ArticleStats>({ total: 0, published: 0, draft: 0, pending_review: 0 });
  const [articleFilter, setArticleFilter] = useState<"all" | "pending">("all");
  const [themeFilter, setThemeFilter] = useState("");
  const [distStats, setDistStats] = useState<DistributionStats | null>(null);
  const [channels, setChannels] = useState<DistributionChannelRow[]>([]);
  const [recentJobs, setRecentJobs] = useState<DistributionJobRow[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [importingArticles, setImportingArticles] = useState(false);
  const [flash, setFlash] = useState<{ variant: "success" | "error"; message: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const [analyticsSnap, setAnalyticsSnap] = useState<AnalyticsSnapshot | null>(null);
  const [publicationTrend, setPublicationTrend] = useState<TrendPoint[]>([]);
  const [taskHealth, setTaskHealth] = useState({ running: 0, pending: 0, failed: 0 });
  const [aiUsage, setAiUsage] = useState({ used_today: 0, total_used: 0, active_models: 0 });
  const [topArticles, setTopArticles] = useState<{ id: number; title: string; view_count: number; status: string }[]>([]);
  const [analyticsInsights, setAnalyticsInsights] = useState<MonitorInsight[]>([]);
  const [visibilityTrends, setVisibilityTrends] = useState<MonitorSnapshot[]>([]);
  const [themeAnalytics, setThemeAnalytics] = useState<
    Array<{
      theme_id: number;
      title: string;
      status: string;
      article_count: number;
      gate_pass_rate_pct: number;
      distribution_success_rate_pct: number;
    }>
  >([]);

  const loadOverview = useCallback(async (t: string) => {
    const [ops, dash] = await Promise.all([
      apiGet<{ stats: OpsStats }>("/api/admin/operations/overview", t),
      apiGet<{ automation: DashboardAutomationPayload }>("/api/admin/dashboard", t),
    ]);
    setStats(ops.stats);
    setAutomation(dash.automation);
  }, []);

  const loadArticles = useCallback(
    async (t: string, filter: "all" | "pending", themeId?: string) => {
      const params = new URLSearchParams();
      if (filter === "pending") params.set("review_status", "pending");
      if (themeId) params.set("theme_id", themeId);
      const qs = params.toString() ? `?${params}` : "";
      const data = await apiGet<{ articles: AdminArticle[]; stats: ArticleStats }>(`/api/admin/articles${qs}`, t);
      setArticles(data.articles);
      setArticleStats(data.stats);
    },
    [],
  );

  const loadDistribution = useCallback(async (t: string, themeId?: string) => {
    const qs = themeId ? `?theme_id=${encodeURIComponent(themeId)}` : "";
    const data = await apiGet<{
      stats: DistributionStats;
      channels: DistributionChannelRow[];
      recent_jobs: DistributionJobRow[];
    }>(`/api/admin/distribution${qs}`, t);
    setDistStats(data.stats);
    setChannels(data.channels);
    setRecentJobs(data.recent_jobs);
  }, []);

  const loadAnalytics = useCallback(async (t: string) => {
    const analytics = await apiGet<{
      snapshot: AnalyticsSnapshot;
      publication_trend: TrendPoint[];
      task_health: { running: number; pending: number; failed: number };
      ai_usage: { used_today: number; total_used: number; active_models: number };
      top_articles: { id: number; title: string; view_count: number; status: string }[];
      insights?: MonitorInsight[];
      visibility_trends?: MonitorSnapshot[];
      themes?: Array<{
        theme_id: number;
        title: string;
        status: string;
        article_count: number;
        gate_pass_rate_pct: number;
        distribution_success_rate_pct: number;
      }>;
    }>("/api/admin/strategy/analytics", t);
    setAnalyticsSnap(analytics.snapshot);
    setPublicationTrend(analytics.publication_trend);
    setTaskHealth(analytics.task_health);
    setAiUsage(analytics.ai_usage);
    setTopArticles(analytics.top_articles);
    setAnalyticsInsights(analytics.insights ?? []);
    setVisibilityTrends(analytics.visibility_trends ?? []);
    setThemeAnalytics(analytics.themes ?? []);
  }, []);

  const reload = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setFlash(null);
    try {
      if (tab === "overview") await loadOverview(t);
      else if (tab === "articles") await loadArticles(t, articleFilter, themeFilter || undefined);
      else if (tab === "distribution") await loadDistribution(t, themeFilter || undefined);
      else if (tab === "analytics") await loadAnalytics(t);
    } catch {
      setFlash({ variant: "error", message: "加载失败，请刷新重试" });
    } finally {
      setLoading(false);
    }
  }, [tab, articleFilter, themeFilter, loadOverview, loadArticles, loadDistribution, loadAnalytics]);

  useEffect(() => {
    if (token) reload();
  }, [token, reload]);

  async function runArticleAction(id: number, action: "review" | "publish" | "trash") {
    const t = getToken();
    if (!t) return;
    setBusyId(id);
    try {
      await apiPost(`/api/admin/articles/${id}/${action}`, t);
      setFlash({ variant: "success", message: `文章 #${id} 已更新` });
      await loadArticles(t, articleFilter, themeFilter || undefined);
    } catch {
      setFlash({ variant: "error", message: `文章 #${id} 操作失败` });
    } finally {
      setBusyId(null);
    }
  }

  async function batchTrashArticles(ids: number[]) {
    const t = getToken();
    if (!t || ids.length === 0) return;
    if (!confirm(`确认将 ${ids.length} 篇文章移入回收站？`)) return;
    try {
      const res = await apiPost<{ trashed: number }>("/api/admin/articles/batch/trash", t, { ids });
      setFlash({ variant: "success", message: `已回收 ${res.trashed} 篇` });
      await loadArticles(t, articleFilter, themeFilter || undefined);
    } catch {
      setFlash({ variant: "error", message: "批量回收失败" });
    }
  }

  async function onImportArticles() {
    const t = getToken();
    if (!t) return;
    setImportingArticles(true);
    setFlash(null);
    try {
      const data = await apiPost<
        { stats: ArticleStats; articles: AdminArticle[]; import?: { created: number; updated: number; official_count?: number; geoflow_skipped?: number } }
      >("/api/admin/articles/import-geoweb", t);
      setArticles(data.articles);
      setArticleStats(data.stats);
      const result = data.import;
      setFlash({
        variant: "success",
        message: zh.articles.importSuccess(
          result?.created ?? 0,
          result?.updated ?? 0,
          result?.official_count,
          result?.geoflow_skipped,
        ),
      });
    } catch {
      setFlash({ variant: "error", message: zh.articles.importError });
    } finally {
      setImportingArticles(false);
    }
  }

  async function batchPublishArticles(ids: number[]) {
    const t = getToken();
    if (!t || ids.length === 0) return;
    try {
      const res = await apiPost<{ published: number }>("/api/admin/articles/batch/publish", t, { ids });
      setFlash({ variant: "success", message: `已发布 ${res.published} 篇` });
      await loadArticles(t, articleFilter, themeFilter || undefined);
    } catch {
      setFlash({ variant: "error", message: "批量发布失败" });
    }
  }

  const headerTitle =
    tab === "distribution-citations"
      ? zh.distribution.citationsTitle
      : tab === "analytics"
        ? zh.operations.tabs.analytics
        : zh.operations.hubTitle;
  const headerSubtitle =
    tab === "distribution-citations"
      ? zh.distribution.citationsSubtitle
      : tab === "analytics"
        ? zh.strategy.analytics.subtitle
        : zh.operations.hubSubtitle;

  return (
    <div>
      <HubHeader title={headerTitle} subtitle={headerSubtitle} />
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />

      {flash && <FlashAlert variant={flash.variant === "success" ? "success" : "error"}>{flash.message}</FlashAlert>}
      {loading && !stats && tab === "overview" && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}
      {loading && tab === "analytics" && !analyticsSnap && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {tab === "overview" && (
        <div className="space-y-8">
          {stats && <OperationsOverview stats={stats} />}
          <div className="rounded-lg border border-blue-100 bg-blue-50/50 p-4 text-sm text-blue-900">
            <p className="font-medium">运营复盘</p>
            <p className="mt-1 text-blue-800/80">产量、访问、队列与可见性趋势已统一到「运营数据」。</p>
            <Link href="/operations/analytics" className="mt-2 inline-block font-medium text-blue-700 hover:underline">
              {zh.operations.overview.goAnalytics}
            </Link>
          </div>
          <div className="rounded-lg border border-violet-100 bg-violet-50/50 p-4 text-sm text-violet-900">
            <p className="font-medium">分发任务</p>
            <p className="mt-1 text-violet-800/80">内容生成已迁至「内容生产 → 内容任务」；此处配置文章如何分发到渠道。</p>
            <Link href="/operations/distribution/tasks" className="mt-2 inline-block font-medium text-violet-700 hover:underline">
              去分发任务管理 →
            </Link>
          </div>
          <QuickStartPanel />
          {automation && <DashboardAutomation automation={automation} />}
        </div>
      )}

      {tab === "articles" && (
        <ArticlesPanel
          articles={articles}
          stats={articleStats}
          filter={articleFilter}
          busyId={busyId}
          themeFilter={themeFilter}
          onThemeFilterChange={setThemeFilter}
          onImport={onImportArticles}
          importing={importingArticles}
          onFilterChange={(f) => {
            setArticleFilter(f);
          }}
          onReview={(id) => runArticleAction(id, "review")}
          onPublish={(id) => runArticleAction(id, "publish")}
          onTrash={(id) => runArticleAction(id, "trash")}
          onBatchTrash={batchTrashArticles}
          onBatchPublish={batchPublishArticles}
        />
      )}

      {tab === "distribution" && distStats && (
        <>
          <DistributionSubNav />
          <DistributionPanel stats={distStats} channels={channels} recentJobs={recentJobs} />
        </>
      )}

      {tab === "distribution-citations" && <DistributionCitationPanel />}

      {tab === "analytics" && analyticsSnap && (
        <AnalyticsPanel
          snapshot={analyticsSnap}
          publicationTrend={publicationTrend}
          taskHealth={taskHealth}
          aiUsage={aiUsage}
          topArticles={topArticles}
          insights={analyticsInsights}
          visibilityTrends={visibilityTrends}
          themes={themeAnalytics}
        />
      )}
    </div>
  );
}
