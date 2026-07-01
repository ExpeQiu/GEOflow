"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { DataTable } from "@/components/admin/PlaceholderPanel";
import { AiConfigPanel } from "@/components/production/AiConfigPanel";
import { KnowledgePanel } from "@/components/production/KnowledgePanel";
import { MaterialsPanel } from "@/components/production/MaterialsPanel";
import { ProductionOverview } from "@/components/production/ProductionOverview";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_NAV } from "@/lib/nav-config";
import type {
  AiModelRow,
  AiStats,
  KnowledgeItem,
  MaterialStats,
  OrchestrationStats,
  PromptRow,
  TechAsset,
  WorkflowCatalog,
} from "@/lib/production-types";

export default function ProductionPage() {
  const { tab } = useParams<{ tab: string }>();
  const token = useAuthGuard();
  const [stats, setStats] = useState<MaterialStats | null>(null);
  const [aiStats, setAiStats] = useState<AiStats | null>(null);
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([]);
  const [orchestration, setOrchestration] = useState<OrchestrationStats | null>(null);
  const [workflowCatalog, setWorkflowCatalog] = useState<WorkflowCatalog | null>(null);
  const [models, setModels] = useState<AiModelRow[]>([]);
  const [prompts, setPrompts] = useState<PromptRow[]>([]);
  const [assets, setAssets] = useState<TechAsset[]>([]);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [flash, setFlash] = useState<{ variant: "success" | "error"; message: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setFlash(null);
    try {
      if (tab === "overview") {
        const data = await apiGet<{ stats: MaterialStats; ai_stats: AiStats }>("/api/admin/production/overview", t);
        setStats(data.stats);
        setAiStats(data.ai_stats);
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
          models: AiModelRow[];
          prompts: PromptRow[];
        }>("/api/admin/production/ai-config", t);
        setAiStats(data.ai_stats);
        setOrchestration(data.orchestration);
        setWorkflowCatalog(data.workflow_catalog);
        setModels(data.models);
        setPrompts(data.prompts);
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

  return (
    <div>
      <HubHeader title={zh.production.hubTitle} subtitle={zh.production.hubSubtitle} />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />

      {flash && <FlashAlert variant={flash.variant === "success" ? "success" : "error"}>{flash.message}</FlashAlert>}
      {loading && tab === "overview" && !stats && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}
      {loading && (tab === "knowledge" || tab === "ai_config") && (
        <FlashAlert variant="info">{zh.common.loading}</FlashAlert>
      )}

      {tab === "overview" && stats && aiStats && <ProductionOverview stats={stats} aiStats={aiStats} />}

      {tab === "materials" && stats && <MaterialsPanel stats={stats} />}

      {tab === "knowledge" && stats && (
        <KnowledgePanel stats={stats} items={knowledgeItems} busyId={busyId} onSync={syncKb} />
      )}

      {tab === "ai_config" && aiStats && orchestration && workflowCatalog && (
        <AiConfigPanel
          aiStats={aiStats}
          orchestration={orchestration}
          workflowCatalog={workflowCatalog}
          models={models}
          prompts={prompts}
        />
      )}

      {tab === "tech-assets" && (
        <DataTable
          headers={["ID", "名称", "IP ID", "Wiki 类型", "状态"]}
          rows={assets.map((a) => [a.id, a.name, a.ip_id, a.wiki_type, a.status])}
          emptyText="暂无技术 IP 资产"
        />
      )}
    </div>
  );
}
