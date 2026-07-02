"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, apiPut, getToken } from "@/lib/api-client";

export default function SecuritySettingsPage() {
  const token = useAuthGuard();
  const [words, setWords] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [flash, setFlash] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<{ words: string }>("/api/admin/settings/security/sensitive-words", t).then((d) => setWords(d.words));
  }, [token]);

  async function onSubmitWords(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    await apiPut("/api/admin/settings/security/sensitive-words", t, { words });
    setFlash("敏感词已保存");
  }

  async function onSubmitPassword(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    setError("");
    try {
      await apiPost("/api/admin/settings/security/password", t, { current_password: currentPassword, new_password: newPassword });
      setFlash("密码已修改");
      setCurrentPassword("");
      setNewPassword("");
    } catch {
      setError("当前密码错误或修改失败");
    }
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title="安全设置" subtitle="敏感词与账号密码" />
      <Link href="/settings/site" className="mb-4 inline-block text-sm text-gray-600">← 站点设置</Link>
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      <form onSubmit={onSubmitWords} className="mb-8 rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
        <label className="text-sm font-medium text-gray-700">敏感词（每行一个）</label>
        <textarea className="mt-2 min-h-[200px] w-full rounded-md border px-3 py-2 text-sm" value={words} onChange={(e) => setWords(e.target.value)} />
        <button type="submit" className="mt-4 rounded-md bg-gray-900 px-4 py-2 text-sm text-white">保存敏感词</button>
      </form>
      <form onSubmit={onSubmitPassword} className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
        <h2 className="text-sm font-semibold text-gray-900">修改密码</h2>
        <input type="password" placeholder="当前密码" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} className="mt-3 w-full rounded-md border px-3 py-2 text-sm" />
        <input type="password" placeholder="新密码（至少 6 位）" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="mt-2 w-full rounded-md border px-3 py-2 text-sm" />
        <button type="submit" className="mt-4 rounded-md bg-emerald-600 px-4 py-2 text-sm text-white">修改密码</button>
      </form>
    </div>
  );
}
