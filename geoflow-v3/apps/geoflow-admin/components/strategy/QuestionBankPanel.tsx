"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import type {
  CompetitorBrand,
  MonitorQuestion,
  MonitorQuestionBulkResult,
  MonitorQuestionListPage,
  MonitorRun,
  MonitorScene,
  QueryTemplate,
} from "@/lib/strategy-types";
import { QuestionProbeDetail } from "./QuestionProbeDetail";
import { surfaceCardClass, surfaceInputClass } from "./shared/AivisPrimitives";

type SubTab = "questions" | "templates" | "import";
type QueryType = "brand" | "product" | "competitor";

type QuestionForm = {
  question_text: string;
  priority: number;
  status: "active" | "paused";
  query_type: QueryType;
  scene_id: number | null;
  competitor_brands: string[];
};

const EMPTY_FORM: QuestionForm = {
  question_text: "",
  priority: 50,
  status: "active",
  query_type: "brand",
  scene_id: null,
  competitor_brands: [],
};

const QUERY_TYPE_LABEL: Record<QueryType, string> = {
  brand: "品牌",
  product: "产品",
  competitor: "竞品",
};

const CSV_SAMPLE = `question_text,priority,query_type,status,scene_id,competitor_brands
吉利汽车口碑怎么样,90,brand,active,,比亚迪|长安
20万纯电轿车智驾怎么选,85,competitor,active,,小鹏|比亚迪`;

const selectClass = "rounded-md border border-gray-300 px-2 py-2 text-sm";
const PAGE_SIZE = 20;

function buildListUrl(params: {
  page: number;
  filterType: string;
  filterStatus: string;
  filterSceneId: string;
  search: string;
}) {
  const q = new URLSearchParams({
    page: String(params.page),
    page_size: String(PAGE_SIZE),
  });
  if (params.filterType !== "all") q.set("query_type", params.filterType);
  if (params.filterStatus !== "all") q.set("status", params.filterStatus);
  if (params.filterSceneId) q.set("scene_id", params.filterSceneId);
  if (params.search.trim()) q.set("search", params.search.trim());
  return `/api/admin/strategy/monitor/questions?${q.toString()}`;
}

export function QuestionBankPanel({
  scenes = [],
  competitors = [],
  brandName = "",
  templates = [],
  recentRuns = [],
  onCreate,
  onUpdate,
  onDelete,
  onRefresh,
}: {
  scenes?: MonitorScene[];
  competitors?: CompetitorBrand[];
  brandName?: string;
  templates?: QueryTemplate[];
  recentRuns?: MonitorRun[];
  onCreate: (body: Record<string, unknown>) => Promise<void>;
  onUpdate: (id: number, body: Record<string, unknown>) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  onRefresh?: () => void;
}) {
  const [tab, setTab] = useState<SubTab>("questions");
  const [form, setForm] = useState<QuestionForm>(EMPTY_FORM);
  const [editId, setEditId] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [listData, setListData] = useState<MonitorQuestionListPage | null>(null);
  const [listLoading, setListLoading] = useState(false);
  const [filterType, setFilterType] = useState<"all" | QueryType>("all");
  const [filterStatus, setFilterStatus] = useState<"all" | "active" | "paused">("all");
  const [filterSceneId, setFilterSceneId] = useState("");
  const [search, setSearch] = useState("");
  const [probeQuestion, setProbeQuestion] = useState<MonitorQuestion | null>(null);
  const [csvText, setCsvText] = useState(CSV_SAMPLE);
  const [importMsg, setImportMsg] = useState("");
  const [importing, setImporting] = useState(false);
  const [templateForm, setTemplateForm] = useState({ template_type: "brand", category: "", pattern: "{brand}怎么样？" });

  const sceneMap = useMemo(() => new Map(scenes.map((s) => [s.id, s.scene_name])), [scenes]);
  const rivalOptions = useMemo(
    () => competitors.filter((c) => !c.is_self && c.status === "active").map((c) => c.brand_name),
    [competitors],
  );

  const questions = listData?.items ?? [];
  const stats = listData?.stats;
  const totalPages = listData ? Math.max(1, Math.ceil(listData.total / PAGE_SIZE)) : 1;

  const loadQuestions = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setListLoading(true);
    try {
      const data = await apiGet<MonitorQuestionListPage>(
        buildListUrl({ page, filterType, filterStatus, filterSceneId, search }),
        t,
      );
      setListData(data);
    } catch {
      setListData(null);
    } finally {
      setListLoading(false);
    }
  }, [page, filterType, filterStatus, filterSceneId, search]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  function resetFilters() {
    setFilterType("all");
    setFilterStatus("all");
    setFilterSceneId("");
    setSearch("");
    setPage(1);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.question_text.trim()) return;
    const body = { ...form, scene_id: form.scene_id, competitor_brands: form.competitor_brands };
    if (editId) await onUpdate(editId, body);
    else await onCreate(body);
    setEditId(null);
    setForm(EMPTY_FORM);
    await loadQuestions();
    onRefresh?.();
  }

  function cancelEdit() {
    setEditId(null);
    setForm(EMPTY_FORM);
  }

  function toggleCompetitor(name: string) {
    setForm((prev) => ({
      ...prev,
      competitor_brands: prev.competitor_brands.includes(name)
        ? prev.competitor_brands.filter((c) => c !== name)
        : [...prev.competitor_brands, name],
    }));
  }

  async function handleDelete(id: number) {
    await onDelete(id);
    await loadQuestions();
    onRefresh?.();
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
    await loadQuestions();
    onRefresh?.();
  }

  async function handleBulkImport(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !csvText.trim()) return;
    setImporting(true);
    setImportMsg("");
    try {
      const res = await apiPost<MonitorQuestionBulkResult>("/api/admin/strategy/monitor/questions/bulk", t, {
        csv_text: csvText,
        skip_duplicates: true,
      });
      setImportMsg(`导入完成：新增 ${res.created} 条，跳过重复 ${res.skipped} 条${res.errors.length ? `，失败 ${res.errors.length} 条` : ""}`);
      await loadQuestions();
      onRefresh?.();
      if (res.created > 0) setTab("questions");
    } catch {
      setImportMsg("导入失败，请检查 CSV 格式");
    } finally {
      setImporting(false);
    }
  }

  function handleCsvFile(file: File | null) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setCsvText(String(reader.result ?? ""));
    reader.readAsText(file);
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-violet-200 bg-violet-50/40 p-5">
        <h2 className="text-lg font-semibold text-gray-900">监控问题库</h2>
        <p className="mt-1 text-sm text-gray-500">
          管理品牌/产品探针问题与问题模板
          {brandName ? ` · 监控品牌：${brandName}` : ""}
        </p>
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          <span>
            问题总数 <strong>{stats?.total ?? "—"}</strong>
          </span>
          <span>启用 <strong>{stats?.active ?? "—"}</strong></span>
          <span>品牌类 <strong>{stats?.brand ?? "—"}</strong></span>
          <span>产品类 <strong>{stats?.product ?? "—"}</strong></span>
          <span>竞品类 <strong>{stats?.competitor ?? "—"}</strong></span>
          <span>模板 <strong>{templates.length}</strong></span>
          <Link href="/strategy/scene-graph" className="text-violet-700 hover:underline">
            场景图谱 →
          </Link>
        </div>
      </section>

      <div className="flex flex-wrap gap-2 border-b border-gray-100 pb-2">
        {([
          ["questions", "问题库"],
          ["templates", "问题模板"],
          ["import", "批量导入"],
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
          <form onSubmit={handleSubmit} className={`space-y-3 ${surfaceCardClass} p-4`}>
            <div className="flex flex-wrap gap-2">
              <input
                className={`min-w-[240px] flex-1 ${surfaceInputClass}`}
                placeholder="监控问题，如：20万纯电轿车智驾怎么选？"
                value={form.question_text}
                onChange={(e) => setForm({ ...form, question_text: e.target.value })}
              />
              <select
                className={selectClass}
                value={form.query_type}
                onChange={(e) => setForm({ ...form, query_type: e.target.value as QueryType })}
              >
                <option value="brand">品牌</option>
                <option value="product">产品</option>
                <option value="competitor">竞品</option>
              </select>
              <input
                type="number"
                min={0}
                max={100}
                className={`w-20 ${selectClass}`}
                title="优先级 0-100"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
              />
              <select
                className={selectClass}
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value as "active" | "paused" })}
              >
                <option value="active">启用</option>
                <option value="paused">暂停</option>
              </select>
              <select
                className={selectClass}
                value={form.scene_id ?? ""}
                onChange={(e) => setForm({ ...form, scene_id: e.target.value ? Number(e.target.value) : null })}
              >
                <option value="">不关联场景</option>
                {scenes.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.scene_name}
                  </option>
                ))}
              </select>
              <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
                {editId ? "更新" : "添加"}
              </button>
              {editId && (
                <button type="button" onClick={cancelEdit} className="rounded-md border border-gray-300 px-4 py-2 text-sm">
                  取消
                </button>
              )}
            </div>
            {rivalOptions.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <span className="text-gray-500">对标竞品：</span>
                {rivalOptions.map((name) => (
                  <label key={name} className="inline-flex cursor-pointer items-center gap-1 rounded-md bg-gray-50 px-2 py-1">
                    <input
                      type="checkbox"
                      checked={form.competitor_brands.includes(name)}
                      onChange={() => toggleCompetitor(name)}
                    />
                    {name}
                  </label>
                ))}
              </div>
            )}
          </form>

          <div className="flex flex-wrap items-center gap-2 text-sm">
            <input
              className={`min-w-[160px] flex-1 ${surfaceInputClass}`}
              placeholder="搜索问题关键词"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
            <select
              className={selectClass}
              value={filterType}
              onChange={(e) => {
                setFilterType(e.target.value as typeof filterType);
                setPage(1);
              }}
            >
              <option value="all">全部类型</option>
              <option value="brand">品牌</option>
              <option value="product">产品</option>
              <option value="competitor">竞品</option>
            </select>
            <select
              className={selectClass}
              value={filterStatus}
              onChange={(e) => {
                setFilterStatus(e.target.value as typeof filterStatus);
                setPage(1);
              }}
            >
              <option value="all">全部状态</option>
              <option value="active">仅启用</option>
              <option value="paused">仅暂停</option>
            </select>
            <select
              className={selectClass}
              value={filterSceneId}
              onChange={(e) => {
                setFilterSceneId(e.target.value);
                setPage(1);
              }}
            >
              <option value="">全部场景</option>
              {scenes.map((s) => (
                <option key={s.id} value={String(s.id)}>
                  {s.scene_name}
                </option>
              ))}
            </select>
            <button type="button" onClick={resetFilters} className="text-violet-600">
              重置
            </button>
            <span className="text-gray-500">
              {listLoading ? "加载中…" : `共 ${listData?.total ?? 0} 条`}
            </span>
          </div>

          <QuestionTable
            questions={questions}
            sceneMap={sceneMap}
            onEdit={(q) => {
              setEditId(q.id);
              setForm({
                question_text: q.question_text,
                priority: q.priority,
                status: (q.status === "paused" ? "paused" : "active") as "active" | "paused",
                query_type: (q.query_type || "brand") as QueryType,
                scene_id: q.scene_id ?? null,
                competitor_brands: q.competitor_brands ?? [],
              });
            }}
            onDelete={handleDelete}
            onViewProbes={setProbeQuestion}
          />

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 text-sm">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
              >
                上一页
              </button>
              <span>
                第 {page} / {totalPages} 页
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded border border-gray-300 px-3 py-1 disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}

      {tab === "templates" && (
        <>
          <form onSubmit={createTemplate} className={`flex flex-wrap gap-2 ${surfaceCardClass} p-4`}>
            <select
              className={selectClass}
              value={templateForm.template_type}
              onChange={(e) => setTemplateForm({ ...templateForm, template_type: e.target.value })}
            >
              <option value="brand">品牌</option>
              <option value="product">产品</option>
              <option value="competitor">竞品</option>
            </select>
            <input
              className={`min-w-[240px] flex-1 ${surfaceInputClass}`}
              placeholder="模板 pattern，如 {brand}和{competitor}哪个更好？"
              value={templateForm.pattern}
              onChange={(e) => setTemplateForm({ ...templateForm, pattern: e.target.value })}
            />
            <button type="submit" className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white">
              添加模板
            </button>
          </form>
          <p className="text-xs text-gray-500">
            占位符：{"{brand}"} {"{product}"} {"{competitor}"} {"{scene}"} — 生成时自动填入品牌名与竞品库
          </p>
          <ul className="space-y-2">
            {templates.map((t) => (
              <li key={t.id} className={`flex items-center justify-between ${surfaceCardClass} px-4 py-3 text-sm`}>
                <span>
                  [{t.template_type}] {t.pattern}
                </span>
                <button type="button" className="text-violet-600" onClick={() => generateFromTemplate(t.id)}>
                  生成问题
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {tab === "import" && (
        <form onSubmit={handleBulkImport} className={`space-y-3 ${surfaceCardClass} p-4`}>
          <p className="text-sm text-gray-600">
            CSV 列：<code className="text-xs">question_text,priority,query_type,status,scene_id,competitor_brands</code>
            （竞品用 <code className="text-xs">|</code> 或 <code className="text-xs">,</code> 分隔）
          </p>
          <textarea
            className={`min-h-[200px] w-full font-mono text-xs ${surfaceInputClass}`}
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
          />
          <div className="flex flex-wrap items-center gap-3">
            <label className="cursor-pointer rounded-md border border-gray-300 px-3 py-2 text-sm">
              选择 CSV 文件
              <input type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => handleCsvFile(e.target.files?.[0] ?? null)} />
            </label>
            <button
              type="submit"
              disabled={importing}
              className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {importing ? "导入中…" : "导入问题"}
            </button>
            {importMsg && <span className="text-sm text-violet-700">{importMsg}</span>}
          </div>
        </form>
      )}

      {recentRuns.length > 0 && tab === "questions" && (
        <section className={`${surfaceCardClass} p-4 text-sm`}>
          <h3 className="mb-2 font-semibold">最近扫描</h3>
          {recentRuns.slice(0, 5).map((run) => (
            <div key={run.id} className="text-gray-600">
              <Link href={`/strategy/monitor/runs/${run.id}`} className="text-violet-600">
                #{run.id}
              </Link>{" "}
              — {run.probe_count} 探针
            </div>
          ))}
        </section>
      )}

      {probeQuestion && (
        <QuestionProbeDetail
          questionId={probeQuestion.id}
          questionText={probeQuestion.question_text}
          onClose={() => setProbeQuestion(null)}
        />
      )}
    </div>
  );
}

function QuestionTable({
  questions,
  sceneMap,
  onEdit,
  onDelete,
  onViewProbes,
}: {
  questions: MonitorQuestion[];
  sceneMap: Map<number, string>;
  onEdit: (q: MonitorQuestion) => void;
  onDelete: (id: number) => void;
  onViewProbes: (q: MonitorQuestion) => void;
}) {
  if (questions.length === 0) {
    return <p className={`${surfaceCardClass} p-4 text-sm text-gray-500`}>暂无匹配问题</p>;
  }

  return (
    <div className={`overflow-x-auto ${surfaceCardClass}`}>
      <table className="min-w-full divide-y divide-gray-100 text-sm">
        <thead className="bg-gray-50">
          <tr>
            {["问题", "优先级", "类型", "状态", "场景", "竞品", "上次扫描", "操作"].map((h) => (
              <th key={h} className="whitespace-nowrap px-4 py-2 text-left text-xs font-medium text-gray-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {questions.map((q) => (
            <tr key={q.id} className={q.status === "paused" ? "bg-gray-50/80 text-gray-500" : ""}>
              <td className="max-w-xs px-4 py-3">{q.question_text}</td>
              <td className="px-4 py-3">{q.priority}</td>
              <td className="px-4 py-3">{QUERY_TYPE_LABEL[(q.query_type || "brand") as QueryType]}</td>
              <td className="px-4 py-3">
                <span
                  className={`rounded px-1.5 py-0.5 text-xs ${
                    q.status === "active" ? "bg-emerald-50 text-emerald-700" : "bg-gray-200 text-gray-600"
                  }`}
                >
                  {q.status === "active" ? "启用" : "暂停"}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-600">
                {q.scene_id ? sceneMap.get(q.scene_id) ?? `#${q.scene_id}` : "—"}
              </td>
              <td className="max-w-[8rem] truncate px-4 py-3 text-gray-600" title={(q.competitor_brands ?? []).join(", ")}>
                {(q.competitor_brands ?? []).join(", ") || "—"}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500">
                {q.last_scan_at ? new Date(q.last_scan_at).toLocaleDateString("zh-CN") : "—"}
              </td>
              <td className="space-x-2 whitespace-nowrap px-4 py-3">
                <button type="button" className="text-violet-600" onClick={() => onViewProbes(q)}>
                  探针
                </button>
                <button type="button" className="text-violet-600" onClick={() => onEdit(q)}>
                  编辑
                </button>
                <button type="button" className="text-red-600" onClick={() => onDelete(q.id)}>
                  删除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
