"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { TaskCreateForm } from "@/components/operations/TaskCreateForm";
import { apiGet, apiPost, getToken } from "@/lib/api-client";

type ThemeRow = {
  id: number;
  title: string;
  status: string;
  task_id?: number | null;
  target_queries?: string[];
  meta?: { mining?: { longtail_queries?: string[] } };
};

const STATUS_LABEL: Record<string, string> = {
  draft: "草稿（待确认）",
  confirmed: "已确认",
  producing: "生产中",
  gate_passed: "门禁通过",
};

/**
 * GEO 主链路入口：先选主题包确认/启生产；手工选标题库降级为高级旁路。
 */
export function ThemeFirstProduceEntry() {
  const [themes, setThemes] = useState<ThemeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [flash, setFlash] = useState<{ variant: "success" | "error" | "info"; message: string } | null>(null);
  const [showLegacy, setShowLegacy] = useState(false);

  const reload = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    try {
      const data = await apiGet<{ items: ThemeRow[] }>("/api/admin/themes", t);
      const items = data.items || [];
      // 优先展示可行动的草稿/已确认
      const ranked = [...items].sort((a, b) => {
        const rank = (s: string) => (s === "draft" ? 0 : s === "confirmed" ? 1 : s === "producing" ? 2 : 3);
        return rank(a.status) - rank(b.status) || b.id - a.id;
      });
      setThemes(ranked.slice(0, 20));
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "加载主题包失败" });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  async function confirmTheme(id: number) {
    const t = getToken();
    if (!t) return;
    setBusyId(id);
    setFlash(null);
    try {
      const res = await apiPost<{ theme?: { task_id?: number }; task_id?: number }>(
        `/api/admin/themes/${id}/confirm`,
        t,
        {},
      );
      const taskId = res.task_id || res.theme?.task_id;
      setFlash({
        variant: "success",
        message: taskId
          ? `主题已确认，已用长尾选题生成标题库并创建 Task #${taskId}。可继续「启动生产」。`
          : "主题已确认并创建任务。",
      });
      await reload();
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "确认失败" });
    } finally {
      setBusyId(null);
    }
  }

  async function startProduce(id: number) {
    const t = getToken();
    if (!t) return;
    setBusyId(id);
    setFlash(null);
    try {
      await apiPost(`/api/admin/themes/${id}/start-produce`, t, {});
      setFlash({ variant: "success", message: "已启动生产，请到内容任务查看进度" });
      await reload();
    } catch (e) {
      setFlash({ variant: "error", message: e instanceof Error ? e.message : "启动失败" });
    } finally {
      setBusyId(null);
    }
  }

  const actionable = themes.filter((th) => th.status === "draft" || th.status === "confirmed" || th.status === "producing");

  return (
    <div className="space-y-6">
      {flash && <FlashAlert variant={flash.variant}>{flash.message}</FlashAlert>}

      <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <div className="border-b border-gray-100 px-5 py-3">
          <h3 className="text-base font-semibold text-gray-900">待确认 / 可启生产的主题</h3>
          <p className="text-xs text-gray-500">确认后系统会按主题包规格写入专用标题库，再绑定内容任务</p>
        </div>
        {loading ? (
          <p className="px-5 py-8 text-sm text-gray-400">加载中…</p>
        ) : actionable.length === 0 ? (
          <div className="px-5 py-8 text-sm text-gray-600">
            暂无待办主题。请先到策略侧「挖掘主题」生成草稿，再到主题包确认。
            <div className="mt-3 flex gap-3">
              <Link href="/strategy/theme-mining" className="text-emerald-700 hover:underline">
                挖掘主题 →
              </Link>
              <Link href="/production/themes" className="text-emerald-700 hover:underline">
                主题包列表 →
              </Link>
            </div>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {actionable.map((th) => {
              const qCount = th.target_queries?.length || th.meta?.mining?.longtail_queries?.length || 0;
              return (
                <li key={th.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      #{th.id} {th.title}
                    </p>
                    <p className="text-xs text-gray-500">
                      {STATUS_LABEL[th.status] || th.status}
                      {qCount ? ` · 选题 ${qCount} 条` : ""}
                      {th.task_id ? ` · Task #${th.task_id}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link
                      href={`/production/themes?id=${th.id}`}
                      className="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
                    >
                      看挖掘摘要
                    </Link>
                    {th.status === "draft" && (
                      <button
                        type="button"
                        disabled={busyId === th.id}
                        onClick={() => confirmTheme(th.id)}
                        className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                      >
                        {busyId === th.id ? "确认中…" : "确认并建任务"}
                      </button>
                    )}
                    {(th.status === "confirmed" || th.status === "producing") && (
                      <button
                        type="button"
                        disabled={busyId === th.id}
                        onClick={() => startProduce(th.id)}
                        className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        {busyId === th.id ? "启动中…" : "启动生产"}
                      </button>
                    )}
                    {th.task_id ? (
                      <Link
                        href={`/production/tasks/${th.task_id}/edit`}
                        className="rounded-md border border-gray-200 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
                      >
                        打开任务
                      </Link>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <details
        className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4"
        open={showLegacy}
        onToggle={(e) => setShowLegacy((e.target as HTMLDetailsElement).open)}
      >
        <summary className="cursor-pointer text-sm font-medium text-gray-700">
          高级：不经主题包、手工选标题库建任务（旁路，非 GEO 主链路）
        </summary>
        <p className="mt-2 text-xs text-amber-800">
          仅用于调试或非策略选题。正式 GEO 内容请用上方主题包确认，避免再用「KB Smoke」等通用标题库替代挖掘选题。
        </p>
        <div className="mt-4">{showLegacy ? <TaskCreateForm /> : null}</div>
      </details>
    </div>
  );
}
