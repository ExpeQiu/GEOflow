"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";

type TokenRow = {
  id: number;
  name: string;
  token_prefix: string;
  scopes: string[];
  revoked_at: string | null;
};

export default function ApiTokensPage() {
  const token = useAuthGuard();
  const [items, setItems] = useState<TokenRow[]>([]);
  const [name, setName] = useState("default");
  const [createdToken, setCreatedToken] = useState("");

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: TokenRow[] }>("/api/admin/settings/api-tokens", t);
    setItems(data.items);
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    const res = await apiPost<{ item: { token: string } }>("/api/admin/settings/api-tokens", t, { name, scopes: [] });
    setCreatedToken(res.item.token);
    setName("default");
    await load();
  }

  async function onRevoke(id: number) {
    const t = getToken();
    if (!t || !confirm("确认吊销此 Token？")) return;
    await apiPost(`/api/admin/settings/api-tokens/${id}/revoke`, t);
    await load();
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="API Token" subtitle="外部集成访问令牌" />
      <Link href="/settings/site" className="mb-4 inline-block text-sm text-gray-600">← 站点设置</Link>
      {createdToken && (
        <FlashAlert variant="success">
          新 Token（仅显示一次）：<code className="break-all">{createdToken}</code>
        </FlashAlert>
      )}
      <form onSubmit={onCreate} className="mb-6 flex gap-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <input className="rounded-md border px-3 py-2 text-sm" placeholder="名称" value={name} onChange={(e) => setName(e.target.value)} />
        <button type="submit" className="rounded-md bg-gray-900 px-4 py-2 text-sm text-white">创建</button>
      </form>
      <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        {items.map((row) => (
          <li key={row.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>
              {row.name} · {row.token_prefix}…
              {row.revoked_at && <span className="ml-2 text-red-600">已吊销</span>}
            </span>
            {!row.revoked_at && (
              <button type="button" onClick={() => onRevoke(row.id)} className="text-red-600">吊销</button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
