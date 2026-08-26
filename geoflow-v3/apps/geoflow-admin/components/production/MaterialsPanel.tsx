"use client";

import Link from "next/link";
import { FolderTree, Image, Key, MessageSquareText, Type, Users } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { zh } from "@/lib/i18n/zh";
import type { MaterialStats } from "@/lib/production-types";

const CARDS: {
  key: keyof MaterialStats;
  secondary: keyof MaterialStats;
  title: string;
  icon: LucideIcon;
  tone: string;
  href?: string;
}[] = [
  { key: "keyword_libraries", secondary: "total_keywords", title: zh.production.materials.keywordTitle, icon: Key, tone: "bg-blue-50 text-blue-600", href: "/production/materials/keywords" },
  { key: "title_libraries", secondary: "total_titles", title: zh.production.materials.titleTitle, icon: Type, tone: "bg-emerald-50 text-emerald-600", href: "/production/materials/titles" },
  { key: "image_libraries", secondary: "total_images", title: zh.production.materials.imageTitle, icon: Image, tone: "bg-purple-50 text-purple-600", href: "/production/materials/images" },
  { key: "authors", secondary: "authors", title: zh.production.materials.authorTitle, icon: Users, tone: "bg-indigo-50 text-indigo-600", href: "/production/materials/authors" },
];

export function MaterialsPanel({ stats }: { stats: MaterialStats }) {
  return (
    <section className="overflow-hidden rounded-lg border border-blue-200 bg-white shadow-sm">
      <div className="border-b border-amber-100 bg-amber-50/70 px-6 py-5">
        <p className="text-xs font-medium uppercase tracking-wide text-amber-800">遗产 CMS</p>
        <h2 className="mt-1 text-xl font-semibold text-gray-900">{zh.production.materials.heading}</h2>
        <p className="mt-1 text-sm text-gray-600">{zh.production.materials.subtitle}</p>
        <p className="mt-2 text-sm text-amber-900">
          新战役请走{" "}
          <Link href="/production/themes" className="font-medium underline">
            主题包
          </Link>{" "}
          与{" "}
          <Link href="/production/knowledge" className="font-medium underline">
            知识库
          </Link>
          ，不要把标题库当选题清单。
        </p>
      </div>
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900">{zh.production.materials.foundationTitle}</h3>
        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
          {CARDS.map((card) => {
            const Icon = card.icon;
            const libCount = stats[card.key] as number;
            const itemCount = stats[card.secondary] as number;
            const itemLabel = card.key === "authors" ? `${itemCount} 位` : zh.production.materials.items(itemCount);
            return (
              <div
                key={card.key}
                className="rounded-lg border border-gray-200 bg-white p-6 shadow transition hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-md"
              >
                <div className={`flex h-12 w-12 items-center justify-center rounded-md ${card.tone}`}>
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="mt-5 text-lg font-semibold text-gray-900">{card.title}</h3>
                <div className="mt-5 space-y-2 text-sm">
                  <div className="flex justify-between gap-4">
                    <span className="text-gray-500">库数量</span>
                    <span className="font-semibold text-gray-900">{zh.production.materials.libraries(libCount)}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-gray-500">条目</span>
                    <span className="font-semibold text-gray-900">{itemLabel}</span>
                  </div>
                </div>
                {card.href && (
                  <Link href={card.href} className="mt-4 inline-flex text-sm font-medium text-emerald-700 hover:text-emerald-800">
                    {zh.production.materials.manage}
                  </Link>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50/40 p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <FolderTree className="h-5 w-5 text-emerald-600" />
              <div>
                <p className="font-semibold text-gray-900">{zh.production.materials.categoryTitle}</p>
                <p className="text-sm text-gray-600">{zh.production.materials.categoryDesc}</p>
              </div>
            </div>
            <Link href="/production/materials/categories" className="inline-flex rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700">
              {zh.production.materials.manageCategories}
            </Link>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/production/url-import" className="inline-flex rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            URL 导入
          </Link>
          <Link href="/production/ai-models" className="inline-flex rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            AI 模型
          </Link>
          <Link href="/production/ai-prompts" className="inline-flex rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            提示词
          </Link>
        </div>

        <div className="mt-6 rounded-lg border border-violet-200 bg-violet-50/40 p-5">
          <div className="flex items-center gap-3">
            <MessageSquareText className="h-5 w-5 text-violet-600" />
            <div>
              <p className="font-semibold text-gray-900">{zh.production.materials.promptTitle}</p>
              <p className="text-sm text-gray-600">
                正文 {stats.body_prompts} · 特殊 {stats.special_prompts}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
