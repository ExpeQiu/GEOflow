"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { zh } from "@/lib/i18n/zh";
import { apiGet, apiPatch, getToken } from "@/lib/api-client";
import type { MonitorKpis, MonitorProbe, MonitorQuestion, MonitorRun, MonitorSettings } from "@/lib/strategy-types";

export function MonitorPanel({
  dashboard,
  questions,
  recentRuns = [],
  recentProbes = [],
  onScan,
  scanning,
  onCreate,
  onUpdate,
  onDelete,
}: {
  dashboard: MonitorKpis;
  questions: MonitorQuestion[];
  recentRuns?: MonitorRun[];
  recentProbes?: MonitorProbe[];
  onScan: () => void;
  scanning: boolean;
  onCreate: (body: { question_text: string; priority: number; status: string }) => Promise<void>;
  onUpdate: (id: number, body: { question_text: string; priority: number; status: string }) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}) {
  const [form, setForm] = useState({ question_text: "", priority: 50, status: "active" });
  const [editId, setEditId] = useState<number | null>(null);
  const [settings, setSettings] = useState<MonitorSettings | null>(null);
  const [settingsForm, setSettingsForm] = useState({ brand_name: "", brand_aliases: "", probe_mode: "corpus" as "corpus" | "llm" });
  const [settingsMsg, setSettingsMsg] = useState("");
  const [savingSettings, setSavingSettings] = useState(false);

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<MonitorSettings>("/api/admin/strategy/monitor/settings", t).then((s) => {
      setSettings(s);
      setSettingsForm({ brand_name: s.brand_name, brand_aliases: s.brand_aliases, probe_mode: s.probe_mode });
    }).catch(() => {});
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.question_text.trim()) return;
    if (editId) {
      await onUpdate(editId, form);
      setEditId(null);
    } else {
      await onCreate(form);
    }
    setForm({ question_text: "", priority: 50, status: "active" });
  }

  async function saveSettings(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    setSavingSettings(true);
    setSettingsMsg("");
    try {
      const saved = await apiPatch<MonitorSettings>("/api/admin/strategy/monitor/settings", t, settingsForm);
      setSettings(saved);
      setSettingsMsg("探针设置已保存");
    } catch {
      setSettingsMsg("保存失败");
    } finally {
      setSavingSettings(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-violet-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">{zh.strategy.monitor.dashboardTitle}</h2>
            <p className="text-sm text-gray-500">{zh.strategy.monitor.dashboardSubtitle}</p>
          </div>
          <button
            type="button"
            disabled={scanning}
            onClick={onScan}
            className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
          >
            {zh.strategy.monitor.scanAll}
          </button>
        </div>
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Kpi label={zh.strategy.monitor.kpiQuestions} value={dashboard.question_count} tone="violet" />
          <Kpi label={zh.strategy.monitor.kpiProbes} value={dashboard.probe_count} />
          <Kpi label="平均排名" value={dashboard.avg_brand_rank ?? "—"} />
          <Kpi label="提及率" value={`${Math.round(dashboard.mention_rate * 100)}%`} />
        </div>
        {dashboard.platform_summary.length > 0 && (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-xs text-gray-600">
              <thead>
                <tr>
                  {["平台", "探针数", "提及", "均排名"].map((h) => (
                    <th key={h} className="px-2 py-1 text-left font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dashboard.platform_summary.map((p) => (
                  <tr key={p.platform}>
                    <td className="px-2 py-1">{p.platform}</td>
                    <td className="px-2 py-1">{p.total}</td>
                    <td className="px-2 py-1">{p.mentions}</td>
                    <td className="px-2 py-1">{p.avg_rank ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {settings && (
        <form onSubmit={saveSettings} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold text-gray-900">探针与品牌设置</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <input
              className="rounded-md border px-3 py-2 text-sm"
              placeholder="品牌名称"
              value={settingsForm.brand_name}
              onChange={(e) => setSettingsForm({ ...settingsForm, brand_name: e.target.value })}
            />
            <input
              className="rounded-md border px-3 py-2 text-sm md:col-span-2"
              placeholder="品牌别名（逗号分隔）"
              value={settingsForm.brand_aliases}
              onChange={(e) => setSettingsForm({ ...settingsForm, brand_aliases: e.target.value })}
            />
            <select
              className="rounded-md border px-3 py-2 text-sm"
              value={settingsForm.probe_mode}
              onChange={(e) => setSettingsForm({ ...settingsForm, probe_mode: e.target.value as "corpus" | "llm" })}
            >
              <option value="corpus">语料启发式（默认）</option>
              <option value="llm">LLM 模拟平台回答</option>
            </select>
            <button
              type="submit"
              disabled={savingSettings}
              className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              保存设置
            </button>
            <p className="text-xs text-gray-500 self-center">
              {settings.ai_mock_mode ? "AI_MOCK_MODE 开启时 LLM 探针将回退语料模式" : "LLM 模式使用前 5 个高优先级问题"}
            </p>
          </div>
          {settingsMsg && <p className="mt-2 text-xs text-violet-700">{settingsMsg}</p>}
        </form>
      )}

      {recentRuns.length > 0 && (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold text-gray-900">最近扫描</h3>
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["ID", "平台", "问题数", "探针", "状态", "完成时间"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recentRuns.map((run) => (
                <tr key={run.id}>
                  <td className="px-3 py-2">
                    <Link href={`/strategy/monitor/runs/${run.id}`} className="text-violet-600 hover:underline">
                      #{run.id}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{run.platform || "—"}</td>
                  <td className="px-3 py-2">{run.question_count}</td>
                  <td className="px-3 py-2">{run.probe_count ?? "—"}</td>
                  <td className="px-3 py-2">{run.status}</td>
                  <td className="px-3 py-2 text-gray-500">{run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {recentProbes.length > 0 && (
        <section className="rounded-lg border border-violet-100 bg-violet-50/30 p-4 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold text-gray-900">最近探针结果</h3>
          <ul className="max-h-64 space-y-2 overflow-y-auto text-sm">
            {recentProbes.map((p) => (
              <li key={p.id} className="rounded-md bg-white px-3 py-2 ring-1 ring-violet-100">
                <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                  <span className="font-medium text-violet-700">{p.platform}</span>
                  <span>{p.mentioned ? `排名 #${p.brand_rank}` : "未提及"}</span>
                </div>
                <p className="mt-1 line-clamp-2 text-gray-700">{p.question_text}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <form onSubmit={handleSubmit} className="flex flex-wrap gap-2 rounded-lg border bg-white p-4 shadow-sm">
        <input
          className="min-w-[200px] flex-1 rounded-md border px-3 py-2 text-sm"
          placeholder="监控问题"
          value={form.question_text}
          onChange={(e) => setForm({ ...form, question_text: e.target.value })}
        />
        <input
          type="number"
          min={0}
          max={100}
          className="w-20 rounded-md border px-2 py-2 text-sm"
          value={form.priority}
          onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
        />
        <select className="rounded-md border px-2 py-2 text-sm" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
          <option value="active">active</option>
          <option value="paused">paused</option>
        </select>
        <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">{editId ? "更新" : "添加"}</button>
        {editId && (
          <button type="button" onClick={() => { setEditId(null); setForm({ question_text: "", priority: 50, status: "active" }); }} className="rounded-md border px-3 py-2 text-sm">取消</button>
        )}
      </form>

      <section className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <div className="border-b px-4 py-3 text-sm font-semibold text-gray-900">{zh.strategy.monitor.questionsTitle}</div>
        {questions.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-gray-500">{zh.strategy.monitor.emptyQuestions}</div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                {["问题", "优先级", "状态", "操作"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {questions.map((q) => (
                <tr key={q.id}>
                  <td className="px-4 py-3">{q.question_text}</td>
                  <td className="px-4 py-3">{q.priority}</td>
                  <td className="px-4 py-3">{q.status}</td>
                  <td className="px-4 py-3 space-x-2">
                    <button type="button" className="text-violet-600" onClick={() => { setEditId(q.id); setForm({ question_text: q.question_text, priority: q.priority, status: q.status }); }}>编辑</button>
                    <button type="button" className="text-red-600" onClick={() => onDelete(q.id)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string | number; tone?: "violet" }) {
  const cls = tone === "violet" ? "bg-violet-50" : "bg-gray-50";
  return (
    <div className={`rounded-md p-4 ${cls}`}>
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}
