"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { cn } from "@/lib/cn";
import { apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { DEFAULT_TASK_FORM, type TaskCreatePayload, type TaskFormOptions } from "@/lib/task-form-types";

const inputClass =
  "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";
const labelClass = "block text-sm font-medium text-gray-700";

export function TaskCreateForm({ taskId }: { taskId?: number }) {
  const router = useRouter();
  const isEdit = Boolean(taskId);
  const [options, setOptions] = useState<TaskFormOptions | null>(null);
  const [form, setForm] = useState<TaskCreatePayload>(DEFAULT_TASK_FORM);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const loads: Promise<void>[] = [
      apiGet<TaskFormOptions>("/api/admin/tasks/form-options", token).then(setOptions),
    ];
    if (taskId) {
      loads.push(
        apiGet<{ task: TaskCreatePayload & { task_name: string } }>(`/api/admin/tasks/${taskId}`, token).then((data) => {
          const t = data.task;
          setForm({
            ...DEFAULT_TASK_FORM,
            ...t,
            task_name: t.task_name || t.name || "",
            distribution_channel_ids: t.distribution_channel_ids || [],
          });
        }),
      );
    }
    Promise.all(loads)
      .catch(() => setError(zh.taskCreate.loadError))
      .finally(() => setLoading(false));
  }, [taskId]);

  const isWiki = form.content_format === "wiki_mdx";
  const channelsDisabled = form.publish_scope === "local_only";

  const publishIntervalDisabled = useMemo(() => form.need_review, [form.need_review]);

  function patch<K extends keyof TaskCreatePayload>(key: K, value: TaskCreatePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function toggleChannel(id: number, checked: boolean) {
    setForm((prev) => {
      const ids = new Set(prev.distribution_channel_ids);
      if (checked) ids.add(id);
      else ids.delete(id);
      return { ...prev, distribution_channel_ids: Array.from(ids) };
    });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (!form.task_name.trim()) {
      setError(zh.taskCreate.errors.nameRequired);
      return;
    }
    if (!form.title_library_id) {
      setError(zh.taskCreate.errors.titleLibraryRequired);
      return;
    }
    if (!form.prompt_id) {
      setError(zh.taskCreate.errors.promptRequired);
      return;
    }
    if (!form.ai_model_id) {
      setError(zh.taskCreate.errors.modelRequired);
      return;
    }
    if (form.draft_limit > form.article_limit) {
      setError(zh.taskCreate.errors.draftLimit);
      return;
    }
    if (form.publish_scope === "distribution_only" && form.distribution_channel_ids.length === 0) {
      setError(zh.taskCreate.errors.distributionChannel);
      return;
    }
    if (form.category_mode === "fixed" && !form.fixed_category_id) {
      setError(zh.taskCreate.errors.fixedCategory);
      return;
    }

    const token = getToken();
    if (!token) return;

    const payload: TaskCreatePayload = {
      ...form,
      task_name: form.task_name.trim(),
      publish_scope: isWiki ? "distribution_only" : form.publish_scope,
      image_count: form.image_library_id ? form.image_count : 0,
      author_id: form.author_id && form.author_id > 0 ? form.author_id : null,
    };

    setSubmitting(true);
    try {
      if (isEdit && taskId) {
        await apiPatch(`/api/admin/tasks/${taskId}`, token, payload);
      } else {
        await apiPost("/api/admin/tasks", token, payload);
      }
      router.push("/operations/tasks");
      router.refresh();
    } catch {
      setError(isEdit ? zh.taskEdit.submitError : zh.taskCreate.submitError);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <FlashAlert variant="info">{zh.common.loading}</FlashAlert>;
  }

  if (!options?.has_categories) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-5">
        <h3 className="text-base font-semibold text-amber-900">{zh.taskCreate.noCategoriesTitle}</h3>
        <p className="mt-2 text-sm text-amber-800">{zh.taskCreate.noCategoriesDesc}</p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="grid grid-cols-1 gap-6 xl:grid-cols-12">
      <div className="mb-2 flex items-center gap-4 xl:col-span-12">
        <Link href="/operations/tasks" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{isEdit ? zh.taskEdit.title : zh.taskCreate.title}</h1>
          <p className="mt-1 text-sm text-gray-600">{isEdit ? zh.taskEdit.subtitle : zh.taskCreate.subtitle}</p>
        </div>
      </div>

      {error && (
        <div className="xl:col-span-12">
          <FlashAlert variant="error">{error}</FlashAlert>
        </div>
      )}

      <FormSection title={zh.taskCreate.sections.basic.title} desc={zh.taskCreate.sections.basic.desc} className="xl:col-span-12">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-3">
            <label htmlFor="task_name" className={labelClass}>
              {zh.taskCreate.fields.taskName} *
            </label>
            <input
              id="task_name"
              required
              value={form.task_name}
              onChange={(e) => patch("task_name", e.target.value)}
              className={inputClass}
              placeholder={zh.taskCreate.placeholders.taskName}
            />
          </div>
          <div className="lg:col-span-2">
            <label htmlFor="title_library_id" className={labelClass}>
              {zh.taskCreate.fields.titleLibrary} *
            </label>
            <select
              id="title_library_id"
              required
              value={form.title_library_id || ""}
              onChange={(e) => patch("title_library_id", Number(e.target.value))}
              className={inputClass}
            >
              <option value="">{zh.taskCreate.options.selectTitleLibrary}</option>
              {options.title_libraries.map((lib) => (
                <option key={lib.id} value={lib.id}>
                  {lib.name} ({lib.count ?? 0})
                </option>
              ))}
            </select>
            {options.title_libraries.length === 0 && (
              <p className="mt-1 text-xs text-amber-600">{zh.taskCreate.hints.noTitleLibraries}</p>
            )}
          </div>
          <div>
            <label htmlFor="status" className={labelClass}>
              {zh.taskCreate.fields.status}
            </label>
            <select id="status" value={form.status} onChange={(e) => patch("status", e.target.value as TaskCreatePayload["status"])} className={inputClass}>
              <option value="active">{zh.taskCreate.options.statusActive}</option>
              <option value="paused">{zh.taskCreate.options.statusPaused}</option>
            </select>
          </div>
        </div>
      </FormSection>

      <FormSection title={zh.taskCreate.sections.wiki.title} desc={zh.taskCreate.sections.wiki.desc} className="xl:col-span-12">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div>
            <label className={labelClass}>{zh.taskCreate.fields.contentFormat}</label>
            <select
              value={form.content_format}
              onChange={(e) => patch("content_format", e.target.value as TaskCreatePayload["content_format"])}
              className={inputClass}
            >
              <option value="article">{zh.taskCreate.options.formatArticle}</option>
              <option value="wiki_mdx">{zh.taskCreate.options.formatWiki}</option>
            </select>
          </div>
          {isWiki && (
            <>
              <div>
                <label className={labelClass}>{zh.taskCreate.fields.wikiType}</label>
                <select value={form.wiki_page_type} onChange={(e) => patch("wiki_page_type", e.target.value)} className={inputClass}>
                  {options.wiki_page_types.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>{zh.taskCreate.fields.techIp}</label>
                <select
                  value={form.tech_ip_asset_id ?? ""}
                  onChange={(e) => patch("tech_ip_asset_id", e.target.value ? Number(e.target.value) : null)}
                  className={inputClass}
                >
                  <option value="">—</option>
                  {options.tech_ip_assets.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.ip_name} ({asset.status})
                    </option>
                  ))}
                </select>
              </div>
              <p className="md:col-span-3 rounded-md bg-indigo-50 px-4 py-3 text-sm text-indigo-700">{zh.taskCreate.hints.wikiGweb}</p>
            </>
          )}
        </div>
      </FormSection>

      <FormSection title={zh.taskCreate.sections.content.title} desc={zh.taskCreate.sections.content.desc} className="xl:col-span-12">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <SelectField
            label={`${zh.taskCreate.fields.prompt} *`}
            value={form.prompt_id}
            onChange={(v) => patch("prompt_id", v)}
            placeholder={zh.taskCreate.options.selectPrompt}
            options={options.prompts}
          />
          <SelectField
            label={`${zh.taskCreate.fields.aiModel} *`}
            value={form.ai_model_id}
            onChange={(v) => patch("ai_model_id", v)}
            placeholder={zh.taskCreate.options.selectModel}
            options={options.ai_models}
          />
          <div>
            <label className={labelClass}>{zh.taskCreate.fields.modelMode}</label>
            <select
              value={form.model_selection_mode}
              onChange={(e) => patch("model_selection_mode", e.target.value as TaskCreatePayload["model_selection_mode"])}
              className={inputClass}
            >
              <option value="fixed">{zh.taskCreate.options.modelFixed}</option>
              <option value="smart_failover">{zh.taskCreate.options.modelFailover}</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>{zh.taskCreate.fields.pipelineMode}</label>
            <select
              value={form.content_pipeline_mode}
              onChange={(e) => patch("content_pipeline_mode", e.target.value as TaskCreatePayload["content_pipeline_mode"])}
              className={inputClass}
            >
              <option value="legacy">{zh.taskCreate.options.pipelineLegacy}</option>
              <option value="pipeline">{zh.taskCreate.options.pipelinePipeline}</option>
              <option value="auto">{zh.taskCreate.options.pipelineAuto}</option>
            </select>
          </div>
          <SelectField
            label={zh.taskCreate.fields.knowledgeBase}
            value={form.knowledge_base_id ?? 0}
            onChange={(v) => patch("knowledge_base_id", v || null)}
            placeholder={zh.taskCreate.options.noKnowledge}
            options={options.knowledge_bases}
            optional
          />
          <div>
            <label className={labelClass}>{zh.taskCreate.fields.author}</label>
            <select
              value={form.author_id ?? 0}
              onChange={(e) => patch("author_id", Number(e.target.value))}
              className={inputClass}
            >
              <option value={0}>{zh.taskCreate.options.randomAuthor}</option>
              {options.authors.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </FormSection>

      <FormSection title={zh.taskCreate.sections.image.title} desc={zh.taskCreate.sections.image.desc} className="xl:col-span-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <SelectField
            label={zh.taskCreate.fields.imageLibrary}
            value={form.image_library_id ?? 0}
            onChange={(v) => {
              patch("image_library_id", v || null);
              patch("image_count", v ? Math.max(1, form.image_count) : 0);
            }}
            placeholder={zh.taskCreate.options.noImages}
            options={options.image_libraries}
            optional
            showCount
          />
          <div>
            <label className={labelClass}>{zh.taskCreate.fields.imageCount}</label>
            <select
              value={form.image_count}
              disabled={!form.image_library_id}
              onChange={(e) => patch("image_count", Number(e.target.value))}
              className={inputClass}
            >
              {[0, 1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>
                  {n === 0 ? zh.taskCreate.options.noImageCount : `${n} 张`}
                </option>
              ))}
            </select>
          </div>
        </div>
      </FormSection>

      <FormSection title={zh.taskCreate.sections.publish.title} desc={zh.taskCreate.sections.publish.desc} className="xl:col-span-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <label className="flex items-start gap-2 text-sm text-gray-900">
            <input
              type="checkbox"
              checked={form.need_review}
              onChange={(e) => patch("need_review", e.target.checked)}
              className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            <span>
              <span className="font-medium">{zh.taskCreate.fields.needReview}</span>
              <span className="mt-1 block text-gray-500">{zh.taskCreate.hints.needReview}</span>
            </span>
          </label>
          <div className={publishIntervalDisabled ? "opacity-50" : ""}>
            <label className={labelClass}>{zh.taskCreate.fields.publishInterval}</label>
            <input
              type="number"
              min={1}
              disabled={publishIntervalDisabled}
              value={form.publish_interval}
              onChange={(e) => patch("publish_interval", Number(e.target.value))}
              className={inputClass}
            />
            <p className="mt-1 text-sm text-gray-500">{zh.taskCreate.hints.publishInterval}</p>
          </div>
        </div>
      </FormSection>

      <FormSection title={zh.taskCreate.sections.distribution.title} desc={zh.taskCreate.sections.distribution.desc} className="xl:col-span-12">
        <fieldset className="mb-5">
          <legend className="text-sm font-medium text-gray-900">{zh.taskCreate.fields.publishScope}</legend>
          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
            {(
              [
                ["local_and_distribution", zh.taskCreate.scopes.localAndDistribution, zh.taskCreate.scopes.localAndDistributionDesc],
                ["distribution_only", zh.taskCreate.scopes.distributionOnly, zh.taskCreate.scopes.distributionOnlyDesc],
                ["local_only", zh.taskCreate.scopes.localOnly, zh.taskCreate.scopes.localOnlyDesc],
              ] as const
            ).map(([value, title, desc]) => (
              <label
                key={value}
                className={cn(
                  "flex cursor-pointer gap-3 rounded-md border border-gray-200 px-4 py-3 text-sm hover:border-blue-300 hover:bg-blue-50",
                  isWiki && value !== "distribution_only" && "cursor-not-allowed opacity-50",
                )}
              >
                <input
                  type="radio"
                  name="publish_scope"
                  value={value}
                  checked={(isWiki ? "distribution_only" : form.publish_scope) === value}
                  disabled={isWiki && value !== "distribution_only"}
                  onChange={() => patch("publish_scope", value)}
                  className="mt-1 h-4 w-4 border-gray-300 text-blue-600"
                />
                <span>
                  <span className="block font-medium text-gray-900">{title}</span>
                  <span className="block text-gray-500">{desc}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        {options.distribution_channels.length === 0 ? (
          <p className="rounded-md bg-gray-50 px-4 py-3 text-sm text-gray-600">{zh.taskCreate.hints.noChannels}</p>
        ) : (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {options.distribution_channels.map((ch) => (
              <label
                key={ch.id}
                className={cn(
                  "flex items-start gap-3 rounded-md border border-gray-200 px-4 py-3 text-sm",
                  channelsDisabled ? "cursor-not-allowed bg-gray-50 opacity-50" : "cursor-pointer hover:border-blue-300 hover:bg-blue-50",
                )}
              >
                <input
                  type="checkbox"
                  disabled={channelsDisabled}
                  checked={!channelsDisabled && form.distribution_channel_ids.includes(ch.id)}
                  onChange={(e) => toggleChannel(ch.id, e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                <span>
                  <span className="block font-medium text-gray-900">{ch.name}</span>
                  <span className="block break-all text-gray-500">{ch.domain || ch.channel_type}</span>
                </span>
              </label>
            ))}
          </div>
        )}
      </FormSection>

      <FormSection title={zh.taskCreate.sections.advanced.title} desc={zh.taskCreate.sections.advanced.desc} className="xl:col-span-12">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          <div>
            <label className={labelClass}>{zh.taskCreate.fields.articleLimit}</label>
            <input
              type="number"
              min={1}
              value={form.article_limit}
              onChange={(e) => patch("article_limit", Number(e.target.value))}
              className={inputClass}
            />
          </div>
          <div>
            <label className={labelClass}>{zh.taskCreate.fields.draftLimit}</label>
            <input
              type="number"
              min={1}
              max={form.article_limit}
              value={form.draft_limit}
              onChange={(e) => patch("draft_limit", Number(e.target.value))}
              className={inputClass}
            />
          </div>
          <label className="flex items-center gap-2 pt-7 text-sm text-gray-900">
            <input
              type="checkbox"
              checked={form.is_loop}
              onChange={(e) => patch("is_loop", e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            {zh.taskCreate.fields.loopMode}
          </label>
          {!isWiki && (
            <>
              <label className="flex items-center gap-2 pt-7 text-sm text-gray-900">
                <input
                  type="checkbox"
                  checked={form.auto_keywords}
                  onChange={(e) => patch("auto_keywords", e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                {zh.taskCreate.fields.autoKeywords}
              </label>
              <label className="flex items-center gap-2 pt-7 text-sm text-gray-900">
                <input
                  type="checkbox"
                  checked={form.auto_description}
                  onChange={(e) => patch("auto_description", e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                {zh.taskCreate.fields.autoDescription}
              </label>
            </>
          )}
        </div>
        <div className="mt-6">
          <p className={labelClass}>{zh.taskCreate.fields.categoryMode}</p>
          <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-3">
            {(
              [
                ["smart", zh.taskCreate.options.categorySmart],
                ["fixed", zh.taskCreate.options.categoryFixed],
                ["random", zh.taskCreate.options.categoryRandom],
              ] as const
            ).map(([value, label]) => (
              <label key={value} className="flex items-start gap-3 rounded-md border border-gray-200 px-4 py-3 text-sm">
                <input
                  type="radio"
                  name="category_mode"
                  value={value}
                  checked={form.category_mode === value}
                  onChange={() => patch("category_mode", value)}
                  className="mt-1 h-4 w-4 border-gray-300 text-blue-600"
                />
                <span className="font-medium text-gray-700">{label}</span>
              </label>
            ))}
          </div>
          {form.category_mode === "fixed" && (
            <div className="mt-4">
              <SelectField
                label={zh.taskCreate.fields.fixedCategory}
                value={form.fixed_category_id ?? 0}
                onChange={(v) => patch("fixed_category_id", v || null)}
                placeholder={zh.taskCreate.options.selectCategory}
                options={options.categories}
              />
            </div>
          )}
        </div>
      </FormSection>

      <div className="flex justify-end gap-3 xl:col-span-12">
        <Link href="/operations/tasks" className="rounded-md border border-gray-300 bg-white px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
          {zh.taskCreate.cancel}
        </Link>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? zh.common.loading : isEdit ? zh.taskEdit.submit : zh.taskCreate.submit}
        </button>
      </div>
    </form>
  );
}

function FormSection({
  title,
  desc,
  children,
  className,
}: {
  title: string;
  desc: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200", className)}>
      <div className="border-b border-gray-100 px-6 py-4">
        <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        <p className="mt-1 text-sm text-gray-600">{desc}</p>
      </div>
      <div className="px-6 py-4">{children}</div>
    </section>
  );
}

function SelectField({
  label,
  value,
  onChange,
  placeholder,
  options,
  optional,
  showCount,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  placeholder: string;
  options: { id: number; name: string; count?: number }[];
  optional?: boolean;
  showCount?: boolean;
}) {
  return (
    <div>
      <label className={labelClass}>{label}</label>
      <select value={value || ""} onChange={(e) => onChange(Number(e.target.value))} className={inputClass}>
        <option value="">{placeholder}</option>
        {options.map((opt) => (
          <option key={opt.id} value={opt.id}>
            {showCount ? `${opt.name} (${opt.count ?? 0})` : opt.name}
          </option>
        ))}
      </select>
      {optional && options.length === 0 && <p className="mt-1 text-xs text-gray-400">{placeholder}</p>}
    </div>
  );
}
