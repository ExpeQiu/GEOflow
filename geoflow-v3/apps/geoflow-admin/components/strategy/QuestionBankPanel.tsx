"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { apiPost, getToken } from "@/lib/api-client";
import type { MonitorQuestion, MonitorRun, QueryTemplate } from "@/lib/strategy-types";
import { surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

type SubTab = "questions" | "templates";

export function QuestionBankPanel({
  questions,
  templates = [],
  recentRuns = [],
  onCreate,
  onUpdate,
  onDelete,
  onRefresh,
}: {
  questions: MonitorQuestion[];
  templates?: QueryTemplate[];
  recentRuns?: MonitorRun[];
  onCreate: (body: Record<string, unknown>) => Promise<void>;
  onUpdate: (id: number, body: Record<string, unknown>) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  onRefresh?: () => void;
}) {
  const [tab, setTab] = useState<SubTab>("questions");
  const [form, setForm] = useState({ question_text: "", priority: 50, status: "active", query_type: "brand" });
  const [editId, setEditId] = useState<number | null>(null);
  const [templateForm, setTemplateForm] = useState({ template_type: "brand", category: "", pattern: "{brand}怎么样？" });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.question_text.trim()) return;
    if (editId) await onUpdate(editId, form);
    else await onCreate(form);
    setEditId(null);
    setForm({ question_text: "", priority: 50, status: "active", query_type: "brand" });
  }

  async function createTemplate(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    await apiPost("/api/admin/strategy/monitor/templates", t, templateForm);
    onRefresh?.();
  }

  async function generateFromTemplate(id: number) {
    const t = getToken();
    if (!t) return;
    await apiPost(`/api/admin/strategy/monitor/templates/${id}/generate`, t, {});
    onRefresh?.();
  }

  const brandCount = questions.filter((q) => (q.query_type || "brand") === "brand").length;
  const productCount = questions.filter((q) => q.query_type === "product").length;

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-violet-200 bg-violet-50/40 p-5">
        <h2 className="text-lg font-semibold text-gray-900">监控问题库</h2>
        <p className="mt-1 text-sm text-gray-500">管理品牌/产品探针问题与问题模板</p>
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <span>问题总数 <strong>{questions.length}</strong></span>
          <span>品牌类 <strong>{brandCount}</strong></span>
          <span>产品类 <strong>{productCount}</strong></span>
          <span>模板 <strong>{templates.length}</strong></span>
          <Link href="/strategy/scene-graph" className="text-violet-700 hover:underline">场景图谱 →</Link>
        </div>
      </section>

      <div className="flex flex-wrap gap-2 border-b border-gray-100 pb-2">
        {([
          ["questions", "问题库"],
          ["templates", "问题模板"],
        ] as const).map(([k, label]) => (
          <button
            key={k}
            type="button"
            onClick={() => setTab(k)}
            className={`rounded-md px-3 py-1.5 text-sm ${tab === k ? "bg-violet-600 text-white" : "bg-gray-100 text-gray-700"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "questions" && (
        <>
          <form onSubmit={handleSubmit} className={`flex flex-wrap gap-2 ${surfaceCardClass} p-4`}>
            <input
              className={`min-w-[200px] flex-1 ${surfaceInputClass}`}
              placeholder="监控问题"
              value={form.question_text}
              onChange={(e) => setForm({ ...form, question_text: e.target.value })}
            />
            <select
              className="rounded-md border border-gray-300 px-2 py-2 text-sm"
              value={form.query_type}
              onChange={(e) => setForm({ ...form, query_type: e.target.value })}
            >
              <option value="brand">品牌</option>
              <option value="product">产品</option>
              <option value="competitor">竞品</option>
            </select>
            <input
              type="number"
              className="w-20 rounded-md border border-gray-300 px-2 py-2 text-sm"
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
            />
            <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
              {editId ? "更新" : "添加"}
            </button>
          </form>
          <QuestionTable
            questions={questions}
            onEdit={(q) => {
              setEditId(q.id);
              setForm({
                question_text: q.question_text,
                priority: q.priority,
                status: q.status,
                query_type: q.query_type || "brand",
              });
            }}
            onDelete={onDelete}
          />
        </>
      )}

      {tab === "templates" && (
        <>
          <form onSubmit={createTemplate} className={`flex flex-wrap gap-2 ${surfaceCardClass} p-4`}>
            <select className="rounded-md border border-gray-300 px-2 py-2 text-sm" value={templateForm.template_type} onChange={(e) => setTemplateForm({ ...templateForm, template_type: e.target.value })}>
              <option value="brand">品牌</option>
              <option value="product">产品</option>
              <option value="competitor">竞品</option>
            </select>
            <input className={`min-w-[240px] flex-1 ${surfaceInputClass}`} placeholder="模板 pattern，如 {brand}怎么样？" value={templateForm.pattern} onChange={(e) => setTemplateForm({ ...templateForm, pattern: e.target.value })} />
            <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">添加模板</button>
          </form>
          <ul className="space-y-2">
            {templates.map((t) => (
              <li key={t.id} className={`flex items-center justify-between ${surfaceCardClass} px-4 py-3 text-sm`}>
                <span>[{t.template_type}] {t.pattern}</span>
                <button type="button" className="text-violet-600" onClick={() => generateFromTemplate(t.id)}>生成问题</button>
              </li>
            ))}
          </ul>
        </>
      )}

      {recentRuns.length > 0 && tab === "questions" && (
        <section className={`${surfaceCardClass} p-4 text-sm`}>
          <h3 className="mb-2 font-semibold">最近扫描</h3>
          {recentRuns.slice(0, 5).map((run) => (
            <div key={run.id} className="text-gray-600">
              <Link href={`/strategy/monitor/runs/${run.id}`} className="text-violet-600">#{run.id}</Link>
              {" "}— {run.probe_count} 探针
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

function QuestionTable({
  questions,
  onEdit,
  onDelete,
}: {
  questions: MonitorQuestion[];
  onEdit: (q: MonitorQuestion) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <table className={`min-w-full divide-y divide-gray-100 ${surfaceCardClass} text-sm`}>
      <thead className="bg-gray-50">
        <tr>
          {["问题", "优先级", "类型", "操作"].map((h) => (
            <th key={h} className="px-4 py-2 text-left text-xs">{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {questions.map((q) => (
          <tr key={q.id}>
            <td className="px-4 py-3">{q.question_text}</td>
            <td className="px-4 py-3">{q.priority}</td>
            <td className="px-4 py-3">{q.query_type || "brand"}</td>
            <td className="space-x-2 px-4 py-3">
              <button type="button" className="text-violet-600" onClick={() => onEdit(q)}>编辑</button>
              <button type="button" className="text-red-600" onClick={() => onDelete(q.id)}>删除</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
