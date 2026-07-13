import Link from "next/link";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";
import type { AiStats, MaterialStats } from "@/lib/production-types";

export type KnowledgeHealth = "ready" | "pending" | "no_embed" | "empty";

const HEALTH_LABEL: Record<KnowledgeHealth, string> = {
  ready: zh.production.knowledge.healthReady,
  pending: zh.production.knowledge.healthPending,
  no_embed: zh.production.knowledge.healthNoEmbed,
  empty: zh.production.knowledge.healthEmpty,
};

const HEALTH_CLASS: Record<KnowledgeHealth, string> = {
  ready: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  pending: "bg-amber-50 text-amber-700 ring-amber-200",
  no_embed: "bg-red-50 text-red-700 ring-red-200",
  empty: "bg-slate-100 text-slate-700 ring-slate-200",
};

export function ProductionOverview({
  stats,
  aiStats,
  knowledgeHealth = "empty",
}: {
  stats: MaterialStats;
  aiStats: AiStats;
  knowledgeHealth?: KnowledgeHealth;
}) {
  const materialCount =
    stats.keyword_libraries + stats.title_libraries + stats.image_libraries + stats.authors;
  const vectorProgress =
    stats.knowledge_chunks > 0 ? Math.round((stats.vectorized_chunks / stats.knowledge_chunks) * 100) : 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-orange-100 bg-orange-50/50 px-5 py-4">
        <div>
          <p className="text-sm font-medium text-gray-900">知识库健康度</p>
          <p className="mt-1 text-xs text-gray-600">
            向量化 {stats.vectorized_chunks}/{stats.knowledge_chunks}（{vectorProgress}%）· Embedding 模型 {stats.active_embedding_models} 个
          </p>
        </div>
        <span className={cn("inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1", HEALTH_CLASS[knowledgeHealth])}>
          {HEALTH_LABEL[knowledgeHealth]}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card
          label={zh.production.tabs.knowledge}
          value={stats.knowledge_bases}
          meta={`切片 ${stats.knowledge_chunks}`}
          href="/production/knowledge"
          tone="emerald"
        />
        <Card
          label={zh.production.tabs.materials}
          value={materialCount}
          meta={`关键词 ${stats.total_keywords}`}
          href="/production/materials"
          tone="blue"
        />
        <Card
          label={zh.production.tabs.ai_config}
          value={aiStats.model_count}
          meta={`Chat ${aiStats.chat_models} · Embed ${aiStats.embedding_models}`}
          href="/production/ai_config"
          tone="violet"
        />
        <Card
          label="向量化进度"
          value={stats.vectorized_chunks}
          meta={`待处理 ${stats.unvectorized_chunks}`}
          href="/production/knowledge"
          tone="amber"
        />
      </div>
    </div>
  );
}

function Card({
  label,
  value,
  meta,
  href,
  tone,
}: {
  label: string;
  value: number;
  meta: string;
  href: string;
  tone: "emerald" | "blue" | "violet" | "amber";
}) {
  const border = {
    emerald: "border-emerald-200 bg-emerald-50/60 text-emerald-700",
    blue: "border-blue-200 bg-blue-50/60 text-blue-700",
    violet: "border-violet-200 bg-violet-50/60 text-violet-700",
    amber: "border-amber-200 bg-amber-50/60 text-amber-700",
  }[tone];
  const link = {
    emerald: "text-emerald-800",
    blue: "text-blue-800",
    violet: "text-violet-800",
    amber: "text-amber-800",
  }[tone];

  return (
    <div className={`rounded-lg border p-5 ${border}`}>
      <p className="text-xs font-semibold uppercase">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
      <p className="mt-1 text-xs text-gray-500">{meta}</p>
      <Link href={href} className={`mt-3 inline-block text-sm hover:underline ${link}`}>
        {zh.production.viewDetail}
      </Link>
    </div>
  );
}
