"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { DiagnosisOverview } from "@/components/strategy/DiagnosisOverview";
import { DifficultyPanelView, OptimizationPanelView } from "@/components/strategy/OptimizationDifficultyPanels";
import { ProbesHub } from "@/components/strategy/ProbesHub";
import { ReportsPanel } from "@/components/strategy/ReportsPanel";
import { SalesCopyPanel } from "@/components/strategy/SalesCopyPanel";
import { SceneGraphPanel } from "@/components/strategy/SceneGraphPanel";
import { ThemeMiningPanel } from "@/components/strategy/ThemeMiningPanel";
import { VisibilityHub } from "@/components/strategy/VisibilityHub";
import { WebIntelPanel } from "@/components/strategy/WebIntelPanel";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { STRATEGY_MORE_NAV, STRATEGY_NAV } from "@/lib/nav-config";
import { useRouteParams } from "@/lib/use-route-params";
import type {
  BrandPanel,
  CollectionPanel as CollectionPanelData,
  CompetitorBrand,
  DiagnosisPanel,
  DifficultyPanel,
  GeoEvalSummary,
  GeowebAlignment,
  MonitorKpis,
  MonitorRun,
  MonitorScene,
  OptimizationPanel,
  ProductPanel,
  QueryTemplate,
  StrategyOverviewData,
  TechBrandMetrics,
  WebSource,
  GapRemediation,
} from "@/lib/strategy-types";

function errMsg(e: unknown, fallback: string) {
  return e instanceof Error && e.message ? e.message : fallback;
}

/** Hub 辅轨扫描跟探针设置，不写死 doubao/kimi。 */
function probeScanPlatforms(data: CollectionPanelData | null | undefined): string[] {
  const fromSettings = (data?.probe_settings?.platforms ?? [])
    .map((p) => p.trim())
    .filter(Boolean);
  if (fromSettings.length) return fromSettings;
  return (data?.next_scan?.platforms ?? []).map((p) => p.platform).filter(Boolean);
}

/** 旧入口 → 收敛后的主路径 / 合并页 */
const LEGACY_TAB_REDIRECT: Record<string, string> = {
  overview: "/strategy/diagnosis",
  monitor: "/strategy/probes",
  analytics: "/operations/analytics",
  simulator: "/production/geo-eval",
  "geo-eval": "/production/geo-eval",
  settings: "/strategy/probes?view=settings",
  collection: "/strategy/probes?view=scan",
  "question-bank": "/strategy/probes?view=questions",
  "gold-labels": "/strategy/probes?view=gold",
  brand: "/strategy/visibility?view=brand",
  product: "/strategy/visibility?view=product",
};

export default function StrategyPage({ params }: { params: Promise<{ tab: string }> }) {
  const { tab } = useRouteParams(params);
  const router = useRouter();
  const token = useAuthGuard();
  const [flash, setFlash] = useState<{ variant: "success" | "error"; message: string } | null>(null);
  const [scanning, setScanning] = useState(false);
  const [scanStatus, setScanStatus] = useState("");
  const [cendScanning, setCendScanning] = useState(false);
  const [frameworkScanning, setFrameworkScanning] = useState(false);
  const [citationScanning, setCitationScanning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [processBusy, setProcessBusy] = useState(false);

  const [diagnosis, setDiagnosis] = useState<DiagnosisPanel | null>(null);
  const [overviewMonitor, setOverviewMonitor] = useState<MonitorKpis | null>(null);
  const [remediations, setRemediations] = useState<GapRemediation[]>([]);
  const [geoEval, setGeoEval] = useState<GeoEvalSummary | null>(null);
  const [techBrand, setTechBrand] = useState<TechBrandMetrics | null>(null);
  const [geowebAlignment, setGeowebAlignment] = useState<GeowebAlignment | null>(null);

  const [collection, setCollection] = useState<CollectionPanelData | null>(null);
  const [brandPanel, setBrandPanel] = useState<BrandPanel | null>(null);
  const [productPanel, setProductPanel] = useState<ProductPanel | null>(null);
  const [optimization, setOptimization] = useState<OptimizationPanel | null>(null);
  const [difficulty, setDifficulty] = useState<DifficultyPanel | null>(null);
  const [webSources, setWebSources] = useState<WebSource[]>([]);
  const [webReports, setWebReports] = useState<{ id: number; title: string; status: string; created_at: string | null }[]>([]);

  const [monitorRuns, setMonitorRuns] = useState<MonitorRun[]>([]);
  const [monitorScenes, setMonitorScenes] = useState<MonitorScene[]>([]);
  const [monitorTemplates, setMonitorTemplates] = useState<QueryTemplate[]>([]);
  const [monitorCompetitors, setMonitorCompetitors] = useState<CompetitorBrand[]>([]);
  const [monitorBrandName, setMonitorBrandName] = useState("");
  const [draftThemes, setDraftThemes] = useState<
    Array<{
      id: number;
      title: string;
      status: string;
      scene_id?: number | null;
      meta?: { mining?: { longtail_queries?: string[]; thinking_digest?: string } };
    }>
  >([]);

  useEffect(() => {
    const dest = LEGACY_TAB_REDIRECT[tab];
    if (dest) router.replace(dest);
  }, [tab, router]);

  const reload = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    if (LEGACY_TAB_REDIRECT[tab]) return;
    setLoading(true);
    setFlash(null);
    try {
      if (tab === "diagnosis") {
        const [diag, ov] = await Promise.all([
          apiGet<DiagnosisPanel>("/api/admin/strategy/diagnosis", t),
          apiGet<StrategyOverviewData>("/api/admin/strategy/overview", t),
        ]);
        setDiagnosis(diag);
        setOverviewMonitor(ov.monitor);
        setRemediations(ov.remediations ?? []);
        setGeoEval(ov.geo_eval);
        setTechBrand(ov.tech_brand);
        setGeowebAlignment(ov.geoweb_alignment ?? ov.gweb_alignment ?? null);
      } else if (tab === "probes") {
        const [coll] = await Promise.all([
          apiGet<CollectionPanelData>("/api/admin/strategy/collection", t),
          loadMonitorSettings(t),
        ]);
        setCollection(coll);
      } else if (tab === "visibility") {
        const [brand, product] = await Promise.all([
          apiGet<BrandPanel>("/api/admin/strategy/brand", t),
          apiGet<ProductPanel>("/api/admin/strategy/product", t),
        ]);
        setBrandPanel(brand);
        setProductPanel(product);
      } else if (tab === "scene-graph") {
        const [product] = await Promise.all([
          apiGet<ProductPanel>("/api/admin/strategy/product", t),
          loadMonitorSettings(t),
        ]);
        setProductPanel(product);
      } else if (tab === "theme-mining") {
        const [, themes] = await Promise.all([
          loadMonitorSettings(t),
          apiGet<{ items: Array<{ id: number; title: string; status: string; scene_id?: number | null; meta?: { mining?: { longtail_queries?: string[]; thinking_digest?: string } } }> }>(
            "/api/admin/themes?status=draft",
            t,
          ).catch(() => ({ items: [] })),
        ]);
        setDraftThemes(themes.items ?? []);
      } else if (tab === "optimization") {
        setOptimization(await apiGet<OptimizationPanel>("/api/admin/strategy/optimization", t));
      } else if (tab === "difficulty") {
        setDifficulty(await apiGet<DifficultyPanel>("/api/admin/strategy/difficulty", t));
      } else if (tab === "web-intel") {
        const data = await apiGet<{
          sources: WebSource[];
          reports: { id: number; title: string; status: string; created_at: string | null }[];
        }>("/api/admin/strategy/web-intel", t);
        setWebSources(data.sources ?? []);
        setWebReports(data.reports ?? []);
      } else if (tab === "sales-copy" || tab === "reports") {
        /* panels self-load */
      }
    } catch (e) {
      setFlash({ variant: "error", message: errMsg(e, "加载失败") });
    } finally {
      setLoading(false);
    }
  }, [tab]);

  async function loadMonitorSettings(t: string) {
    const data = await apiGet<{
      dashboard: MonitorKpis;
      brand_name?: string;
      recent_runs: MonitorRun[];
      scenes?: MonitorScene[];
      templates?: QueryTemplate[];
      competitors?: CompetitorBrand[];
    }>("/api/admin/strategy/monitor", t);
    setMonitorBrandName(data.brand_name ?? "");
    setMonitorRuns(data.recent_runs ?? []);
    setMonitorScenes(data.scenes ?? []);
    setMonitorTemplates(data.templates ?? []);
    setMonitorCompetitors(data.competitors ?? []);
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
            setFlash({
              variant: "success",
              message: `扫描 #${latest.id} 已${latest.status === "completed" ? "完成" : "结束"}`,
            });
            break;
          }
        } else {
          setScanStatus("Worker 处理中…");
        }
      }
      if (tab !== "probes") await reload();
    } catch (e) {
      setFlash({ variant: "error", message: errMsg(e, "扫描入队失败") });
    } finally {
      setScanning(false);
      setScanStatus("");
    }
  }

  async function runCendScan() {
    const t = getToken();
    if (!t) return;
    setCendScanning(true);
    setScanStatus("C端金标入队…");
    try {
      await apiPost("/api/admin/strategy/cend/scan", t, {
        platforms: ["yuanbao"],
        limit: 5,
        min_priority: 80,
        sync: false,
      });
      setFlash({
        variant: "success",
        message: "C端金标扫描已入队（辅轨 cend_sample，不覆盖 open_api）",
      });
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        await reloadCollection(t);
      }
    } catch (e) {
      setFlash({ variant: "error", message: errMsg(e, "C端扫描入队失败") });
    } finally {
      setCendScanning(false);
      setScanStatus("");
    }
  }

  async function runFrameworkScan() {
    const t = getToken();
    if (!t) return;
    const data = collection ?? (await reloadCollection(t));
    const platforms = probeScanPlatforms(data);
    if (!platforms.length) {
      setFlash({ variant: "error", message: "探针设置未配置平台，请先到探针设置勾选" });
      return;
    }
    setFrameworkScanning(true);
    setScanStatus("框架轨入队…");
    try {
      await apiPost("/api/admin/strategy/framework/scan", t, {
        platforms,
        limit: 8,
        min_priority: 80,
        sync: false,
      });
      setFlash({
        variant: "success",
        message: `框架轨已入队（${platforms.join(",")}，scheme=framework_api，不覆盖 open_api）`,
      });
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        await reloadCollection(t);
      }
    } catch (e) {
      setFlash({ variant: "error", message: errMsg(e, "框架轨扫描入队失败") });
    } finally {
      setFrameworkScanning(false);
      setScanStatus("");
    }
  }

  async function runCitationScan() {
    const t = getToken();
    if (!t) return;
    const data = collection ?? (await reloadCollection(t));
    const platforms = probeScanPlatforms(data);
    if (!platforms.length) {
      setFlash({ variant: "error", message: "探针设置未配置平台，请先到探针设置勾选" });
      return;
    }
    setCitationScanning(true);
    setScanStatus("引用轨入队…");
    try {
      await apiPost("/api/admin/strategy/citation/scan", t, {
        platforms,
        limit: 8,
        min_priority: 80,
        sync: false,
      });
      setFlash({
        variant: "success",
        message: `引用轨已入队（${platforms.join(",")}，scheme=citation_grounded，不覆盖 open_api）`,
      });
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        await reloadCollection(t);
      }
    } catch (e) {
      setFlash({ variant: "error", message: errMsg(e, "引用轨扫描入队失败") });
    } finally {
      setCitationScanning(false);
      setScanStatus("");
    }
  }

  async function processRemediationsDue() {
    const t = getToken();
    if (!t) return;
    setProcessBusy(true);
    try {
      const res = await apiPost<{ processed?: number }>("/api/admin/strategy/monitor/remediations/process-due", t);
      setFlash({ variant: "success", message: `已处理到期实验 ${res.processed ?? 0} 条` });
      await reload();
    } catch (e) {
      setFlash({ variant: "error", message: errMsg(e, "处理到期实验失败") });
    } finally {
      setProcessBusy(false);
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

  async function createWebSource(body: { url: string; label: string }) {
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/strategy/web-intel/sources", t, body);
    await reload();
  }

  async function deleteWebSource(id: number) {
    const t = getToken();
    if (!t) return;
    await apiDelete(`/api/admin/strategy/web-intel/sources/${id}`, t);
    await reload();
  }

  async function refreshWebSource(id: number) {
    const t = getToken();
    if (!t) return;
    await apiPost(`/api/admin/strategy/web-intel/sources/${id}/refresh`, t);
    await reload();
  }

  if (LEGACY_TAB_REDIRECT[tab]) {
    return (
      <div>
        <HubHeader title={zh.strategy.hubTitle} subtitle={zh.strategy.hubSubtitle} />
        <FlashAlert variant="info">正在跳转至正确板块…</FlashAlert>
      </div>
    );
  }

  const diagnosisMonitor =
    overviewMonitor ??
    diagnosis?.monitor ?? {
      probe_count: 0,
      avg_brand_rank: null,
      mention_rate: 0,
      visibility_pct: 0,
      weighted_rank_score: null,
      sentiment_score: null,
      platform_summary: [],
      question_count: 0,
    };

  return (
    <div>
      <HubHeader title={zh.strategy.hubTitle} subtitle={zh.strategy.hubSubtitle} />
      <HubNav items={STRATEGY_NAV} moreItems={STRATEGY_MORE_NAV} tone="violet" />

      {flash && <FlashAlert variant={flash.variant === "success" ? "success" : "error"}>{flash.message}</FlashAlert>}
      {loading && tab !== "sales-copy" && tab !== "reports" && (
        <FlashAlert variant="info">{zh.common.loading}</FlashAlert>
      )}

      {tab === "diagnosis" && diagnosis && (
        <DiagnosisOverview
          data={diagnosis}
          monitor={diagnosisMonitor}
          remediations={remediations}
          geoEval={geoEval}
          techBrand={techBrand}
          geowebAlignment={geowebAlignment}
          onScan={runMonitorScan}
          scanning={scanning}
          onProcessDue={processRemediationsDue}
          processBusy={processBusy}
        />
      )}

      {tab === "probes" && (
        <ProbesHub
          collection={collection}
          onScan={runMonitorScan}
          onCendScan={runCendScan}
          onFrameworkScan={runFrameworkScan}
          onCitationScan={runCitationScan}
          onRefreshCollection={async () => {
            const t = getToken();
            if (t) await reloadCollection(t);
          }}
          scanning={scanning}
          scanStatus={scanStatus}
          cendScanning={cendScanning}
          frameworkScanning={frameworkScanning}
          citationScanning={citationScanning}
          scenes={monitorScenes}
          competitors={monitorCompetitors}
          brandName={monitorBrandName}
          templates={monitorTemplates}
          recentRuns={monitorRuns}
          onCreateQuestion={createMonitorQuestion}
          onUpdateQuestion={updateMonitorQuestion}
          onDeleteQuestion={deleteMonitorQuestion}
          onRefreshQuestions={reload}
        />
      )}

      {tab === "visibility" && (
        <VisibilityHub brand={brandPanel} product={productPanel} onRefresh={reload} />
      )}

      {tab === "scene-graph" && productPanel && (
        <SceneGraphPanel funnel={productPanel.scene_funnel} onRefresh={reload} />
      )}

      {tab === "theme-mining" && (
        <ThemeMiningPanel scenes={monitorScenes} draftThemes={draftThemes} onRefresh={reload} />
      )}

      {tab === "optimization" && optimization && (
        <OptimizationPanelView data={optimization} onMarketSaved={reload} />
      )}

      {tab === "difficulty" && difficulty && <DifficultyPanelView data={difficulty} />}

      {tab === "reports" && <ReportsPanel />}

      {tab === "sales-copy" && <SalesCopyPanel />}

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
