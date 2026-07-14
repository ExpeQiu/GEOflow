"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { AiConfigSubNav } from "@/components/production/AiConfigSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_NAV } from "@/lib/nav-config";

type ModelRow = {
  id: number;
  name: string;
  model_id: string;
  model_type: string;
  api_url: string;
  status: string;
  has_api_key: boolean;
};

const EMPTY_FORM = {
  name: "",
  model_id: "",
  api_key: "",
  api_url: "https://api.openai.com/v1",
  model_type: "chat",
};

export default function AiModelsPage() {
  const token = useAuthGuard();
  const [items, setItems] = useState<ModelRow[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editId, setEditId] = useState<number | null>(null);
  const [testMsg, setTestMsg] = useState("");

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: ModelRow[] }>("/api/admin/ai-models", t);
    setItems(data.items);
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    const payload = { ...form };
    if (editId) {
      if (!payload.api_key) {
        const { api_key: _removed, ...rest } = payload;
        await apiPatch(`/api/admin/ai-models/${editId}`, t, rest);
      } else {
        await apiPatch(`/api/admin/ai-models/${editId}`, t, payload);
      }
      setEditId(null);
    } else {
      await apiPost("/api/admin/ai-models", t, payload);
    }
    setForm(EMPTY_FORM);
    await load();
  }

  async function onDelete(id: number) {
    const t = getToken();
    if (!t || !confirm("确认删除？")) return;
    await apiDelete(`/api/admin/ai-models/${id}`, t);
    await load();
  }

  async function onTest(id: number) {
    const t = getToken();
    if (!t) return;
    const res = await apiPost<{ ok: boolean; message: string; mock?: boolean }>(`/api/admin/ai-models/${id}/test`, t);
    setTestMsg(res.mock ? "Mock 模式：连接 OK" : res.message);
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={zh.production.tabs.ai_config} subtitle={zh.production.aiConfigSub.models} />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <AiConfigSubNav />
      {testMsg && <FlashAlert variant="success">{testMsg}</FlashAlert>}
      <form onSubmit={onSubmit} className="mb-6 space-y-2 rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
        <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
          <input className="rounded-md border px-3 py-2 text-sm" placeholder="显示名" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input className="rounded-md border px-3 py-2 text-sm" placeholder="model_id" value={form.model_id} onChange={(e) => setForm({ ...form, model_id: e.target.value })} />
          <select className="rounded-md border px-3 py-2 text-sm" value={form.model_type} onChange={(e) => setForm({ ...form, model_type: e.target.value })}>
            <option value="chat">Chat（正文生成）</option>
            <option value="embedding">Embedding（知识库 RAG）</option>
          </select>
          <input className="rounded-md border px-3 py-2 text-sm md:col-span-2" placeholder="API URL" value={form.api_url} onChange={(e) => setForm({ ...form, api_url: e.target.value })} />
          <input className="rounded-md border px-3 py-2 text-sm" placeholder={editId ? "api_key（留空不修改）" : "api_key"} value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} />
        </div>
        <button type="submit" className="rounded-md bg-emerald-600 px-3 py-2 text-sm text-white">{editId ? "更新" : "添加"}</button>
      </form>
      <ul className="divide-y divide-gray-100 rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        {items.map((m) => (
          <li key={m.id} className="flex items-center justify-between px-4 py-3 text-sm">
            <span>
              {m.name} · {m.model_id} · <span className="text-gray-500">{m.model_type}</span> · {m.status}
              {m.has_api_key ? "" : " · 无 Key"}
            </span>
            <span className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setEditId(m.id);
                  setForm({ name: m.name, model_id: m.model_id, api_key: "", api_url: m.api_url, model_type: m.model_type });
                }}
                className="text-emerald-700"
              >
                编辑
              </button>
              <button type="button" onClick={() => onTest(m.id)} className="text-blue-600">测试</button>
              <button type="button" onClick={() => onDelete(m.id)} className="text-red-600">删除</button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
