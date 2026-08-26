"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";

type TrashedArticle = { id: number; title: string; status: string; deleted_at: string | null };

export default function ArticleTrashPage() {
  const token = useAuthGuard();
  const [articles, setArticles] = useState<TrashedArticle[]>([]);
  const [flash, setFlash] = useState("");

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ articles: TrashedArticle[] }>("/api/admin/articles/trash", t);
    setArticles(data.articles);
  }, []);

  useEffect(() => {
    if (token) load().catch(() => setFlash("加载失败"));
  }, [token, load]);

  async function restore(id: number) {
    const t = getToken();
    if (!t) return;
    await apiPost(`/api/admin/articles/${id}/restore`, t);
    await load();
  }

  async function purge(id: number) {
    const t = getToken();
    if (!t) return;
    await apiDelete(`/api/admin/articles/${id}/purge`, t);
    await load();
  }

  return (
    <div>
      <HubHeader title={zh.articleTrash.title} subtitle="" />
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      {flash && <FlashAlert variant="error">{flash}</FlashAlert>}
      <div className="mb-4">
        <Link href="/operations/articles" className="text-sm text-blue-600 hover:text-blue-700">← 返回文章列表</Link>
      </div>
      {articles.length === 0 ? (
        <div className="rounded-lg bg-white px-6 py-10 text-center text-sm text-gray-500 shadow-sm ring-1 ring-gray-200">{zh.articleTrash.empty}</div>
      ) : (
        <div className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">标题</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">删除时间</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {articles.map((a) => (
                <tr key={a.id}>
                  <td className="px-4 py-3 text-sm">{a.title}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{a.deleted_at ? new Date(a.deleted_at).toLocaleString("zh-CN") : "—"}</td>
                  <td className="px-4 py-3 text-sm">
                    <button type="button" onClick={() => restore(a.id)} className="mr-2 text-blue-600 hover:text-blue-700">{zh.articleTrash.restore}</button>
                    <button type="button" onClick={() => purge(a.id)} className="text-red-600 hover:text-red-700">{zh.articleTrash.purge}</button>
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
