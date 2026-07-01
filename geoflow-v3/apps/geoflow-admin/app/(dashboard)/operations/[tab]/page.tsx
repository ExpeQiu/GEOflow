"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { ArticlesPanel } from "@/components/operations/ArticlesPanel";
import { DistributionPanel } from "@/components/operations/DistributionPanel";
import { OperationsOverview } from "@/components/operations/OperationsOverview";
import { TasksPanel } from "@/components/operations/TasksPanel";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
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
    const data = await apiGet<{ stats: OpsStats }>("/api/admin/operations/overview", t);
    setStats(data.stats);
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

  return (
    <div>
      <HubHeader title={zh.operations.hubTitle} subtitle={zh.operations.hubSubtitle} />
      <HubNav items={OPERATIONS_NAV} tone="blue" />

      {flash && <FlashAlert variant={flash.variant === "success" ? "success" : "error"}>{flash.message}</FlashAlert>}
      {loading && !stats && tab === "overview" && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {tab === "overview" && stats && <OperationsOverview stats={stats} />}

      {tab === "tasks" && (
        <TasksPanel
          tasks={tasks}
          busyId={busyId}
          onStart={(id) => runTaskAction(id, "start")}
          onStop={(id) => runTaskAction(id, "stop")}
          onEnqueue={(id) => runTaskAction(id, "enqueue")}
        />
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
        />
      )}

      {tab === "distribution" && distStats && (
        <DistributionPanel stats={distStats} channels={channels} recentJobs={recentJobs} />
      )}
    </div>
  );
}
