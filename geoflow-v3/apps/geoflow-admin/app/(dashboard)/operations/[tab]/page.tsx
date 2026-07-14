"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
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
import { TasksPanel } from "@/components/operations/TasksPanel";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { useTaskWebSocket } from "@/hooks/use-task-websocket";
import { apiDelete, apiGet, apiPost, getToken } from "@/lib/api-client";
import type { DashboardAutomationPayload } from "@/lib/dashboard-types";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_NAV } from "@/lib/nav-config";
import type {
  AdminArticle,
  AdminTask,
  ArticleStats,
  DistributionChannelRow,
  DistributionJobRow,
  DistributionStats,
  OpsStats,
} from "@/lib/operations-types";

export default function OperationsPage() {
  const { tab } = useParams<{ tab: string }>();
  const token = useAuthGuard();
  const [stats, setStats] = useState<OpsStats | null>(null);
  const [automation, setAutomation] = useState<DashboardAutomationPayload | null>(null);
  const [tasks, setTasks] = useState<AdminTask[]>([]);
  const [articles, setArticles] = useState<AdminArticle[]>([]);
  const [articleStats, setArticleStats] = useState<ArticleStats>({ total: 0, published: 0, draft: 0, pending_review: 0 });
  const [articleFilter, setArticleFilter] = useState<"all" | "pending">("all");
  const [distStats, setDistStats] = useState<DistributionStats | null>(null);
  const [channels, setChannels] = useState<DistributionChannelRow[]>([]);
  const [recentJobs, setRecentJobs] = useState<DistributionJobRow[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [flash, setFlash] = useState<{ variant: "success" | "error"; message: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const loadOverview = useCallback(async (t: string) => {
    const [ops, dash] = await Promise.all([
      apiGet<{ stats: OpsStats }>("/api/admin/operations/overview", t),
      apiGet<{ automation: DashboardAutomationPayload }>("/api/admin/dashboard", t),
    ]);
    setStats(ops.stats);
    setAutomation(dash.automation);
  }, []);

  const loadTasks = useCallback(async (t: string) => {
    const data = await apiGet<{ tasks: AdminTask[]; stats: OpsStats }>("/api/admin/tasks", t);
    setTasks(data.tasks);
    setStats(data.stats);
  }, []);

  const loadArticles = useCallback(
    async (t: string, filter: "all" | "pending") => {
      const qs = filter === "pending" ? "?review_status=pending" : "";
      const data = await apiGet<{ articles: AdminArticle[]; stats: ArticleStats }>(`/api/admin/articles${qs}`, t);
      setArticles(data.articles);
      setArticleStats(data.stats);
    },
    [],
  );

  const loadDistribution = useCallback(async (t: string) => {
    const data = await apiGet<{
      stats: DistributionStats;
      channels: DistributionChannelRow[];
      recent_jobs: DistributionJobRow[];
    }>("/api/admin/distribution", t);
    setDistStats(data.stats);
    setChannels(data.channels);
    setRecentJobs(data.recent_jobs);
  }, []);

  const reload = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setFlash(null);
    try {
      if (tab === "overview") await loadOverview(t);
      else if (tab === "tasks") await loadTasks(t);
      else if (tab === "articles") await loadArticles(t, articleFilter);
      else if (tab === "distribution") await loadDistribution(t);
    } catch {
      setFlash({ variant: "error", message: "加载失败，请刷新重试" });
    } finally {
      setLoading(false);
    }
  }, [tab, articleFilter, loadOverview, loadTasks, loadArticles, loadDistribution]);

  useEffect(() => {
    if (token) reload();
  }, [token, reload]);

  useTaskWebSocket(() => {
    const t = getToken();
    if (t && tab === "tasks") loadTasks(t);
  });

  async function runTaskAction(id: number, action: "start" | "stop" | "enqueue") {
    const t = getToken();
    if (!t) return;
    setBusyId(id);
    try {
      await apiPost(`/api/admin/tasks/${id}/${action === "enqueue" ? "enqueue" : action}`, t);
      setFlash({ variant: "success", message: `任务 #${id} 操作成功` });
      await loadTasks(t);
    } catch {
      setFlash({ variant: "error", message: `任务 #${id} 操作失败` });
    } finally {
      setBusyId(null);
    }
  }

  async function runArticleAction(id: number, action: "review" | "publish" | "trash") {
    const t = getToken();
    if (!t) return;
    setBusyId(id);
    try {
      await apiPost(`/api/admin/articles/${id}/${action}`, t);
      setFlash({ variant: "success", message: `文章 #${id} 已更新` });
      await loadArticles(t, articleFilter);
    } catch {
      setFlash({ variant: "error", message: `文章 #${id} 操作失败` });
    } finally {
      setBusyId(null);
    }
  }

  async function deleteTask(id: number) {
    const t = getToken();
    if (!t || !confirm(`确认删除任务 #${id}？`)) return;
    setBusyId(id);
    try {
      await apiDelete(`/api/admin/tasks/${id}`, t);
      setFlash({ variant: "success", message: `任务 #${id} 已删除` });
      await loadTasks(t);
    } catch {
      setFlash({ variant: "error", message: `任务 #${id} 删除失败` });
    } finally {
      setBusyId(null);
    }
  }

  async function batchStartTasks(ids: number[]) {
    const t = getToken();
    if (!t || ids.length === 0) return;
    try {
      const res = await apiPost<{ started: number }>("/api/admin/tasks/batch/start", t, { ids });
      setFlash({ variant: "success", message: `已启动 ${res.started} 个任务` });
      await loadTasks(t);
    } catch {
      setFlash({ variant: "error", message: "批量启动失败" });
    }
  }

  async function batchTrashArticles(ids: number[]) {
    const t = getToken();
    if (!t || ids.length === 0) return;
    if (!confirm(`确认将 ${ids.length} 篇文章移入回收站？`)) return;
    try {
      const res = await apiPost<{ trashed: number }>("/api/admin/articles/batch/trash", t, { ids });
      setFlash({ variant: "success", message: `已回收 ${res.trashed} 篇` });
      await loadArticles(t, articleFilter);
    } catch {
      setFlash({ variant: "error", message: "批量回收失败" });
    }
  }

  async function batchPublishArticles(ids: number[]) {
    const t = getToken();
    if (!t || ids.length === 0) return;
    try {
      const res = await apiPost<{ published: number }>("/api/admin/articles/batch/publish", t, { ids });
      setFlash({ variant: "success", message: `已发布 ${res.published} 篇` });
      await loadArticles(t, articleFilter);
    } catch {
      setFlash({ variant: "error", message: "批量发布失败" });
    }
  }

  const headerTitle = tab === "distribution-citations" ? zh.distribution.citationsTitle : zh.operations.hubTitle;
  const headerSubtitle =
    tab === "distribution-citations" ? zh.distribution.citationsSubtitle : zh.operations.hubSubtitle;

  return (
    <div>
      <HubHeader title={headerTitle} subtitle={headerSubtitle} />
      <HubNav items={OPERATIONS_NAV} tone="blue" />

      {flash && <FlashAlert variant={flash.variant === "success" ? "success" : "error"}>{flash.message}</FlashAlert>}
      {loading && !stats && tab === "overview" && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}
      {loading && tab === "tasks" && tasks.length === 0 && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {tab === "overview" && (
        <div className="space-y-8">
          <QuickStartPanel />
          {automation && <DashboardAutomation automation={automation} />}
        </div>
      )}

      {tab === "tasks" && (
        <>
          {stats && (
            <div className="mb-6">
              <OperationsOverview stats={stats} />
            </div>
          )}
          <TasksPanel
            tasks={tasks}
            busyId={busyId}
            onStart={(id) => runTaskAction(id, "start")}
            onStop={(id) => runTaskAction(id, "stop")}
            onEnqueue={(id) => runTaskAction(id, "enqueue")}
            onDelete={deleteTask}
            onBatchStart={batchStartTasks}
          />
        </>
      )}

      {tab === "articles" && (
        <ArticlesPanel
          articles={articles}
          stats={articleStats}
          filter={articleFilter}
          busyId={busyId}
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
    </div>
  );
}
