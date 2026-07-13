"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { AnalyticsPanel } from "@/components/strategy/AnalyticsPanel";
import { BrandVisibilityPanel } from "@/components/strategy/BrandVisibilityPanel";
import { CollectionPanel } from "@/components/strategy/CollectionPanel";
import { DiagnosisOverview } from "@/components/strategy/DiagnosisOverview";
import { GeoEvalPanel } from "@/components/strategy/GeoEvalPanel";
import { DifficultyPanelView, OptimizationPanelView } from "@/components/strategy/OptimizationDifficultyPanels";
import { ProductVisibilityPanel } from "@/components/strategy/ProductVisibilityPanel";
import { ReportsPanel } from "@/components/strategy/ReportsPanel";
import { QuestionBankPanel } from "@/components/strategy/QuestionBankPanel";
import { SceneGraphPanel } from "@/components/strategy/SceneGraphPanel";
import { SimulatorPanel } from "@/components/strategy/SimulatorPanel";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { STRATEGY_NAV } from "@/lib/nav-config";
import type {
  AnalyticsSnapshot,
  BrandPanel,
  CollectionPanel as CollectionPanelData,
  CompetitorBrand,
  DiagnosisPanel,
  DifficultyPanel,
  EvalFailureRow,
  FailureTopN,
  GateConfig,
  GeoEvalSummary,
  MonitorInsight,
  MonitorKpis,
  MonitorQuestion,
  MonitorRun,
  MonitorProbe,
  MonitorScene,
  MonitorSnapshot,
  GeoAlert,
  OptimizationPanel,
  ProductPanel,
  QueryTemplate,
  TrendPoint,
  VisibilityReport,
} from "@/lib/strategy-types";

export default function StrategyPage() {
  const { tab } = useParams<{ tab: string }>();
  const token = useAuthGuard();
  const [flash, setFlash] = useState<{ variant: "success" | "error"; message: string } | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [scanning, setScanning] = useState(false);
  const [loading, setLoading] = useState(true);

  const [diagnosis, setDiagnosis] = useState<DiagnosisPanel | null>(null);
  const [collection, setCollection] = useState<CollectionPanelData | null>(null);
  const [brandPanel, setBrandPanel] = useState<BrandPanel | null>(null);
  const [productPanel, setProductPanel] = useState<ProductPanel | null>(null);
  const [optimization, setOptimization] = useState<OptimizationPanel | null>(null);
  const [difficulty, setDifficulty] = useState<DifficultyPanel | null>(null);

  const [monitorKpis, setMonitorKpis] = useState<MonitorKpis | null>(null);
  const [monitorQuestions, setMonitorQuestions] = useState<MonitorQuestion[]>([]);
  const [monitorRuns, setMonitorRuns] = useState<MonitorRun[]>([]);
  const [monitorProbes, setMonitorProbes] = useState<MonitorProbe[]>([]);
  const [monitorScenes, setMonitorScenes] = useState<MonitorScene[]>([]);
  const [monitorTemplates, setMonitorTemplates] = useState<QueryTemplate[]>([]);
  const [monitorCompetitors, setMonitorCompetitors] = useState<CompetitorBrand[]>([]);
  const [monitorInsights, setMonitorInsights] = useState<MonitorInsight[]>([]);
  const [monitorSnapshots, setMonitorSnapshots] = useState<MonitorSnapshot[]>([]);
  const [visibilityReports, setVisibilityReports] = useState<VisibilityReport[]>([]);

  const [geoEval, setGeoEval] = useState<GeoEvalSummary | null>(null);
  const [gate, setGate] = useState<GateConfig | null>(null);
  const [failureTopN, setFailureTopN] = useState<FailureTopN[]>([]);
  const [recentFailures, setRecentFailures] = useState<EvalFailureRow[]>([]);
  const [geoAlerts, setGeoAlerts] = useState<GeoAlert[]>([]);
  const [analyticsSnap, setAnalyticsSnap] = useState<AnalyticsSnapshot | null>(null);
  const [publicationTrend, setPublicationTrend] = useState<TrendPoint[]>([]);
  const [taskHealth, setTaskHealth] = useState({ running: 0, pending: 0, failed: 0 });
  const [aiUsage, setAiUsage] = useState({ used_today: 0, total_used: 0, active_models: 0 });
  const [topArticles, setTopArticles] = useState<{ id: number; title: string; view_count: number; status: string }[]>([]);

  const reload = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setFlash(null);
    try {
      if (tab === "diagnosis" || tab === "overview") {
        setDiagnosis(await apiGet<DiagnosisPanel>("/api/admin/strategy/diagnosis", t));
      } else if (tab === "collection" || tab === "monitor") {
        const data = await apiGet<CollectionPanelData>("/api/admin/strategy/collection", t);
        setCollection(data);
      } else if (tab === "question-bank") {
        await loadMonitorSettings(t);
      } else if (tab === "brand") {
        setBrandPanel(await apiGet<BrandPanel>("/api/admin/strategy/brand", t));
      } else if (tab === "product") {
        setProductPanel(await apiGet<ProductPanel>("/api/admin/strategy/product", t));
      } else if (tab === "scene-graph") {
        const [product] = await Promise.all([
          apiGet<ProductPanel>("/api/admin/strategy/product", t),
          loadMonitorSettings(t),
        ]);
        setProductPanel(product);
      } else if (tab === "optimization") {
        setOptimization(await apiGet<OptimizationPanel>("/api/admin/strategy/optimization", t));
      } else if (tab === "difficulty") {
        setDifficulty(await apiGet<DifficultyPanel>("/api/admin/strategy/difficulty", t));
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
          insights?: MonitorInsight[];
          visibility_trends?: MonitorSnapshot[];
        }>("/api/admin/strategy/analytics", t);
        setAnalyticsSnap(data.snapshot);
        setPublicationTrend(data.publication_trend);
        setTaskHealth(data.task_health);
        setAiUsage(data.ai_usage);
        setTopArticles(data.top_articles);
        setMonitorInsights(data.insights ?? []);
        setMonitorSnapshots(data.visibility_trends ?? []);
      }
    } catch {
      setFlash({ variant: "error", message: "加载失败" });
    } finally {
      setLoading(false);
    }
  }, [tab]);

  async function loadMonitorSettings(t: string) {
    const data = await apiGet<{
      dashboard: MonitorKpis;
      questions: MonitorQuestion[];
      recent_runs: MonitorRun[];
      recent_probes: MonitorProbe[];
      scenes?: MonitorScene[];
      templates?: QueryTemplate[];
      competitors?: CompetitorBrand[];
      insights?: MonitorInsight[];
      snapshots?: MonitorSnapshot[];
      reports?: VisibilityReport[];
    }>("/api/admin/strategy/monitor", t);
    setMonitorKpis(data.dashboard);
    setMonitorQuestions(data.questions);
    setMonitorRuns(data.recent_runs ?? []);
    setMonitorProbes(data.recent_probes ?? []);
    setMonitorScenes(data.scenes ?? []);
    setMonitorTemplates(data.templates ?? []);
    setMonitorCompetitors(data.competitors ?? []);
    setMonitorInsights(data.insights ?? []);
    setMonitorSnapshots(data.snapshots ?? []);
    setVisibilityReports(data.reports ?? []);
  }

  useEffect(() => {
    if (token) reload();
  }, [token, reload]);

  async function runMonitorScan() {
    const t = getToken();
    if (!t) return;
    setScanning(true);
    try {
      await apiPost("/api/admin/strategy/monitor/scan", t);
      setFlash({ variant: "success", message: "扫描已入队" });
      await reload();
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

  async function createMonitorQuestion(body: Record<string, unknown>) {
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/strategy/monitor/questions", t, body);
    await reload();
  }

  async function updateMonitorQuestion(id: number, body: Record<string, unknown>) {
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

  async function batchReevaluate(articleIds: number[]) {
    const t = getToken();
    if (!t) return;
    const res = await apiPost<{ queued: number }>("/api/admin/strategy/simulator/batch-reevaluate", t, { article_ids: articleIds });
    setFlash({ variant: "success", message: `已入队 ${res.queued} 篇` });
  }

  const effectiveTab = tab === "overview" ? "diagnosis" : tab === "monitor" ? "collection" : tab === "settings" ? "analytics" : tab;

  return (
    <div>
      <HubHeader title={zh.strategy.hubTitle} subtitle={zh.strategy.hubSubtitle} />
      <HubNav items={STRATEGY_NAV} tone="violet" />

      {flash && <FlashAlert variant={flash.variant === "success" ? "success" : "error"}>{flash.message}</FlashAlert>}
      {loading && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {(effectiveTab === "diagnosis") && diagnosis && (
        <DiagnosisOverview
          data={diagnosis}
          monitor={
            diagnosis.monitor ?? {
              probe_count: 0,
              avg_brand_rank: null,
              mention_rate: 0,
              visibility_pct: 0,
              weighted_rank_score: null,
              sentiment_score: null,
              platform_summary: [],
              question_count: 0,
            }
          }
          onScan={runMonitorScan}
          scanning={scanning}
        />
      )}

      {(effectiveTab === "collection") && collection && (
        <CollectionPanel data={collection} onScan={runMonitorScan} scanning={scanning} />
      )}

      {effectiveTab === "brand" && brandPanel && <BrandVisibilityPanel data={brandPanel} onRefresh={reload} />}

      {effectiveTab === "product" && productPanel && <ProductVisibilityPanel data={productPanel} onRefresh={reload} />}

      {effectiveTab === "scene-graph" && productPanel && (
        <SceneGraphPanel scenes={monitorScenes} funnel={productPanel.scene_funnel} onRefresh={reload} />
      )}

      {effectiveTab === "optimization" && optimization && <OptimizationPanelView data={optimization} />}

      {effectiveTab === "difficulty" && difficulty && <DifficultyPanelView data={difficulty} />}

      {effectiveTab === "reports" && <ReportsPanel />}

      {effectiveTab === "question-bank" && monitorKpis && (
        <QuestionBankPanel
          questions={monitorQuestions}
          templates={monitorTemplates}
          recentRuns={monitorRuns}
          onCreate={createMonitorQuestion}
          onUpdate={updateMonitorQuestion}
          onDelete={deleteMonitorQuestion}
          onRefresh={reload}
        />
      )}

      {effectiveTab === "analytics" && analyticsSnap && (
        <AnalyticsPanel
          snapshot={analyticsSnap}
          publicationTrend={publicationTrend}
          taskHealth={taskHealth}
          aiUsage={aiUsage}
          topArticles={topArticles}
          insights={monitorInsights}
          visibilityTrends={monitorSnapshots}
        />
      )}

      {effectiveTab === "geo-eval" && gate && geoEval && (
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

      {effectiveTab === "simulator" && gate && geoEval && (
        <SimulatorPanel
          gate={gate}
          summary={geoEval}
          failureTopN={failureTopN}
          recentFailures={recentFailures}
          onReevaluate={reevaluate}
          onBatchReevaluate={batchReevaluate}
          onApplyRecommendations={async () => {}}
          busyId={busyId}
        />
      )}
    </div>
  );
}
