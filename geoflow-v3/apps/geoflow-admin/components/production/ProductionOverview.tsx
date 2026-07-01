import Link from "next/link";
import { zh } from "@/lib/i18n/zh";
import type { AiStats, MaterialStats } from "@/lib/production-types";

export function ProductionOverview({ stats, aiStats }: { stats: MaterialStats; aiStats: AiStats }) {
  const materialCount =
    stats.keyword_libraries + stats.title_libraries + stats.image_libraries + stats.authors;

  return (
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
        meta={`提示词 ${aiStats.prompt_count}`}
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
