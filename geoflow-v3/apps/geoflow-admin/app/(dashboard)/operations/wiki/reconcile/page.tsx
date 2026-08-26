"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { WikiSubNav } from "@/components/operations/WikiSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";

type ReconRow = {
  slug: string;
  title?: string;
  wiki_page_type?: string;
  id?: number;
  url?: string;
  local_hash?: string | null;
  remote_hash?: string | null;
};

type ReconPayload = {
  matched: ReconRow[];
  hash_mismatch: ReconRow[];
  local_only: ReconRow[];
  remote_only: ReconRow[];
  stats: {
    local: number;
    remote: number;
    matched: number;
    hash_mismatch: number;
    local_only: number;
    remote_only: number;
  };
  pages_json: string;
};

export default function WikiReconcilePage() {
  const token = useAuthGuard();
  const [payload, setPayload] = useState<ReconPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setError("");
    try {
      setPayload(await apiGet<ReconPayload>("/api/admin/wiki/reconcile", t));
    } catch {
      setError(zh.wiki.reconcileError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  return (
    <div>
      <HubHeader title={zh.wiki.reconcileTitle} subtitle={zh.wiki.reconcileSubtitle} />
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      <WikiSubNav />
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {loading && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}
      {payload && (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <Stat label={zh.wiki.reconcileMatched} value={payload.stats.matched} />
            <Stat label={zh.wiki.reconcileHash} value={payload.stats.hash_mismatch} warn />
            <Stat label={zh.wiki.reconcileLocalOnly} value={payload.stats.local_only} />
            <Stat label={zh.wiki.reconcileRemoteOnly} value={payload.stats.remote_only} />
            <button
              type="button"
              onClick={load}
              className="ml-auto rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              {zh.wiki.reconcileRefresh}
            </button>
          </div>
          <p className="mb-4 text-xs text-gray-500">{payload.pages_json}</p>
          <ReconTable title={zh.wiki.reconcileHash} rows={payload.hash_mismatch} />
          <ReconTable title={zh.wiki.reconcileLocalOnly} rows={payload.local_only} local />
          <ReconTable title={zh.wiki.reconcileRemoteOnly} rows={payload.remote_only} />
          <ReconTable title={zh.wiki.reconcileMatched} rows={payload.matched} />
        </>
      )}
    </div>
  );
}

function Stat({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <div className="rounded-lg bg-white px-4 py-3 shadow-sm ring-1 ring-gray-200">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`text-xl font-semibold ${warn && value ? "text-amber-600" : "text-gray-900"}`}>{value}</p>
    </div>
  );
}

function ReconTable({ title, rows, local }: { title: string; rows: ReconRow[]; local?: boolean }) {
  if (!rows.length) return null;
  return (
    <section className="mb-4 overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
      <h3 className="border-b border-gray-100 px-6 py-3 text-sm font-medium text-gray-900">
        {title} ({rows.length})
      </h3>
      <ul className="divide-y divide-gray-50 px-6 py-2 text-sm">
        {rows.map((row) => (
          <li key={row.slug} className="flex items-center justify-between py-2">
            <span>
              {row.id ? (
                <Link href={`/operations/wiki/${row.id}`} className="text-blue-700 hover:underline">
                  {row.title || row.slug}
                </Link>
              ) : (
                <span>{row.title || row.slug}</span>
              )}
              <span className="ml-2 font-mono text-xs text-gray-500">{row.slug}</span>
            </span>
            {row.url && !local ? (
              <a href={row.url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline">
                {zh.wiki.preview}
              </a>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
