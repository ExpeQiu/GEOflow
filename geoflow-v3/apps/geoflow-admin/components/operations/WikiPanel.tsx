"use client";

import Link from "next/link";
import { BookOpen, FileText, Globe, Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";
import { WIKI_PAGE_TYPES, type WikiPage, type WikiStats } from "@/lib/wiki-form-types";

const typeLabel = zh.wiki.types as Record<string, string>;

export function WikiPanel({
  pages,
  stats,
  typeCounts,
  filter,
  query,
  onFilterChange,
  onQueryChange,
  onImport,
  importing,
}: {
  pages: WikiPage[];
  stats: WikiStats;
  typeCounts: Record<string, number>;
  filter: string;
  query: string;
  onFilterChange: (type: string) => void;
  onQueryChange: (q: string) => void;
  onImport?: () => void;
  importing?: boolean;
}) {
  return (
    <div>
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat icon={BookOpen} label={zh.wiki.statsTotal} value={stats.total} color="text-blue-600" />
        <Stat icon={FileText} label={zh.wiki.statsVisible} value={stats.visible} color="text-slate-600" />
        <Stat icon={Globe} label={zh.wiki.statsSynced} value={stats.synced} color="text-green-600" />
        <Stat icon={Search} label={zh.wiki.statsSmokeHidden} value={stats.smoke_hidden} color="text-amber-600" />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <FilterChip active={filter === "all"} onClick={() => onFilterChange("all")} label={zh.wiki.filterAll} />
        {WIKI_PAGE_TYPES.map((type) => (
          <FilterChip
            key={type}
            active={filter === type}
            onClick={() => onFilterChange(type)}
            label={`${typeLabel[type] || type}${typeCounts[type] ? ` ${typeCounts[type]}` : ""}`}
          />
        ))}
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder={zh.wiki.searchPlaceholder}
          className="w-48 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
        <Link
          href="/operations/wiki/new"
          className="ml-auto rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          {zh.wiki.createButton}
        </Link>
        {onImport && (
          <button
            type="button"
            disabled={importing}
            onClick={onImport}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {importing ? zh.common.loading : zh.wiki.importFromGeoweb}
          </button>
        )}
      </div>
      <p className="mb-3 text-xs text-gray-500">{zh.wiki.smokeHint}</p>

      {pages.length === 0 ? (
        <div className="rounded-lg bg-white px-6 py-10 text-center text-sm text-gray-500 shadow-sm ring-1 ring-gray-200">
          {zh.wiki.empty}
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{zh.wiki.columnTitle}</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{zh.wiki.columnType}</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{zh.wiki.columnSlug}</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{zh.wiki.columnSync}</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">{zh.wiki.columnActions}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {pages.map((page) => (
                <tr key={page.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link href={`/operations/wiki/${page.id}`} className="font-medium text-gray-900 hover:text-blue-700">
                      {page.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{typeLabel[page.wiki_page_type] || page.wiki_page_type}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{page.slug}</td>
                  <td className="px-4 py-3 text-sm">
                    {page.synced ? (
                      <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs text-green-700">{zh.wiki.synced}</span>
                    ) : (
                      <span className="rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">{zh.wiki.draft}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-sm">
                    <Link href={`/operations/wiki/${page.id}`} className="text-blue-600 hover:underline">
                      {zh.wiki.edit}
                    </Link>
                    {page.preview_url && (
                      <a
                        href={page.preview_url}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-3 text-gray-600 hover:underline"
                      >
                        {zh.wiki.preview}
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: typeof BookOpen;
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Icon className={cn("h-4 w-4", color)} />
        {label}
      </div>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}

function FilterChip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full px-3 py-1 text-xs font-medium",
        active ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-600 hover:bg-gray-200",
      )}
    >
      {label}
    </button>
  );
}
