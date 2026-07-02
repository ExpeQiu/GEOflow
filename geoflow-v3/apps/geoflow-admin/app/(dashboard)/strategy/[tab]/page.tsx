"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { AnalyticsPanel } from "@/components/strategy/AnalyticsPanel";
import { GeoEvalPanel } from "@/components/strategy/GeoEvalPanel";
import { MonitorPanel } from "@/components/strategy/MonitorPanel";
import { SimulatorPanel } from "@/components/strategy/SimulatorPanel";
import { StrategyOverview } from "@/components/strategy/StrategyOverview";
import { WebIntelPanel } from "@/components/strategy/WebIntelPanel";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { STRATEGY_NAV } from "@/lib/nav-config";
import type {
  AnalyticsSnapshot,
  EvalFailureRow,
  FailureTopN,
  GateConfig,
  GeoEvalSummary,
  MonitorKpis,
  MonitorQuestion,
  MonitorRun,
  MonitorProbe,
  GeoAlert,
  TechBrandMetrics,
  TrendPoint,
  WebSource,
} from "@/lib/strategy-types";

export default function StrategyPage() {
  const { tab } = useParams<{ tab: string }>();
  const token = useAuthGuard();
  const [flash, setFlash] = useState<{ variant: "success" | "error"; message: string } | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [scanning, setScanning] = useState(false);
  const [loading, setLoading] = useState(true);

  const [geoEval, setGeoEval] = useState<GeoEvalSummary | null>(null);
  const [techBrand, setTechBrand] = useState<TechBrandMetrics | null>(null);
  const [monitorKpis, setMonitorKpis] = useState<MonitorKpis | null>(null);
  const [analyticsSnap, setAnalyticsSnap] = useState<AnalyticsSnapshot | null>(null);
  const [monitorQuestions, setMonitorQuestions] = useState<MonitorQuestion[]>([]);
  const [monitorRuns, setMonitorRuns] = useState<MonitorRun[]>([]);
  const [monitorProbes, setMonitorProbes] = useState<MonitorProbe[]>([]);
  const [geoAlerts, setGeoAlerts] = useState<GeoAlert[]>([]);
  const [gate, setGate] = useState<GateConfig | null>(null);
  const [failureTopN, setFailureTopN] = useState<FailureTopN[]>([]);
  const [recentFailures, setRecentFailures] = useState<EvalFailureRow[]>([]);
  const [publicationTrend, setPublicationTrend] = useState<TrendPoint[]>([]);
  const [taskHealth, setTaskHealth] = useState({ running: 0, pending: 0, failed: 0 });
  const [aiUsage, setAiUsage] = useState({ used_today: 0, total_used: 0, active_models: 0 });
  const [topArticles, setTopArticles] = useState<{ id: number; title: string; view_count: number; status: string }[]>([]);
  const [webSources, setWebSources] = useState<WebSource[]>([]);
  const [webReports, setWebReports] = useState<{ id: number; title: string; status: string; created_at: string | null }[]>([]);

  const reload = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setFlash(null);
    try {
      if (tab === "overview") {
        const data = await apiGet<{
          geo_eval: GeoEvalSummary;
          tech_brand: TechBrandMetrics;
          monitor: MonitorKpis;
          analytics: AnalyticsSnapshot;
        }>("/api/admin/strategy/overview", t);
        setGeoEval(data.geo_eval);
        setTechBrand(data.tech_brand);
        setMonitorKpis(data.monitor);
        setAnalyticsSnap(data.analytics);
      } else if (tab === "monitor") {
        const data = await apiGet<{ dashboard: MonitorKpis; questions: MonitorQuestion[]; recent_runs: MonitorRun[]; recent_probes: MonitorProbe[] }>("/api/admin/strategy/monitor", t);
        setMonitorKpis(data.dashboard);
        setMonitorQuestions(data.questions);
        setMonitorRuns(data.recent_runs ?? []);
        setMonitorProbes(data.recent_probes ?? []);
      } else if (tab === "geo-eval" || tab === "simulator") {
        const data = await apiGet<{
          gate: GateConfig;
          summary: GeoEvalSummary;
          failure_top_n: FailureTopN[];
          recent_failures: EvalFailureRow[];
          recent_alerts: GeoAlert[];
        }>("/api/admin/strategy/geo-eval", t);
        setGate(data.gate);
        setGeoEval(data.summary);
        setFailureTopN(data.failure_top_n);
        setRecentFailures(data.recent_failures);
        setGeoAlerts(data.recent_alerts ?? []);
      } else if (tab === "analytics") {
        const data = await apiGet<{
          snapshot: AnalyticsSnapshot;
          publication_trend: TrendPoint[];
          task_health: { running: number; pending: number; failed: number };
          ai_usage: { used_today: number; total_used: number; active_models: number };
          top_articles: { id: number; title: string; view_count: number; status: string }[];
        }>("/api/admin/strategy/analytics", t);
        setAnalyticsSnap(data.snapshot);
        setPublicationTrend(data.publication_trend);
        setTaskHealth(data.task_health);
        setAiUsage(data.ai_usage);
        setTopArticles(data.top_articles);
      } else if (tab === "web-intel") {
        const data = await apiGet<{ sources: WebSource[]; reports: typeof webReports }>("/api/admin/strategy/web-intel", t);
        setWebSources(data.sources);
        setWebReports(data.reports);
      }
    } catch {
      setFlash({ variant: "error", message: "加载失败" });
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    if (token) reload();
  }, [token, reload]);

  async function runMonitorScan() {
    const t = getToken();
    if (!t) return;
    setScanning(true);
    try {
      await apiPost("/api/admin/strategy/monitor/scan", t);
      setFlash({ variant: "success", message: "Monitor 扫描已入队" });
    } catch {
      setFlash({ variant: "error", message: "扫描入队失败" });
    } finally {
      setScanning(false);
    }
  }

  async function reevaluate(articleId: number) {
    const t = getToken();
    if (!t) return;
    setBusyId(articleId);
    try {
      await apiPost(`/api/admin/strategy/geo-eval/reevaluate/${articleId}`, t);
      setFlash({ variant: "success", message: `文章 #${articleId} 评估已入队` });
      await reload();
    } catch {
      setFlash({ variant: "error", message: "评估入队失败" });
    } finally {
      setBusyId(null);
    }
  }

  async function createMonitorQuestion(body: { question_text: string; priority: number; status: string }) {
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/strategy/monitor/questions", t, body);
    await reload();
  }

  async function updateMonitorQuestion(id: number, body: { question_text: string; priority: number; status: string }) {
    const t = getToken();
    if (!t) return;
    await apiPatch(`/api/admin/strategy/monitor/questions/${id}`, t, body);
    await reload();
  }

  async function deleteMonitorQuestion(id: number) {
    const t = getToken();
    if (!t || !confirm("确认删除？")) return;
    await apiDelete(`/api/admin/strategy/monitor/questions/${id}`, t);
    await reload();
  }

  async function createWebSource(body: { url: string; label: string }) {
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/strategy/web-intel/sources", t, body);
    await reload();
  }

  async function deleteWebSource(id: number) {
    const t = getToken();
    if (!t || !confirm("确认删除信源？")) return;
    await apiDelete(`/api/admin/strategy/web-intel/sources/${id}`, t);
    await reload();
  }

  async function refreshWebSource(id: number) {
    const t = getToken();
    if (!t) return;
    await apiPost(`/api/admin/strategy/web-intel/sources/${id}/refresh`, t);
    setFlash({ variant: "success", message: "刷新已入队" });
  }

  async function batchReevaluate(articleIds: number[]) {
    const t = getToken();
    if (!t) return;
    const res = await apiPost<{ queued: number }>("/api/admin/strategy/simulator/batch-reevaluate", t, { article_ids: articleIds });
    setFlash({ variant: "success", message: `已入队 ${res.queued} 篇` });
  }

  async function applyRecommendations(articleId: number) {
    const t = getToken();
    if (!t) return;
    setBusyId(articleId);
    try {
      await apiPost(`/api/admin/strategy/simulator/apply-recommendations/${articleId}`, t);
      setFlash({ variant: "success", message: `文章 #${articleId} 建议已应用` });
    } catch {
      setFlash({ variant: "error", message: "应用失败" });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <HubHeader title={zh.strategy.hubTitle} subtitle={zh.strategy.hubSubtitle} />
      <HubNav items={STRATEGY_NAV} tone="violet" />

      {flash && <FlashAlert variant={flash.variant === "success" ? "success" : "error"}>{flash.message}</FlashAlert>}
      {loading && tab === "overview" && !geoEval && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {tab === "overview" && geoEval && techBrand && monitorKpis && analyticsSnap && (
        <StrategyOverview geoEval={geoEval} techBrand={techBrand} monitor={monitorKpis} analytics={analyticsSnap} />
      )}

      {tab === "monitor" && monitorKpis && (
        <MonitorPanel
          dashboard={monitorKpis}
          questions={monitorQuestions}
          recentRuns={monitorRuns}
          recentProbes={monitorProbes}
          onScan={runMonitorScan}
          scanning={scanning}
          onCreate={createMonitorQuestion}
          onUpdate={updateMonitorQuestion}
          onDelete={deleteMonitorQuestion}
        />
      )}

      {tab === "geo-eval" && gate && geoEval && (
        <GeoEvalPanel
          gate={gate}
          summary={geoEval}
          failureTopN={failureTopN}
          recentFailures={recentFailures}
          recentAlerts={geoAlerts}
          onReevaluate={reevaluate}
          busyId={busyId}
        />
      )}

      {tab === "simulator" && gate && geoEval && (
        <SimulatorPanel
          gate={gate}
          summary={geoEval}
          failureTopN={failureTopN}
          recentFailures={recentFailures}
          onReevaluate={reevaluate}
          onBatchReevaluate={batchReevaluate}
          onApplyRecommendations={applyRecommendations}
          busyId={busyId}
        />
      )}

      {tab === "analytics" && analyticsSnap && (
        <AnalyticsPanel
          snapshot={analyticsSnap}
          publicationTrend={publicationTrend}
          taskHealth={taskHealth}
          aiUsage={aiUsage}
          topArticles={topArticles}
        />
      )}

      {tab === "web-intel" && (
        <WebIntelPanel
          sources={webSources}
          reports={webReports}
          onCreate={createWebSource}
          onDelete={deleteWebSource}
          onRefresh={refreshWebSource}
        />
      )}
    </div>
  );
}
