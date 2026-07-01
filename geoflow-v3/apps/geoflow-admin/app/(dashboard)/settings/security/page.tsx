"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPut, getToken } from "@/lib/api-client";

export default function SecuritySettingsPage() {
  const token = useAuthGuard();
  const [words, setWords] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<{ words: string }>("/api/admin/settings/security/sensitive-words", t).then((d) => setWords(d.words));
  }, [token]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    await apiPut("/api/admin/settings/security/sensitive-words", t, { words });
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="安全设置" subtitle="敏感词过滤" />
      <Link href="/settings/site" className="mb-4 inline-block text-sm text-gray-600">← 站点设置</Link>
      <form onSubmit={onSubmit} className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
        <label className="text-sm font-medium text-gray-700">敏感词（每行一个）</label>
        <textarea className="mt-2 min-h-[200px] w-full rounded-md border px-3 py-2 text-sm" value={words} onChange={(e) => setWords(e.target.value)} />
        <button type="submit" className="mt-4 rounded-md bg-gray-900 px-4 py-2 text-sm text-white">保存</button>
      </form>
    </div>
  );
}
