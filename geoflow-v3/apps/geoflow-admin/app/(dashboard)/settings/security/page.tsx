"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { SecurityRuntimePanel, type SecurityRuntime } from "@/components/admin/SecurityRuntimePanel";
import { SettingsSubNav } from "@/components/admin/SettingsSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, apiPut, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";

export default function SecuritySettingsPage() {
  const token = useAuthGuard();
  const [words, setWords] = useState("");
  const [runtime, setRuntime] = useState<SecurityRuntime | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [flash, setFlash] = useState("");
  const [error, setError] = useState("");
  const [savingWords, setSavingWords] = useState(false);
  const [savingPwd, setSavingPwd] = useState(false);

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<{ words: string; security_runtime?: SecurityRuntime }>("/api/admin/settings/security/sensitive-words", t)
      .then((d) => {
        setWords(d.words ?? "");
        if (d.security_runtime) setRuntime(d.security_runtime);
      })
      .catch(() => setError("无法加载敏感词"));
  }, [token]);

  const wordCount = useMemo(() => words.split(/\n/).filter((w) => w.trim()).length, [words]);

  async function onSubmitWords(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    setError("");
    setSavingWords(true);
    try {
      await apiPut("/api/admin/settings/security/sensitive-words", t, { words });
      setFlash("敏感词已保存");
    } catch {
      setError("敏感词保存失败（需超级管理员）");
    } finally {
      setSavingWords(false);
    }
  }

  async function onSubmitPassword(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    setError("");
    if (newPassword.length < 6) {
      setError(zh.settings.security.passwordTooShort);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError(zh.settings.security.passwordMismatch);
      return;
    }
    setSavingPwd(true);
    try {
      await apiPost("/api/admin/settings/security/password", t, {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setFlash("密码已修改");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch {
      setError("当前密码错误或修改失败");
    } finally {
      setSavingPwd(false);
    }
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={zh.settings.security.title} subtitle={zh.settings.security.subtitle} />
      <SettingsSubNav />
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      <div className="mb-6">
        <SecurityRuntimePanel runtime={runtime} variant="security" />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={onSubmitWords} className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700">{zh.settings.security.wordsLabel}</label>
            <span className="text-xs text-gray-400">{zh.settings.security.wordsCount(wordCount)}</span>
          </div>
          <p className="mt-1 text-xs text-gray-500">{zh.settings.security.wordsHint}</p>
          <textarea
            className="mt-3 min-h-[220px] w-full rounded-md border px-3 py-2 font-mono text-sm"
            value={words}
            onChange={(e) => setWords(e.target.value)}
          />
          <button type="submit" disabled={savingWords} className="mt-4 rounded-md bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50">
            {zh.settings.security.saveWords}
          </button>
        </form>
        <form onSubmit={onSubmitPassword} className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
          <h2 className="text-sm font-semibold text-gray-900">{zh.settings.security.passwordTitle}</h2>
          <input
            type="password"
            placeholder={zh.settings.security.currentPassword}
            autoComplete="current-password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="mt-4 w-full rounded-md border px-3 py-2 text-sm"
            required
          />
          <input
            type="password"
            placeholder={zh.settings.security.newPassword}
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="mt-2 w-full rounded-md border px-3 py-2 text-sm"
            minLength={6}
            required
          />
          <input
            type="password"
            placeholder={zh.settings.security.confirmPassword}
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="mt-2 w-full rounded-md border px-3 py-2 text-sm"
            minLength={6}
            required
          />
          <button type="submit" disabled={savingPwd} className="mt-4 rounded-md bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-50">
            {zh.settings.security.changePassword}
          </button>
        </form>
      </div>
    </div>
  );
}
