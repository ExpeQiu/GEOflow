"use client";

import Link from "next/link";
import { useState } from "react";
import { Inbox, Play, Plus, Square, Zap } from "lucide-react";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";
import type { AdminTask } from "@/lib/operations-types";

export function TasksPanel({
  tasks,
  onStart,
  onStop,
  onEnqueue,
  onDelete,
  onBatchStart,
  busyId,
  themeFilter,
  onThemeFilterChange,
  basePath = "/production/tasks",
}: {
  tasks: AdminTask[];
  onStart: (id: number) => void;
  onStop: (id: number) => void;
  onEnqueue: (id: number) => void;
  onDelete: (id: number) => void;
  onBatchStart?: (ids: number[]) => void;
  busyId: number | null;
  themeFilter?: string;
  onThemeFilterChange?: (value: string) => void;
  basePath?: string;
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set());

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === tasks.length) setSelected(new Set());
    else setSelected(new Set(tasks.map((t) => t.id)));
  }
  if (tasks.length === 0 && !themeFilter) {
    return (
      <div className="rounded-lg bg-white px-6 py-10 text-center shadow-sm ring-1 ring-gray-200">
        <Inbox className="mx-auto mb-4 h-12 w-12 text-gray-400" />
        <h3 className="text-lg font-medium text-gray-900">{zh.tasks.emptyTitle}</h3>
        <p className="mt-2 text-sm text-gray-500">{zh.tasks.emptyDesc}</p>
        <Link
          href={`${basePath}/new`}
          className="mt-6 inline-flex items-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700"
        >
          <Plus className="mr-2 h-4 w-4" />
          {zh.tasks.createButton}
        </Link>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
      <div className="flex flex-col gap-3 border-b border-gray-200 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-lg font-medium text-gray-900">{zh.tasks.listTitle}</h3>
        <div className="flex flex-wrap items-center gap-2">
          {onThemeFilterChange && (
            <label className="flex items-center gap-2 text-sm text-gray-600">
              Theme
              <input
                type="number"
                min={1}
                placeholder="ID"
                value={themeFilter ?? ""}
                onChange={(e) => onThemeFilterChange(e.target.value)}
                className="w-24 rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              />
            </label>
          )}
          {onBatchStart && selected.size > 0 && (
            <button
              type="button"
              onClick={() => {
                onBatchStart([...selected]);
                setSelected(new Set());
              }}
              className="inline-flex h-9 items-center rounded-lg border border-emerald-200 bg-emerald-50 px-3 text-sm font-medium text-emerald-700 hover:bg-emerald-100"
            >
              批量启动 ({selected.size})
            </button>
          )}
          <Link
            href={`${basePath}/new`}
            className="inline-flex h-9 items-center rounded-lg bg-emerald-600 px-3 text-sm font-semibold text-white hover:bg-emerald-700"
          >
            <Plus className="mr-2 h-4 w-4" />
            {zh.tasks.createButton}
          </Link>
        </div>
      </div>
      {tasks.length === 0 ? (
        <div className="px-6 py-10 text-center text-sm text-gray-500">该 Theme 下暂无任务</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-[1080px] w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selected.size === tasks.length && tasks.length > 0}
                    onChange={toggleAll}
                  />
                </th>
                {[
                  zh.tasks.columnName,
                  "Theme",
                  zh.tasks.columnCreated,
                  zh.tasks.columnModel,
                  zh.tasks.columnStats,
                  zh.tasks.columnLoop,
                  zh.tasks.columnStatus,
                  zh.tasks.columnActions,
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {tasks.map((task) => (
                <TaskRow
                  key={task.id}
                  task={task}
                  busy={busyId === task.id}
                  selected={selected.has(task.id)}
                  basePath={basePath}
                  onToggle={() => toggle(task.id)}
                  onStart={onStart}
                  onStop={onStop}
                  onEnqueue={onEnqueue}
                  onDelete={onDelete}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ThemeLink({ task }: { task: AdminTask }) {
  if (!task.theme_id) return <span className="text-sm text-gray-400">—</span>;
  return (
    <div className="max-w-[160px]">
      <Link
        href={`/production/themes?id=${task.theme_id}`}
        className="line-clamp-2 text-sm text-blue-700 hover:underline"
        title={task.theme_title || undefined}
      >
        {task.theme_title || `#${task.theme_id}`}
      </Link>
      {task.theme_gate_hint && (
        <span className="mt-1 inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
          {task.theme_gate_hint}
        </span>
      )}
    </div>
  );
}

function TaskRow({
  task,
  busy,
  selected,
  basePath,
  onToggle,
  onStart,
  onStop,
  onEnqueue,
  onDelete,
}: {
  task: AdminTask;
  busy: boolean;
  selected: boolean;
  basePath: string;
  onToggle: () => void;
  onStart: (id: number) => void;
  onStop: (id: number) => void;
  onEnqueue: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  const active = task.status === "active";
  const limit = Math.max(1, task.article_limit || 10);
  const progress = Math.min(100, Math.floor((Math.min(limit, task.created_count) / limit) * 100));
  const createdAt = task.created_at ? new Date(task.created_at).toLocaleString("zh-CN") : "—";
  const hasFailure = task.batch_error_message && ["failed", "cancelled"].includes(task.batch_status ?? "");

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-4 align-top">
        <input type="checkbox" checked={selected} onChange={onToggle} />
      </td>
      <td className="px-4 py-4 align-top">
        <div className="text-sm font-medium text-gray-900">{task.name}</div>
        <span className="mt-1 inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-100">
          内容生成
        </span>
        {hasFailure && (
          <div className="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
            {task.batch_error_message}
          </div>
        )}
        {(task.title_library_name || task.knowledge_base_name) && (
          <div className="mt-2 space-y-0.5 text-xs text-gray-500">
            {task.title_library_name && <div>标题库：{task.title_library_name}</div>}
            {task.knowledge_base_name && (
              <div>
                知识库：
                {task.knowledge_base_id ? (
                  <Link href={`/production/knowledge/${task.knowledge_base_id}`} className="text-emerald-700 hover:underline">
                    {task.knowledge_base_name}
                  </Link>
                ) : (
                  task.knowledge_base_name
                )}
              </div>
            )}
          </div>
        )}
      </td>
      <td className="px-4 py-4 align-top">
        <ThemeLink task={task} />
      </td>
      <td className="whitespace-nowrap px-4 py-4 align-top text-sm text-gray-500">{createdAt}</td>
      <td className="px-4 py-4 align-top text-sm text-gray-500">
        <div>{task.ai_model_name || "—"}</div>
        <span className="mt-1 inline-flex rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
          {task.model_selection_mode === "smart_failover" ? "智能 failover" : "固定模型"}
        </span>
      </td>
      <td className="whitespace-nowrap px-4 py-4 align-top text-sm text-gray-500">
        <div>{zh.tasks.createdOfLimit(task.created_count, limit)}</div>
        <div>{zh.tasks.published(task.published_count)}</div>
        <div className="mt-2 h-1.5 w-28 overflow-hidden rounded-full bg-gray-200">
          <div className="h-full rounded-full bg-emerald-600" style={{ width: `${progress}%` }} />
        </div>
      </td>
      <td className="whitespace-nowrap px-4 py-4 align-top text-sm text-gray-500">
        {zh.tasks.loopTimes(task.loop_count)}
        <div className="mt-1 text-xs text-gray-400">{Math.max(1, Math.ceil(task.publish_interval / 60))} 分钟/篇</div>
      </td>
      <td className="px-4 py-4 align-top">
        <span className={`text-sm ${active ? "text-green-600" : "text-gray-500"}`}>
          {active ? zh.tasks.statusActive : zh.tasks.statusPaused}
        </span>
      </td>
      <td className="px-4 py-4 align-top">
        <div className="flex items-center gap-1.5">
          <Link
            href={`${basePath}/${task.id}/edit`}
            className="inline-flex h-8 items-center rounded-md border border-gray-200 px-2 text-xs text-gray-600 hover:bg-gray-50"
          >
            编辑
          </Link>
          {active ? (
            <IconButton title={zh.tasks.actionStop} onClick={() => onStop(task.id)} disabled={busy} tone="red">
              <Square className="h-4 w-4" />
            </IconButton>
          ) : (
            <IconButton title={zh.tasks.actionStart} onClick={() => onStart(task.id)} disabled={busy} tone="green">
              <Play className="h-4 w-4" />
            </IconButton>
          )}
          <IconButton title={zh.tasks.actionRun} onClick={() => onEnqueue(task.id)} disabled={busy} tone="blue">
            <Zap className="h-4 w-4" />
          </IconButton>
          <button
            type="button"
            disabled={busy}
            onClick={() => onDelete(task.id)}
            className="inline-flex h-8 items-center rounded-md border border-red-200 px-2 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50"
          >
            删除
          </button>
        </div>
      </td>
    </tr>
  );
}

function IconButton({
  children,
  onClick,
  disabled,
  title,
  tone,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  title: string;
  tone: "red" | "green" | "blue";
}) {
  const toneClass = {
    red: "border-red-200 text-red-600 hover:bg-red-50",
    green: "border-green-200 text-green-600 hover:bg-green-50",
    blue: "border-blue-200 text-blue-600 hover:bg-blue-50",
  }[tone];

  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-md border transition-colors disabled:opacity-50",
        toneClass,
      )}
    >
      {children}
    </button>
  );
}
