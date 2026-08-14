"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";

type MiningMeta = {
  probe_evidence?: Array<{ id?: number; question_text?: string }>;
  thinking_digest?: string;
  source_hints?: Array<{ title?: string; url?: string; domain?: string }>;
  longtail_queries?: string[];
  keyword_combos?: string[];
  llm_enhanced?: boolean;
};

type ThemeCandidate = {
  index: number;
  title: string;
  target_queries?: string[];
};

type ThemeItem = {
  id: number;
  slug: string;
  title: string;
  status: string;
  scene_id?: number | null;
  gate_mode?: string;
  pack_spec?: Array<{ type: string; title?: string; required?: boolean }>;
  gate_summary?: { pack_gate_ok?: boolean; article_count?: number; by_eval_status?: Record<string, number> };
  task_id?: number | null;
  remediation_id?: number | null;
  target_queries?: string[];
  meta?: {
    mining?: MiningMeta;
    candidates?: ThemeCandidate[];
    probe_evidence?: Array<{ id?: number; question_text?: string }>;
  };
};

type ThemeDetail = ThemeItem & {
  articles?: Array<{
    id: number;
    title: string;
    status: string;
    eval_status: string;
    wiki_page_type?: string;
  }>;
};

const STATUS_LABEL: Record<string, string> = {
  draft: "草稿",
  confirmed: "已确认",
  producing: "生产中",
  gate_passed: "门禁通过",
  distributing: "分发中",
  published: "已发布",
  measuring: "测量中",
  completed: "已完成",
};

export function ThemesPanel() {
  const [items, setItems] = useState<ThemeItem[]>([]);
  const [selected, setSelected] = useState<ThemeDetail | null>(null);
  const [flash, setFlash] = useState<{ variant: "success" | "error" | "info"; message: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [queryEdit, setQueryEdit] = useState("");

  const reload = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    try {
      const data = await apiGet<{ items: ThemeItem[] }>("/api/admin/themes", t);
      setItems(data.items || []);
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "加载 Theme 失败" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function openDetail(id: number) {
    const t = getToken();
    if (!t) return;
    try {
      const data = await apiGet<ThemeDetail>(`/api/admin/themes/${id}`, t);
      setSelected(data);
      setQueryEdit((data.target_queries || []).join("\n"));
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "加载详情失败" });
    }
  }

  async function confirmTheme(id: number) {
    const t = getToken();
    if (!t) return;
    setBusy(true);
    setFlash(null);
    try {
      await apiPost(`/api/admin/themes/${id}/confirm`, t, {});
      setFlash({ variant: "success", message: "主题已确认并创建任务" });
      await reload();
      await openDetail(id);
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "确认失败" });
    } finally {
      setBusy(false);
    }
  }

  async function startProduce(id: number) {
    const t = getToken();
    if (!t) return;
    setBusy(true);
    try {
      await apiPost(`/api/admin/themes/${id}/start-produce`, t, {});
      setFlash({ variant: "success", message: "已启动生产" });
      await reload();
      await openDetail(id);
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "启动失败" });
    } finally {
      setBusy(false);
    }
  }

  async function toggleGateMode(id: number, mode: string) {
    const t = getToken();
    if (!t) return;
    const next = mode === "hard" ? "soft" : "hard";
    try {
      await apiPatch(`/api/admin/themes/${id}`, t, { gate_mode: next });
      await reload();
      await openDetail(id);
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "更新门禁失败" });
    }
  }

  async function saveQueries(id: number) {
    const t = getToken();
    if (!t) return;
    const queries = queryEdit
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    setBusy(true);
    try {
      await apiPatch(`/api/admin/themes/${id}`, t, { target_queries: queries });
      setFlash({ variant: "success", message: "长尾 Query 已保存" });
      await openDetail(id);
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "保存失败" });
    } finally {
      setBusy(false);
    }
  }

  async function spawnCandidate(id: number, index: number) {
    const t = getToken();
    if (!t) return;
    setBusy(true);
    try {
      const res = await apiPost<{ theme: ThemeItem }>(
        `/api/admin/themes/${id}/spawn-candidate?candidate_index=${index}`,
        t,
        {},
      );
      setFlash({ variant: "success", message: `已另存候选草稿 #${res.theme.id}` });
      await reload();
      await openDetail(res.theme.id);
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "另存失败" });
    } finally {
      setBusy(false);
    }
  }

  const mining = selected?.meta?.mining;
  const candidates = selected?.meta?.candidates || [];
  const evidence = mining?.probe_evidence || selected?.meta?.probe_evidence || [];

  return (
    <div className="space-y-4">
      {flash && <FlashAlert variant={flash.variant}>{flash.message}</FlashAlert>}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">主题包（内容选题入口）</h2>
          <p className="text-sm text-gray-600">
            主链路：确认挖掘摘要与长尾选题 → 自动建标题库/任务 → 启生产 → GEO 门禁。勿用监控题或 Smoke 标题库替代。
          </p>
          <p className="mt-1 text-xs text-gray-500">
            草稿来自{" "}
            <Link href="/strategy/theme-mining" className="text-emerald-700 hover:underline">
              策略 → 挖掘主题
            </Link>
          </p>
        </div>
        <button
          type="button"
          onClick={reload}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          刷新
        </button>
      </div>

      {loading && <p className="text-sm text-gray-500">加载中…</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left font-medium text-gray-600">主题</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">状态</th>
                <th className="px-3 py-2 text-left font-medium text-gray-600">门禁</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((item) => (
                <tr
                  key={item.id}
                  className={`cursor-pointer hover:bg-blue-50 ${selected?.id === item.id ? "bg-blue-50" : ""}`}
                  onClick={() => openDetail(item.id)}
                >
                  <td className="px-3 py-2">
                    <div className="font-medium text-gray-900">{item.title}</div>
                    <div className="text-xs text-gray-500">{item.slug}</div>
                  </td>
                  <td className="px-3 py-2">{STATUS_LABEL[item.status] || item.status}</td>
                  <td className="px-3 py-2">{item.gate_mode || "soft"}</td>
                </tr>
              ))}
              {!loading && items.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-3 py-8 text-center text-gray-500">
                    暂无主题。请从{" "}
                    <Link href="/strategy/theme-mining" className="text-emerald-700 hover:underline">
                      策略 → 挖掘主题
                    </Link>{" "}
                    生成草稿。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-4">
          {!selected && <p className="text-sm text-gray-500">选择左侧主题查看详情</p>}
          {selected && (
            <div className="space-y-3">
              <h3 className="text-base font-semibold text-gray-900">{selected.title}</h3>
              <p className="text-xs text-gray-500">
                #{selected.id} · {STATUS_LABEL[selected.status] || selected.status}
                {selected.scene_id ? ` · scene ${selected.scene_id}` : ""}
                {selected.task_id ? (
                  <>
                    {" · "}
                    <Link className="text-blue-600 hover:underline" href={`/production/tasks/${selected.task_id}/edit`}>
                      Task #{selected.task_id}
                    </Link>
                  </>
                ) : null}
              </p>

              <div className="flex flex-wrap gap-2">
                {selected.status === "draft" && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => confirmTheme(selected.id)}
                    className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    启动生产
                  </button>
                )}
                {(selected.status === "confirmed" || selected.status === "producing") && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => startProduce(selected.id)}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    启动生产
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => toggleGateMode(selected.id, selected.gate_mode || "soft")}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
                >
                  门禁：{selected.gate_mode || "soft"}（切换）
                </button>
              </div>

              {(mining || evidence.length > 0) && (
                <div className="rounded-lg border border-violet-100 bg-violet-50/50 p-3 space-y-2">
                  <h4 className="text-sm font-medium text-violet-900">挖掘摘要</h4>
                  {mining?.thinking_digest && (
                    <div>
                      <div className="text-xs font-medium text-gray-600">思考链摘要</div>
                      <p className="text-sm text-gray-800">{mining.thinking_digest}</p>
                    </div>
                  )}
                  {evidence.length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-gray-600">探针证据（不作生产标题）</div>
                      <ul className="mt-1 list-disc pl-4 text-xs text-gray-600">
                        {evidence.slice(0, 5).map((e, i) => (
                          <li key={i}>{e.question_text}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {(mining?.source_hints || []).length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-gray-600">信源提示</div>
                      <ul className="mt-1 space-y-0.5 text-xs text-gray-600">
                        {(mining?.source_hints || []).slice(0, 6).map((s, i) => (
                          <li key={i}>
                            {s.domain || s.title || s.url}
                            {s.url ? (
                              <>
                                {" · "}
                                <a className="text-blue-600 hover:underline" href={s.url} target="_blank" rel="noreferrer">
                                  链接
                                </a>
                              </>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {(mining?.keyword_combos || []).length > 0 && (
                    <div className="text-xs text-gray-600">
                      关键词组合：{(mining?.keyword_combos || []).slice(0, 8).join(" · ")}
                    </div>
                  )}
                </div>
              )}

              <div>
                <h4 className="text-sm font-medium text-gray-800">长尾 Query（可编辑）</h4>
                <textarea
                  className="mt-1 w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                  rows={4}
                  value={queryEdit}
                  onChange={(e) => setQueryEdit(e.target.value)}
                  disabled={selected.status !== "draft"}
                />
                {selected.status === "draft" && (
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => saveQueries(selected.id)}
                    className="mt-1 rounded-md border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
                  >
                    保存 Query
                  </button>
                )}
              </div>

              {candidates.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-800">备选战役</h4>
                  <ul className="mt-1 space-y-2">
                    {candidates.map((c) => (
                      <li key={c.index} className="flex items-center justify-between gap-2 text-sm">
                        <span className="text-gray-800">{c.title}</span>
                        <button
                          type="button"
                          disabled={busy}
                          onClick={() => spawnCandidate(selected.id, c.index)}
                          className="shrink-0 rounded-md border border-violet-300 px-2 py-1 text-xs text-violet-700 hover:bg-violet-50"
                        >
                          另存草稿
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div>
                <h4 className="text-sm font-medium text-gray-800">复合包规格</h4>
                <ul className="mt-1 space-y-1 text-sm text-gray-600">
                  {(selected.pack_spec || []).map((p, i) => (
                    <li key={`${p.type}-${i}`}>
                      <span className="font-mono text-xs text-violet-700">{p.type}</span>{" "}
                      {p.title || ""} {p.required === false ? "(可选)" : ""}
                    </li>
                  ))}
                </ul>
              </div>

              {selected.gate_summary && (
                <div className="rounded-lg bg-gray-50 p-3 text-sm">
                  <div>
                    门禁聚合：{selected.gate_summary.pack_gate_ok ? "通过" : "未通过"} · 文章{" "}
                    {selected.gate_summary.article_count ?? 0}
                  </div>
                </div>
              )}

              {(selected.articles || []).length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-800">子页</h4>
                  <ul className="mt-1 space-y-1 text-sm">
                    {selected.articles!.map((a) => (
                      <li key={a.id}>
                        <Link href={`/operations/articles/${a.id}`} className="text-blue-600 hover:underline">
                          {a.title}
                        </Link>{" "}
                        <span className="text-xs text-gray-500">
                          {a.wiki_page_type || "-"} · {a.eval_status} · {a.status}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
