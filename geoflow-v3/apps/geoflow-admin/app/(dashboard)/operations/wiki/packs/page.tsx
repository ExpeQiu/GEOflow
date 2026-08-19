"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { WikiSubNav } from "@/components/operations/WikiSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_NAV } from "@/lib/nav-config";
import type { WikiPage } from "@/lib/wiki-form-types";

type WikiPack = {
  id: number;
  title: string;
  slug: string;
  status: string;
  page_count: number;
  can_sync: boolean;
  blocked: { id: number; slug: string; wiki_page_type: string; errors: string[] }[];
  empty_body: string[];
  pages: WikiPage[];
};

type WikiPacksPayload = {
  packs: WikiPack[];
  unassigned: WikiPage[];
  geoweb_sync_enabled: boolean;
  table_missing?: boolean;
  sync?: { dry_run?: boolean; ok_count?: number };
};

const typeLabel = zh.wiki.types as Record<string, string>;

export default function WikiPacksPage() {
  const token = useAuthGuard();
  const [payload, setPayload] = useState<WikiPacksPayload | null>(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [syncing, setSyncing] = useState<number | null>(null);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    try {
      setPayload(await apiGet<WikiPacksPayload>("/api/admin/wiki/packs", t));
    } catch {
      setError("加载 Theme 包失败");
    }
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSync(themeId: number) {
    const t = getToken();
    if (!t) return;
    setSyncing(themeId);
    setError("");
    setFlash("");
    try {
      const data = await apiPost<WikiPacksPayload>(`/api/admin/wiki/packs/${themeId}/sync-pack`, t);
      setPayload(data);
      setFlash(data.sync?.dry_run ? zh.wiki.syncPackDryRun : zh.wiki.syncPackSuccess);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setError(`${zh.wiki.syncPackError}${msg.includes("·") ? msg.slice(msg.indexOf("·")) : ""}`);
    } finally {
      setSyncing(null);
    }
  }

  return (
    <div>
      <HubHeader title={zh.wiki.packsTitle} subtitle={zh.wiki.packsSubtitle} />
      <HubNav items={OPERATIONS_NAV} tone="blue" />
      <WikiSubNav />
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {!payload && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}
      {payload && payload.packs.length === 0 && (
        <div className="rounded-lg bg-white px-6 py-10 text-center text-sm text-gray-500 shadow-sm ring-1 ring-gray-200">
          {zh.wiki.packsEmpty}
        </div>
      )}
      {payload && (
        <div className="space-y-4">
          {payload.packs.map((pack) => (
            <section key={pack.id} className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-gray-100 px-6 py-4">
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{pack.title}</h3>
                  <p className="mt-1 text-xs text-gray-500">
                    #{pack.id} · {pack.slug} · {pack.status} · {zh.wiki.pageCount} {pack.page_count}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={!pack.can_sync || syncing === pack.id}
                  onClick={() => onSync(pack.id)}
                  className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {syncing === pack.id ? zh.common.loading : pack.can_sync ? zh.wiki.syncPack : zh.wiki.syncBlocked}
                </button>
              </div>
              <div className="px-6 py-4">
                {pack.blocked.length > 0 && (
                  <p className="mb-3 text-sm text-red-700">
                    {zh.wiki.syncBlocked}：{pack.blocked.map((item) => `${item.slug}(${item.errors.join(",")})`).join("、")}
                  </p>
                )}
                {pack.pages.length === 0 ? (
                  <p className="text-sm text-gray-500">尚未挂 Wiki 页</p>
                ) : (
                  <ol className="space-y-2">
                    {pack.pages.map((page, idx) => (
                      <li key={page.id} className="flex items-center justify-between text-sm">
                        <span>
                          <span className="mr-2 font-mono text-xs text-gray-400">{idx + 1}</span>
                          <Link href={`/operations/wiki/${page.id}`} className="text-blue-700 hover:underline">
                            {page.title}
                          </Link>
                          <span className="ml-2 text-xs text-gray-500">
                            {typeLabel[page.wiki_page_type] || page.wiki_page_type} · {page.slug}
                            {page.wiki_page_type === "topic" ? " · hub" : ""}
                          </span>
                        </span>
                        <span className="text-xs text-gray-400">{page.synced ? zh.wiki.synced : zh.wiki.draft}</span>
                      </li>
                    ))}
                  </ol>
                )}
              </div>
            </section>
          ))}
          {payload.unassigned.length > 0 && (
            <section className="rounded-lg bg-white px-6 py-4 shadow-sm ring-1 ring-gray-200">
              <h3 className="mb-3 text-sm font-medium text-gray-700">{zh.wiki.packsUnassigned}</h3>
              <ul className="space-y-1 text-sm">
                {payload.unassigned.map((page) => (
                  <li key={page.id}>
                    <Link href={`/operations/wiki/${page.id}`} className="text-blue-700 hover:underline">
                      {page.title}
                    </Link>
                    <span className="ml-2 text-xs text-gray-500">{page.slug}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
