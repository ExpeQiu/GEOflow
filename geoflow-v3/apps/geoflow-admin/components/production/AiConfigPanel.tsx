"use client";

import Link from "next/link";
import { useState } from "react";
import { Activity, Cpu, MessageSquare, Workflow } from "lucide-react";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";
import type { AiModelRow, AiStats, OrchestrationStats, PromptRow, WorkflowCatalog } from "@/lib/production-types";

const WORKFLOW_LABELS: Record<string, string> = {
  content: "正文生成",
  content_pipeline: "编辑部 Pipeline",
  url_import: "URL 导入",
  semantic_chunk: "语义切片",
};

export function AiConfigPanel({
  aiStats,
  orchestration,
  workflowCatalog,
  models,
  prompts,
}: {
  aiStats: AiStats;
  orchestration: OrchestrationStats;
  workflowCatalog: WorkflowCatalog;
  models: AiModelRow[];
  prompts: PromptRow[];
}) {
  const workflows = workflowCatalog.workflows;
  const workflowKeys = Object.keys(workflows);
  const [activeWorkflow, setActiveWorkflow] = useState(workflowCatalog.default_workflow || workflowKeys[0] || "");

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-lg border border-violet-200 bg-white shadow-sm">
        <div className="border-b border-violet-100 bg-violet-50/60 px-6 py-5">
          <h2 className="text-xl font-semibold text-gray-900">{zh.production.ai.heading}</h2>
          <p className="mt-1 text-sm text-gray-600">{zh.production.ai.subtitle}</p>
        </div>
        <div className="grid grid-cols-1 gap-4 p-6 md:grid-cols-3">
          <MiniCard icon={Cpu} title={zh.production.ai.modelsTitle} value={aiStats.model_count} sub={`Chat ${aiStats.chat_models} · Embed ${aiStats.embedding_models}`} />
          <MiniCard icon={MessageSquare} title={zh.production.ai.promptsTitle} value={aiStats.prompt_count} sub={zh.production.ai.todayUsage(aiStats.today_usage)} />
          <MiniCard icon={Activity} title="累计调用" value={aiStats.total_usage} sub={zh.production.ai.todayUsage(aiStats.today_usage)} />
        </div>
      </section>

      <OrchestrationPanel orchestration={orchestration} workflowCatalog={workflowCatalog} activeWorkflow={activeWorkflow} onSelectWorkflow={setActiveWorkflow} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ModelsTable models={models} />
        <PromptsTable prompts={prompts} />
      </div>
    </div>
  );
}

function OrchestrationPanel({
  orchestration,
  workflowCatalog,
  activeWorkflow,
  onSelectWorkflow,
}: {
  orchestration: OrchestrationStats;
  workflowCatalog: WorkflowCatalog;
  activeWorkflow: string;
  onSelectWorkflow: (key: string) => void;
}) {
  const totals = orchestration.totals_24h;
  const wf = workflowCatalog.workflows[activeWorkflow];

  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 bg-slate-50/80 px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Workflow className="h-5 w-5 text-slate-600" />
            <h2 className="text-base font-semibold text-gray-900">{zh.production.orchestration.title}</h2>
          </div>
          <span
            className={cn(
              "inline-flex rounded-full px-3 py-1 text-xs font-semibold ring-1",
              orchestration.sidecar_healthy
                ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
                : "bg-red-50 text-red-700 ring-red-200",
            )}
          >
            {orchestration.sidecar_healthy ? zh.production.orchestration.healthy : zh.production.orchestration.unhealthy}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
        <div>
          <p className="text-xs font-medium uppercase text-gray-500">{zh.production.orchestration.backend}</p>
          <p className="mt-1 text-lg font-semibold text-gray-900">{zh.production.orchestration.backendInternal}</p>
          <p className="mt-1 text-xs text-gray-500">{orchestration.driver_hint}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase text-gray-500">{zh.production.orchestration.completed24h}</p>
          <p className="mt-1 text-lg font-semibold text-emerald-700">{totals.completed ?? 0}</p>
          <p className="mt-1 text-xs text-gray-500">{zh.production.orchestration.failed24h((totals.failed ?? 0) + (totals.expired ?? 0))}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase text-gray-500">{zh.production.orchestration.pending}</p>
          <p className="mt-1 text-lg font-semibold text-amber-700">{(totals.pending ?? 0) + (totals.running ?? 0)}</p>
        </div>
        <div>
          <p className="text-xs font-medium uppercase text-gray-500">工作流 24h</p>
          <dl className="mt-1 space-y-1 text-xs text-gray-600">
            {Object.entries(orchestration.by_workflow).slice(0, 4).map(([key, stats]) => (
              <div key={key} className="flex justify-between gap-2">
                <dt>{WORKFLOW_LABELS[key] ?? key}</dt>
                <dd className="font-medium text-gray-900">
                  {stats.completed}/{stats.failed}/{stats.pending}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      {Object.keys(workflowCatalog.workflows).length > 0 && (
        <div className="border-t border-gray-100 px-6 py-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">{zh.production.orchestration.graphTitle}</h3>
              <p className="mt-1 text-xs text-gray-500">{zh.production.orchestration.graphDesc}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.keys(workflowCatalog.workflows).map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => onSelectWorkflow(key)}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium ring-1 transition",
                    activeWorkflow === key
                      ? "bg-slate-800 text-white ring-slate-800"
                      : "bg-white text-slate-700 ring-slate-200 hover:bg-slate-50",
                  )}
                >
                  {WORKFLOW_LABELS[key] ?? key}
                </button>
              ))}
            </div>
          </div>

          {wf && (
            <div className="mt-4 overflow-x-auto rounded-lg border border-slate-200 bg-slate-50/50 p-4">
              <p className="text-sm font-medium text-gray-900">{WORKFLOW_LABELS[activeWorkflow] ?? activeWorkflow}</p>
              {wf.description && <p className="mt-1 text-xs text-gray-500">{wf.description}</p>}
              <div className="mt-4 flex flex-wrap items-center gap-2">
                {wf.visual_steps.map((step, index) => (
                  <span key={step.id} className="flex items-center gap-2">
                    <span
                      className={cn(
                        "rounded-lg border px-3 py-2 text-xs font-medium",
                        step.type === "agent" ? "border-violet-200 bg-violet-50 text-violet-800" : "border-slate-200 bg-white text-slate-700",
                      )}
                    >
                      {step.label}
                      {step.type === "agent" && step.agent && (
                        <span className="ml-1 text-[10px] text-violet-500">({step.agent})</span>
                      )}
                    </span>
                    {index < wf.visual_steps.length - 1 && <span className="text-gray-300">→</span>}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function MiniCard({ icon: Icon, title, value, sub }: { icon: typeof Cpu; title: string; value: number; sub: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="flex items-center gap-3">
        <Icon className="h-5 w-5 text-violet-600" />
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{sub}</p>
        </div>
      </div>
    </div>
  );
}

function ModelsTable({ models }: { models: AiModelRow[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <span className="text-sm font-semibold text-gray-900">{zh.production.ai.modelsTitle}</span>
        <Link href="/production/ai-models" className="text-xs text-violet-600 hover:underline">管理全部 →</Link>
      </div>
      {models.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-gray-500">暂无模型</div>
      ) : (
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {["名称", "类型", "状态", "今日"].map((h) => (
                <th key={h} className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {models.map((m) => (
              <tr key={m.id}>
                <td className="px-4 py-2 font-medium text-gray-900">{m.name}</td>
                <td className="px-4 py-2 text-gray-600">{m.model_type}</td>
                <td className="px-4 py-2">
                  <span className={m.status === "active" ? "text-green-700" : "text-gray-500"}>{m.status}</span>
                </td>
                <td className="px-4 py-2 text-gray-600">{m.used_today}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function PromptsTable({ prompts }: { prompts: PromptRow[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <span className="text-sm font-semibold text-gray-900">{zh.production.ai.promptsTitle}</span>
        <Link href="/production/ai-prompts" className="text-xs text-violet-600 hover:underline">管理全部 →</Link>
      </div>
      {prompts.length === 0 ? (
        <div className="px-4 py-8 text-center text-sm text-gray-500">暂无提示词</div>
      ) : (
        <ul className="divide-y divide-gray-100">
          {prompts.map((p) => (
            <li key={p.id} className="px-4 py-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-gray-900">{p.name}</span>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{p.type}</span>
              </div>
              <p className="mt-1 line-clamp-2 text-xs text-gray-500">{p.preview}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
