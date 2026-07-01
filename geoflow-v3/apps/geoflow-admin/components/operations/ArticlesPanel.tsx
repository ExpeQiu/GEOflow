"use client";

import Link from "next/link";
import { FileText, Globe, Inbox, PenLine, Pencil } from "lucide-react";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";
import type { AdminArticle, ArticleStats } from "@/lib/operations-types";

export function ArticlesPanel({
  articles,
  stats,
  filter,
  onFilterChange,
  onReview,
  onPublish,
  onTrash,
  busyId,
}: {
  articles: AdminArticle[];
  stats: ArticleStats;
  filter: "all" | "pending";
  onFilterChange: (f: "all" | "pending") => void;
  onReview: (id: number) => void;
  onPublish: (id: number) => void;
  onTrash: (id: number) => void;
  busyId: number | null;
}) {
  return (
    <div>
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat icon={FileText} label={zh.articles.statsTotal} value={stats.total} color="text-blue-600" />
        <Stat icon={Globe} label={zh.articles.statsPublished} value={stats.published} color="text-green-600" />
        <Stat icon={PenLine} label={zh.articles.statsDraft} value={stats.draft} color="text-amber-600" />
        <Stat icon={Inbox} label={zh.articles.statsPending} value={stats.pending_review} color="text-violet-600" />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <FilterChip active={filter === "all"} onClick={() => onFilterChange("all")} label={zh.articles.filterAll} />
        <FilterChip active={filter === "pending"} onClick={() => onFilterChange("pending")} label={zh.articles.filterPending} />
        <Link href="/operations/articles/new" className="ml-auto rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700">
          {zh.articles.createButton}
        </Link>
        <Link href="/operations/articles/trash" className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">
          {zh.articles.trashLink}
        </Link>
      </div>

      {articles.length === 0 ? (
        <div className="rounded-lg bg-white px-6 py-10 text-center text-sm text-gray-500 shadow-sm ring-1 ring-gray-200">
          {zh.articles.empty}
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          <div className="overflow-x-auto">
            <table className="min-w-[900px] w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {[zh.articles.columnTitle, zh.articles.columnStatus, zh.articles.columnReview, zh.articles.columnEval, zh.articles.columnViews, zh.articles.columnActions].map(
                    (h) => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {articles.map((article) => (
                  <tr key={article.id} className="hover:bg-gray-50">
                    <td className="max-w-xs px-4 py-3 text-sm font-medium text-gray-900">
                      <Link href={`/operations/articles/${article.id}`} className="group block">
                        <div className="line-clamp-2 group-hover:text-blue-700">{article.title}</div>
                        <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
                          <span>#{article.id}</span>
                          <Pencil className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
                        </div>
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <Badge value={article.status} />
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <Badge value={article.review_status} tone={article.review_status === "pending" ? "amber" : "green"} />
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{article.eval_status}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{article.view_count}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <Link
                          href={`/operations/articles/${article.id}`}
                          className="rounded-md border border-gray-300 px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                        >
                          {zh.articles.actionEdit}
                        </Link>
                        {article.review_status === "pending" && (
                          <ActionBtn disabled={busyId === article.id} onClick={() => onReview(article.id)}>
                            {zh.articles.actionReview}
                          </ActionBtn>
                        )}
                        {article.status !== "published" && article.review_status === "approved" && (
                          <ActionBtn disabled={busyId === article.id} onClick={() => onPublish(article.id)} primary>
                            {zh.articles.actionPublish}
                          </ActionBtn>
                        )}
                        <ActionBtn disabled={busyId === article.id} onClick={() => onTrash(article.id)} danger>
                          {zh.articles.actionTrash}
                        </ActionBtn>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ icon: Icon, label, value, color }: { icon: typeof FileText; label: string; value: number; color: string }) {
  return (
    <div className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center p-5">
        <Icon className={cn("h-6 w-6", color)} />
        <div className="ml-4">
          <div className="text-sm text-gray-500">{label}</div>
          <div className="text-2xl font-semibold text-gray-900">{value}</div>
        </div>
      </div>
    </div>
  );
}

function FilterChip({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-blue-100 text-blue-800" : "text-gray-600 hover:bg-gray-100",
      )}
    >
      {label}
    </button>
  );
}

function Badge({ value, tone }: { value: string; tone?: "amber" | "green" }) {
  const cls =
    tone === "amber"
      ? "bg-amber-50 text-amber-700"
      : tone === "green"
        ? "bg-emerald-50 text-emerald-700"
        : "bg-slate-100 text-slate-700";
  return <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium", cls)}>{value}</span>;
}

function ActionBtn({
  children,
  onClick,
  disabled,
  primary,
  danger,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  primary?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "rounded-md px-2 py-1 text-xs font-medium disabled:opacity-50",
        primary && "bg-blue-600 text-white hover:bg-blue-700",
        danger && "border border-red-200 text-red-700 hover:bg-red-50",
        !primary && !danger && "border border-gray-300 text-gray-700 hover:bg-gray-50",
      )}
    >
      {children}
    </button>
  );
}
