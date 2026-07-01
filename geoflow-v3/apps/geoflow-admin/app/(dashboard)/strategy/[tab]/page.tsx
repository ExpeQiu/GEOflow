"use client";

import { useParams } from "next/navigation";

const TABS: Record<string, string> = {
  overview: "策略总览",
  monitor: "GEO Monitor",
  simulator: "模拟器",
  "geo-eval": "GEO 诊断",
  analytics: "分析",
};

export default function StrategyPage() {
  const { tab } = useParams<{ tab: string }>();
  return (
    <div>
      <h1 className="text-lg font-bold mb-4">Strategy · {TABS[tab] || tab}</h1>
      <div className="bg-white border rounded-lg p-6 text-[var(--muted)] text-sm">
        {tab === "overview" && "Strategy Hub KPI — 技术品牌 P0 覆盖率、Wiki 合规率、Gweb 同步成功率"}
        {tab === "monitor" && "Monitor 探针扫描 — Celery beat geo:monitor-scan"}
        {tab === "simulator" && "RAG 模拟回答 — InternalGeoEvalEngine"}
        {tab === "geo-eval" && "GEO 门禁诊断 — article_evaluations"}
        {tab === "analytics" && "运营分析 — view_logs / adoption metrics"}
      </div>
    </div>
  );
}
