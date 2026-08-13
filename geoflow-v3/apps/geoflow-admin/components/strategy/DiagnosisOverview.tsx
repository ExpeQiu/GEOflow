"use client";

import Link from "next/link";
import type { DiagnosisPanel, MonitorKpis } from "@/lib/strategy-types";
import { ProbeDashboard } from "./ProbeDashboard";
import { AivisKpiCard, GapPriorityBadge, LayerSection } from "./shared/AivisPrimitives";

export function DiagnosisOverview({
  data,
  monitor,
  onScan,
  scanning,
}: {
  data: DiagnosisPanel;
  monitor: MonitorKpis;
  onScan?: () => void;
  scanning?: boolean;
}) {
  const { collection, brand, product, optimization, difficulty } = data;
  const window =
    collection.collection_window.period_start && collection.collection_window.period_end
      ? `${collection.collection_window.period_start} ~ ${collection.collection_window.period_end}`
      : "暂无采集记录";

  return (
    <div className="space-y-6">
      <ProbeDashboard dashboard={monitor} onScan={onScan} scanning={scanning} />

      <LayerSection title="数据采集层" subtitle={`${collection.platform_count} 个 AI 平台 · ${window}`}>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <AivisKpiCard label="品牌场景" value={`${collection.question_stats.brand_questions} 题`} sub={`约 ${collection.question_stats.brand_probes_estimated} 次探针`} />
          <AivisKpiCard label="产品场景" value={`${collection.question_stats.product_questions} 题`} sub={`约 ${collection.question_stats.product_probes_estimated} 次探针`} tone="cyan" />
          <AivisKpiCard label="平台数" value={String(collection.platform_count)} tone="amber" />
          <Link href="/strategy/collection" className="flex items-center text-sm text-violet-700 hover:underline">
            查看采集详情 →
          </Link>
        </div>
      </LayerSection>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <LayerSection title="品牌分析层 (Brand Visibility)">
          <div className="grid grid-cols-3 gap-3">
            <AivisKpiCard label="Top3" value={brand.top3_pct != null ? `${brand.top3_pct}%` : `${brand.visibility_pct}%`} />
            <AivisKpiCard label="提及率" value={brand.mention_rate_pct != null ? `${brand.mention_rate_pct}%` : `${brand.visibility_pct}%`} tone="cyan" />
            <AivisKpiCard label="负向率" value={brand.sentiment_negative_pct != null ? `${brand.sentiment_negative_pct}%` : brand.sentiment_score != null ? `${brand.sentiment_score}%` : "—"} tone="amber" />
          </div>
          <Link href="/strategy/brand" className="mt-3 inline-block text-sm text-violet-700 hover:underline">
            品牌竞品矩阵 →
          </Link>
        </LayerSection>

        <LayerSection title="产品分析层 (Product Visibility)">
          <div className="grid grid-cols-3 gap-3">
            <AivisKpiCard label="Top3" value={product.top3_pct != null ? `${product.top3_pct}%` : `${product.visibility_pct}%`} />
            <AivisKpiCard label="提及率" value={product.mention_rate_pct != null ? `${product.mention_rate_pct}%` : `${product.visibility_pct}%`} tone="cyan" />
            <AivisKpiCard label="负向率" value={product.sentiment_negative_pct != null ? `${product.sentiment_negative_pct}%` : product.sentiment_score != null ? `${product.sentiment_score}%` : "—"} tone="amber" />
          </div>
          <Link href="/strategy/product" className="mt-3 inline-block text-sm text-violet-700 hover:underline">
            场景图谱 →
          </Link>
        </LayerSection>
      </div>

      <LayerSection title="优化策略层" subtitle={optimization.market_summary}>
        <div className="grid gap-4 md:grid-cols-3">
          {optimization.top_platform && (
            <div className="rounded-md bg-violet-50 p-4">
              <p className="text-xs text-gray-500">平台优先</p>
              <p className="text-lg font-semibold">{optimization.top_platform.label}</p>
              <p className="text-sm text-violet-700">推荐分 {optimization.top_platform.score}</p>
            </div>
          )}
          <div className="md:col-span-2">
            <p className="mb-2 text-xs font-medium text-gray-500">TOP 高优先级场景</p>
            <ul className="space-y-2">
              {optimization.priority_scenes.length === 0 ? (
                <li className="text-sm text-gray-400">暂无场景数据</li>
              ) : (
                optimization.priority_scenes.map((s) => (
                  <li key={s.scene_name} className="flex items-center justify-between text-sm">
                    <span>{s.scene_name}</span>
                    <GapPriorityBadge priority={s.gap_priority} />
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>
        {optimization.insights[0] && (
          <p className="mt-3 text-sm text-gray-600">
            💡 {optimization.insights[0].title}：{optimization.insights[0].body}
          </p>
        )}
        <Link href="/strategy/optimization" className="mt-3 inline-block text-sm text-violet-700 hover:underline">
          查看优化策略 →
        </Link>
      </LayerSection>

      <LayerSection title="难度评估层">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <AivisKpiCard label="监管合规" value={`${difficulty.regulatory_compliance}/5`} />
          <AivisKpiCard label="市场竞争" value={`${difficulty.market_competition}/5`} tone="cyan" />
          <AivisKpiCard label="实体基础" value={`${difficulty.entity_foundation}/5`} tone="amber" />
          <AivisKpiCard label="综合难度" value={`${difficulty.overall_score}/5`} />
        </div>
        <Link href="/strategy/difficulty" className="mt-3 inline-block text-sm text-violet-700 hover:underline">
          难度详情 →
        </Link>
      </LayerSection>

      {data.latest_report && (
        <LayerSection title="最新诊断报告">
          <p className="text-sm font-medium">{data.latest_report.title}</p>
          <Link href="/strategy/reports" className="mt-2 inline-block text-sm text-violet-700 hover:underline">
            查看全部报告 →
          </Link>
        </LayerSection>
      )}
    </div>
  );
}
