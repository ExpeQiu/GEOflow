"use client";

import { useCallback, useEffect, useState } from "react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { WikiPanel } from "@/components/operations/WikiPanel";
import { WikiSubNav } from "@/components/operations/WikiSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";
import type { WikiPanelPayload } from "@/lib/wiki-form-types";

export default function WikiListPage() {
  const token = useAuthGuard();
  const [payload, setPayload] = useState<WikiPanelPayload | null>(null);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setError("");
    try {
      const data = await apiGet<WikiPanelPayload>("/api/admin/wiki", t);
      setPayload(data);
    } catch {
      setError("加载 Wiki 列表失败");
    } finally {
      setLoading(false);
    }
  }, []);

  async function onImport() {
    const t = getToken();
    if (!t) return;
    setImporting(true);
    setError("");
    setFlash("");
    try {
      const data = await apiPost<
        WikiPanelPayload & {
          import?: {
            created: number;
            updated: number;
            official_count?: number;
            geoflow_skipped?: number;
          };
        }
      >(
        "/api/admin/wiki/import-geoweb",
        t,
      );
      setPayload(data);
      const result = data.import;
      setFlash(
        zh.wiki.importSuccess(
          result?.created ?? 0,
          result?.updated ?? 0,
          result?.official_count,
          result?.geoflow_skipped,
        ),
      );
    } catch {
      setError(zh.wiki.importError);
    } finally {
      setImporting(false);
    }
  }

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  return (
    <div>
      <HubHeader title={zh.wiki.hubTitle} subtitle={zh.wiki.hubSubtitle} />
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      <WikiSubNav />
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {loading && !payload && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}
      {payload && (
        <WikiPanel
          pages={payload.pages.filter((page) => {
            if (filter !== "all" && page.wiki_page_type !== filter) return false;
            const needle = query.trim().toLowerCase();
            if (!needle) return true;
            return page.title.toLowerCase().includes(needle) || page.slug.toLowerCase().includes(needle);
          })}
          stats={payload.stats}
          typeCounts={payload.type_counts}
          filter={filter}
          query={query}
          onFilterChange={setFilter}
          onQueryChange={setQuery}
          onImport={onImport}
          importing={importing}
        />
      )}
    </div>
  );
}
