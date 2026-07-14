"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { DataTable } from "@/components/admin/PlaceholderPanel";
import { AiConfigPanel } from "@/components/production/AiConfigPanel";
import { AiConfigSubNav } from "@/components/production/AiConfigSubNav";
import { KnowledgePanel } from "@/components/production/KnowledgePanel";
import { KnowledgeSubNav } from "@/components/production/KnowledgeSubNav";
import { MaterialsPanel } from "@/components/production/MaterialsPanel";
import { ProductionOverview, type KnowledgeHealth } from "@/components/production/ProductionOverview";
import { GeoEvalPanel } from "@/components/strategy/GeoEvalPanel";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, apiPut, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_NAV } from "@/lib/nav-config";
import type {
  AiStats,
  KnowledgeItem,
  MaterialStats,
  OrchestrationStats,
  TechAsset,
  WorkflowCatalog,
} from "@/lib/production-types";
import type {
  EvalFailureRow,
  FailureTopN,
  GateConfig,
  GeoAlert,
  GeoEvalSummary,
  ProbeStandardsConfig,
} from "@/lib/strategy-types";

export default function ProductionPage() {
  const { tab } = useParams<{ tab: string }>();
  const token = useAuthGuard();
  const [stats, setStats] = useState<MaterialStats | null>(null);
  const [aiStats, setAiStats] = useState<AiStats | null>(null);
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([]);
  const [orchestration, setOrchestration] = useState<OrchestrationStats | null>(null);
  const [workflowCatalog, setWorkflowCatalog] = useState<WorkflowCatalog | null>(null);
  const [assets, setAssets] = useState<TechAsset[]>([]);
  const [yamlText, setYamlText] = useState("");
  const [yamlFlash, setYamlFlash] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [flash, setFlash] = useState<{ variant: "success" | "error"; message: string } | null>(null);
  const [knowledgeHealth, setKnowledgeHealth] = useState<KnowledgeHealth>("empty");
  const [loading, setLoading] = useState(true);
  const [geoEval, setGeoEval] = useState<GeoEvalSummary | null>(null);
  const [gate, setGate] = useState<GateConfig | null>(null);
  const [probeStandards, setProbeStandards] = useState<ProbeStandardsConfig | null>(null);
  const [failureTopN, setFailureTopN] = useState<FailureTopN[]>([]);
  const [recentFailures, setRecentFailures] = useState<EvalFailureRow[]>([]);
  const [geoAlerts, setGeoAlerts] = useState<GeoAlert[]>([]);
  const [savingSettings, setSavingSettings] = useState(false);

  const reload = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setFlash(null);
    try {
      if (tab === "overview") {
        const data = await apiGet<{ stats: MaterialStats; ai_stats: AiStats; knowledge_health: KnowledgeHealth }>(
          "/api/admin/production/overview",
          t,
        );
        setStats(data.stats);
        setAiStats(data.ai_stats);
        setKnowledgeHealth(data.knowledge_health ?? "empty");
      } else if (tab === "materials") {
        const data = await apiGet<{ stats: MaterialStats }>("/api/admin/production/materials", t);
        setStats(data.stats);
      } else if (tab === "knowledge") {
        const data = await apiGet<{ stats: MaterialStats; items: KnowledgeItem[]; orchestration: OrchestrationStats }>(
          "/api/admin/production/knowledge",
          t,
        );
        setStats(data.stats);
        setKnowledgeItems(data.items);
        setOrchestration(data.orchestration);
      } else if (tab === "ai_config") {
        const data = await apiGet<{
          ai_stats: AiStats;
          orchestration: OrchestrationStats;
          workflow_catalog: WorkflowCatalog;
        }>("/api/admin/production/ai-config", t);
        setAiStats(data.ai_stats);
        setOrchestration(data.orchestration);
        setWorkflowCatalog(data.workflow_catalog);
      } else if (tab === "geo-eval") {
        const data = await apiGet<{
          gate: GateConfig;
          probe_standards?: ProbeStandardsConfig;
          summary: GeoEvalSummary;
          failure_top_n: FailureTopN[];
          recent_failures: EvalFailureRow[];
          recent_alerts: GeoAlert[];
        }>("/api/admin/strategy/geo-eval", t);
        setGate(data.gate);
        setProbeStandards(data.probe_standards ?? null);
        setGeoEval(data.summary);
        setFailureTopN(data.failure_top_n);
        setRecentFailures(data.recent_failures);
        setGeoAlerts(data.recent_alerts ?? []);
      } else if (tab === "tech-assets") {
        const data = await apiGet<{ items: TechAsset[] }>("/api/admin/tech-assets", t);
        setAssets(data.items);
      }
    } catch {
      setFlash({ variant: "error", message: "加载失败，请刷新重试" });
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    if (token) reload();
  }, [token, reload]);

  async function syncKb(kbId: number) {
    const t = getToken();
    if (!t) return;
    setBusyId(kbId);
    try {
      await apiPost(`/api/admin/knowledge-bases/${kbId}/sync-chunks`, t);
      setFlash({ variant: "success", message: `知识库 #${kbId} 切片任务已入队` });
      await reload();
    } catch {
      setFlash({ variant: "error", message: `知识库 #${kbId} 同步失败` });
    } finally {
      setBusyId(null);
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

  async function batchReevaluate(articleIds: number[]) {
    const t = getToken();
    if (!t || articleIds.length === 0) return;
    setBusyId(-1);
    try {
      const res = await apiPost<{ queued: number }>("/api/admin/strategy/simulator/batch-reevaluate", t, {
        article_ids: articleIds.slice(0, 50),
      });
      setFlash({ variant: "success", message: `已入队 ${res.queued} 篇重评` });
      await reload();
    } catch {
      setFlash({ variant: "error", message: "批量重评失败" });
    } finally {
      setBusyId(null);
    }
  }

  async function saveGate(next: {
    enabled: boolean;
    hard_gate: boolean;
    wiki_checks_enabled: boolean;
    simulation_pass_score: number;
    audit_pass_score: number;
  }) {
    const t = getToken();
    if (!t) return;
    setSavingSettings(true);
    try {
      const data = await apiPut<{ gate: GateConfig; probe_standards: ProbeStandardsConfig }>(
        "/api/admin/strategy/geo-eval/settings",
        t,
        { gate: next },
      );
      setGate(data.gate);
      if (data.probe_standards) setProbeStandards(data.probe_standards);
      setFlash({ variant: "success", message: "内容门禁已保存" });
    } catch {
      setFlash({ variant: "error", message: "内容门禁保存失败" });
    } finally {
      setSavingSettings(false);
    }
  }

  async function saveProbeStandards(next: {
    footnote_on_bias: boolean;
    do_not_overwrite_open_api_kpi: true;
    rank_report_weight: { list_order: number; first_mention: number; unknown: number };
    min_evidence_level: string;
    forbid_corpus_as_l1: boolean;
    fixture_min_list_acc: number;
    scan_platforms: string;
    priority_floor_daily: number;
  }) {
    const t = getToken();
    if (!t) return;
    setSavingSettings(true);
    try {
      const data = await apiPut<{ gate: GateConfig; probe_standards: ProbeStandardsConfig }>(
        "/api/admin/strategy/geo-eval/settings",
        t,
        { probe_standards: next },
      );
      setGate(data.gate);
      setProbeStandards(data.probe_standards);
      setFlash({ variant: "success", message: "探针标准已保存" });
    } catch {
      setFlash({ variant: "error", message: "探针标准保存失败" });
    } finally {
      setSavingSettings(false);
    }
  }

  const headerTitle =
    tab === "geo-eval"
      ? zh.production.tabs["geo-eval"]
      : tab === "knowledge" || tab === "tech-assets"
        ? zh.production.tabs.knowledge
        : zh.production.hubTitle;
  const headerSubtitle =
    tab === "geo-eval"
      ? zh.strategy.geoEval.dualTrackTitle
      : tab === "knowledge" || tab === "tech-assets"
        ? zh.production.knowledge.hubDesc
        : zh.production.hubSubtitle;

  return (
    <div>
      <HubHeader title={headerTitle} subtitle={headerSubtitle} />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      {(tab === "knowledge" || tab === "tech-assets") && <KnowledgeSubNav />}
      {tab === "ai_config" && <AiConfigSubNav />}

      {flash && <FlashAlert variant={flash.variant === "success" ? "success" : "error"}>{flash.message}</FlashAlert>}
      {loading && tab === "overview" && !stats && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}
      {loading && (tab === "knowledge" || tab === "ai_config" || tab === "geo-eval") && (
        <FlashAlert variant="info">{zh.common.loading}</FlashAlert>
      )}

      {tab === "overview" && stats && aiStats && (
        <ProductionOverview stats={stats} aiStats={aiStats} knowledgeHealth={knowledgeHealth} />
      )}

      {tab === "materials" && stats && <MaterialsPanel stats={stats} />}

      {tab === "knowledge" && stats && (
        <KnowledgePanel stats={stats} items={knowledgeItems} busyId={busyId} onSync={syncKb} />
      )}

      {tab === "ai_config" && aiStats && orchestration && workflowCatalog && (
        <AiConfigPanel
          aiStats={aiStats}
          orchestration={orchestration}
          workflowCatalog={workflowCatalog}
        />
      )}

      {tab === "geo-eval" && gate && geoEval && (
        <GeoEvalPanel
          gate={gate}
          probeStandards={probeStandards}
          summary={geoEval}
          failureTopN={failureTopN}
          recentFailures={recentFailures}
          recentAlerts={geoAlerts}
          onReevaluate={reevaluate}
          onBatchReevaluate={batchReevaluate}
          onSaveGate={saveGate}
          onSaveProbeStandards={saveProbeStandards}
          busyId={busyId}
          saving={savingSettings}
        />
      )}

      {tab === "tech-assets" && (
        <div>
          <div className="mb-3 flex flex-wrap justify-end gap-2">
            <Link href="/production/tech-assets/new" className="rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white">新建</Link>
          </div>
          <div className="mb-4 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
            <h3 className="text-sm font-medium text-gray-900">YAML 批量导入</h3>
            <textarea className="mt-2 w-full rounded-md border px-3 py-2 text-xs font-mono" rows={5} placeholder="- ip_id: tech-001\n  name: 示例技术点" value={yamlText} onChange={(e) => setYamlText(e.target.value)} />
            <button
              type="button"
              className="mt-2 rounded-md bg-emerald-600 px-3 py-1.5 text-sm text-white"
              onClick={async () => {
                const t = getToken();
                if (!t || !yamlText.trim()) return;
                const res = await apiPost<{ created: number; updated: number }>("/api/admin/tech-assets/import-yaml", t, { yaml_text: yamlText });
                setYamlFlash(`导入完成：新建 ${res.created}，更新 ${res.updated}`);
                const data = await apiGet<{ items: TechAsset[] }>("/api/admin/tech-assets", t);
                setAssets(data.items);
              }}
            >
              导入 YAML
            </button>
            {yamlFlash && <p className="mt-2 text-sm text-emerald-700">{yamlFlash}</p>}
          </div>
          <DataTable
            headers={["ID", "名称", "IP ID", "Wiki 类型", "状态", "操作"]}
            rows={assets.map((a) => [a.id, a.name, a.ip_id, a.wiki_type, a.status, ""]) }
            emptyText="暂无技术 IP 资产"
          />
          <ul className="mt-2 divide-y rounded-lg bg-white text-sm shadow-sm ring-1 ring-gray-200">
            {assets.map((a) => (
              <li key={a.id} className="flex justify-between px-4 py-2">
                <span>{a.name}</span>
                <Link href={`/production/tech-assets/${a.id}`} className="text-emerald-700">编辑</Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
