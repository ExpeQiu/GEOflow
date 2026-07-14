"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { BrandVisibilityPanel } from "@/components/strategy/BrandVisibilityPanel";
import { CollectionPanel } from "@/components/strategy/CollectionPanel";
import { DiagnosisOverview } from "@/components/strategy/DiagnosisOverview";
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
  OptimizationPanel,
  ProductPanel,
  QueryTemplate,
  VisibilityReport,
} from "@/lib/strategy-types";

export default function StrategyPage() {
  const { tab } = useParams<{ tab: string }>();
  const token = useAuthGuard();
  const [flash, setFlash] = useState<{ variant: "success" | "error"; message: string } | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState("");
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
  const [monitorBrandName, setMonitorBrandName] = useState("");
  const [monitorInsights, setMonitorInsights] = useState<MonitorInsight[]>([]);
  const [monitorSnapshots, setMonitorSnapshots] = useState<MonitorSnapshot[]>([]);
  const [visibilityReports, setVisibilityReports] = useState<VisibilityReport[]>([]);

  const [geoEval, setGeoEval] = useState<GeoEvalSummary | null>(null);
  const [gate, setGate] = useState<GateConfig | null>(null);
  const [failureTopN, setFailureTopN] = useState<FailureTopN[]>([]);
  const [recentFailures, setRecentFailures] = useState<EvalFailureRow[]>([]);

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
      } else if (tab === "simulator") {
        const data = await apiGet<{
          gate: GateConfig;
          summary: GeoEvalSummary;
          failure_top_n: FailureTopN[];
          recent_failures: EvalFailureRow[];
        }>("/api/admin/strategy/geo-eval", t);
        setGate(data.gate);
        setGeoEval(data.summary);
        setFailureTopN(data.failure_top_n);
        setRecentFailures(data.recent_failures);
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
      brand_name?: string;
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
    setMonitorBrandName(data.brand_name ?? "");
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

  async function reloadCollection(t: string) {
    const data = await apiGet<CollectionPanelData>("/api/admin/strategy/collection", t);
    setCollection(data);
    return data;
  }

  async function runMonitorScan(scanType: "daily" | "market" = "daily") {
    const t = getToken();
    if (!t) return;
    setScanning(true);
    setScanStatus("已入队，等待 Worker…");
    const beforeRunId = collection?.latest_run?.id ?? collection?.recent_runs[0]?.id ?? 0;
    try {
      await apiPost(`/api/admin/strategy/monitor/scan?scan_type=${scanType}`, t);
      setFlash({ variant: "success", message: `${scanType === "market" ? "竞品" : "全量"}扫描已入队` });

      for (let i = 0; i < 40; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        const data = await reloadCollection(t);
        const latest = data.latest_run ?? data.recent_runs[0];
        if (!latest) continue;
        if (latest.id > beforeRunId) {
          setScanStatus(`任务 #${latest.id} · ${latest.status}`);
          if (latest.status === "completed" || latest.status === "failed") {
            setFlash({ variant: "success", message: `扫描 #${latest.id} 已${latest.status === "completed" ? "完成" : "结束"}` });
            break;
          }
        } else {
          setScanStatus("Worker 处理中…");
        }
      }
      if (tab !== "collection" && tab !== "monitor") await reload();
    } catch {
      setFlash({ variant: "error", message: "扫描入队失败" });
    } finally {
      setScanning(false);
      setScanStatus("");
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

  const effectiveTab = tab === "overview" ? "diagnosis" : tab === "monitor" ? "collection" : tab;

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
        <CollectionPanel
          data={collection}
          onScan={runMonitorScan}
          onRefresh={async () => {
            const t = getToken();
            if (t) await reloadCollection(t);
          }}
          scanning={scanning}
          scanStatus={scanStatus}
        />
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
          scenes={monitorScenes}
          competitors={monitorCompetitors}
          brandName={monitorBrandName}
          templates={monitorTemplates}
          recentRuns={monitorRuns}
          onCreate={createMonitorQuestion}
          onUpdate={updateMonitorQuestion}
          onDelete={deleteMonitorQuestion}
          onRefresh={reload}
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
