"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, Eye, EyeOff, Plus, Trash2 } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { cn } from "@/lib/cn";
import { apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import {
  emptyWikiPayload,
  suggestWikiSlug,
  wikiPayloadFromPage,
  WIKI_DOMAINS,
  WIKI_PAGE_TYPES,
  type WikiDetailPayload,
  type WikiPagePayload,
} from "@/lib/wiki-form-types";

const inputClass =
  "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";
const labelClass = "block text-sm font-medium text-gray-700";

const typeLabel = zh.wiki.types as Record<string, string>;
const domainLabel = zh.wiki.domains as Record<string, string>;

export function WikiEditForm({ articleId }: { articleId?: number }) {
  const router = useRouter();
  const isNew = articleId == null;
  const [form, setForm] = useState<WikiPagePayload>(emptyWikiPayload());
  const [slugTouched, setSlugTouched] = useState(!isNew);
  const [previewUrl, setPreviewUrl] = useState("");
  const [synced, setSynced] = useState(false);
  const [geowebUrl, setGeowebUrl] = useState<string | null>(null);
  const [syncEnabled, setSyncEnabled] = useState(true);
  const [previewMd, setPreviewMd] = useState(false);
  const [loading, setLoading] = useState(!isNew);
  const [submitting, setSubmitting] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    if (isNew || !articleId) return;
    const token = getToken();
    if (!token) return;
    apiGet<WikiDetailPayload>(`/api/admin/wiki/${articleId}`, token)
      .then((data) => {
        setForm(wikiPayloadFromPage(data.page));
        setPreviewUrl(data.page.preview_url);
        setSynced(data.page.synced);
        setGeowebUrl(data.page.geoweb_url);
        setSyncEnabled(data.geoweb_sync_enabled);
      })
      .catch(() => setError(zh.wiki.loadError))
      .finally(() => setLoading(false));
  }, [articleId, isNew]);

  function patch<K extends keyof WikiPagePayload>(key: K, value: WikiPagePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function onTitleChange(title: string) {
    const next = { ...form, title };
    if (!slugTouched) next.slug = suggestWikiSlug(title);
    setForm(next);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) return;
    setSubmitting(true);
    setError("");
    setSuccess("");
    try {
      if (isNew) {
        const res = await apiPost<WikiDetailPayload>("/api/admin/wiki", token, toPayload(form));
        router.push(`/operations/wiki/${res.page.id}`);
        return;
      }
      const res = await apiPatch<WikiDetailPayload>(`/api/admin/wiki/${articleId}`, token, toPayload(form));
      setForm(wikiPayloadFromPage(res.page));
      setPreviewUrl(res.page.preview_url);
      setSynced(res.page.synced);
      setGeowebUrl(res.page.geoweb_url);
      setSuccess(zh.wiki.saveSuccess);
    } catch (err) {
      setError(isNew ? zh.wiki.createError : `${zh.wiki.saveError}${detailSuffix(err)}`);
    } finally {
      setSubmitting(false);
    }
  }

  async function onPublish() {
    const token = getToken();
    if (!token || isNew || !articleId) return;
    setPublishing(true);
    setError("");
    setSuccess("");
    try {
      await apiPatch<WikiDetailPayload>(`/api/admin/wiki/${articleId}`, token, toPayload(form));
      const res = await apiPost<WikiDetailPayload>(`/api/admin/wiki/${articleId}/publish`, token);
      setForm(wikiPayloadFromPage(res.page));
      setPreviewUrl(res.page.preview_url);
      setSynced(res.page.synced);
      setGeowebUrl(res.page.geoweb_url);
      setSuccess(res.publish?.dry_run ? zh.wiki.publishDryRun : zh.wiki.publishSuccess);
    } catch (err) {
      setError(`${zh.wiki.publishError}${detailSuffix(err)}`);
    } finally {
      setPublishing(false);
    }
  }

  if (loading) return <FlashAlert variant="info">{zh.common.loading}</FlashAlert>;

  const openUrl = geowebUrl || previewUrl;

  return (
    <form onSubmit={onSubmit}>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-4">
          <Link href="/operations/wiki" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{isNew ? zh.wiki.createTitle : zh.wiki.editTitle}</h1>
            {!isNew && <p className="mt-1 line-clamp-1 text-sm text-gray-600">{form.title}</p>}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {openUrl && (
            <a
              href={openUrl}
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              {zh.wiki.preview}
            </a>
          )}
          {!isNew && (
            <button
              type="button"
              disabled={publishing}
              onClick={onPublish}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {publishing ? zh.common.loading : zh.wiki.publish}
            </button>
          )}
        </div>
      </div>

      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {success && <FlashAlert variant="success">{success}</FlashAlert>}
      {!syncEnabled && !isNew && (
        <FlashAlert variant="info">GEOWEB_SYNC_ENABLED 未开启，发布将走 dry-run。</FlashAlert>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <div className="space-y-6 lg:col-span-3">
          <Section title={zh.wiki.sections.basic}>
            <div className="space-y-4">
              <div>
                <label className={labelClass}>{zh.wiki.fields.title} *</label>
                <input required value={form.title} onChange={(e) => onTitleChange(e.target.value)} className={inputClass} />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className={labelClass}>{zh.wiki.fields.slug} *</label>
                  <input
                    required
                    value={form.slug}
                    onChange={(e) => {
                      setSlugTouched(true);
                      patch("slug", e.target.value.toLowerCase());
                    }}
                    className={cn(inputClass, "font-mono")}
                  />
                  <p className="mt-1 text-xs text-gray-500">{zh.wiki.slugHint}</p>
                </div>
                <div>
                  <label className={labelClass}>{zh.wiki.fields.type} *</label>
                  <select
                    value={form.wiki_page_type}
                    onChange={(e) => patch("wiki_page_type", e.target.value)}
                    className={inputClass}
                  >
                    {WIKI_PAGE_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {typeLabel[type] || type}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className={labelClass}>{zh.wiki.fields.domain}</label>
                  <select value={form.domain} onChange={(e) => patch("domain", e.target.value)} className={inputClass}>
                    <option value="">—</option>
                    {WIKI_DOMAINS.map((d) => (
                      <option key={d} value={d}>
                        {domainLabel[d] || d}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={labelClass}>{zh.wiki.fields.schemaType}</label>
                  <select
                    value={form.schema_type}
                    onChange={(e) => patch("schema_type", e.target.value)}
                    className={inputClass}
                  >
                    <option value="TechArticle">TechArticle</option>
                    <option value="FAQPage">FAQPage</option>
                    <option value="HowTo">HowTo</option>
                  </select>
                </div>
              </div>
            </div>
          </Section>

          <Section title={zh.wiki.sections.geo}>
            <div className="space-y-4">
              <div>
                <label className={labelClass}>{zh.wiki.fields.quickAnswer}</label>
                <input value={form.quick_answer} onChange={(e) => patch("quick_answer", e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>{zh.wiki.fields.coreTakeaway}</label>
                <textarea
                  rows={2}
                  value={form.core_takeaway}
                  onChange={(e) => patch("core_takeaway", e.target.value)}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>{zh.wiki.fields.targetQuery}</label>
                <input value={form.target_query} onChange={(e) => patch("target_query", e.target.value)} className={inputClass} />
              </div>
            </div>
          </Section>

          <Section
            title={zh.wiki.sections.content}
            action={
              <button
                type="button"
                onClick={() => setPreviewMd((p) => !p)}
                className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                {previewMd ? <EyeOff className="mr-1 h-4 w-4" /> : <Eye className="mr-1 h-4 w-4" />}
                {previewMd ? zh.articleEdit.hidePreview : zh.articleEdit.showPreview}
              </button>
            }
          >
            {previewMd ? (
              <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-gray-200 bg-gray-50 p-4 text-sm leading-6 text-gray-800">
                {form.body}
              </pre>
            ) : (
              <textarea
                required
                value={form.body}
                onChange={(e) => patch("body", e.target.value)}
                className={cn(inputClass, "min-h-96 font-mono text-sm leading-6")}
              />
            )}
          </Section>

          <Section title={zh.wiki.sections.related}>
            <div className="space-y-4">
              <div>
                <label className={labelClass}>{zh.wiki.fields.related}</label>
                <textarea
                  rows={4}
                  value={form.related.join("\n")}
                  onChange={(e) =>
                    patch(
                      "related",
                      e.target.value
                        .split("\n")
                        .map((line) => line.trim())
                        .filter(Boolean),
                    )
                  }
                  className={cn(inputClass, "font-mono")}
                />
              </div>
              <div className="space-y-3">
                {form.faq.map((item, idx) => (
                  <div key={idx} className="rounded-md border border-gray-200 p-3">
                    <div className="mb-2 flex justify-end">
                      <button
                        type="button"
                        onClick={() => patch("faq", form.faq.filter((_, i) => i !== idx))}
                        className="text-gray-400 hover:text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                    <input
                      placeholder={zh.wiki.fields.faqQ}
                      value={item.q}
                      onChange={(e) => {
                        const next = [...form.faq];
                        next[idx] = { ...item, q: e.target.value };
                        patch("faq", next);
                      }}
                      className={inputClass}
                    />
                    <textarea
                      placeholder={zh.wiki.fields.faqA}
                      rows={2}
                      value={item.a}
                      onChange={(e) => {
                        const next = [...form.faq];
                        next[idx] = { ...item, a: e.target.value };
                        patch("faq", next);
                      }}
                      className={inputClass}
                    />
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => patch("faq", [...form.faq, { q: "", a: "" }])}
                  className="inline-flex items-center rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
                >
                  <Plus className="mr-1 h-4 w-4" />
                  {zh.wiki.addFaq}
                </button>
              </div>
            </div>
          </Section>
        </div>

        <div className="space-y-6">
          <Section title={zh.wiki.sections.publish}>
            <div className="space-y-4">
              <div>
                <label className={labelClass}>{zh.wiki.fields.geoThemeId}</label>
                <input value={form.geo_theme_id} onChange={(e) => patch("geo_theme_id", e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>{zh.wiki.fields.tags}</label>
                <input
                  value={form.tags.join(", ")}
                  onChange={(e) =>
                    patch(
                      "tags",
                      e.target.value
                        .split(",")
                        .map((t) => t.trim())
                        .filter(Boolean),
                    )
                  }
                  className={inputClass}
                />
              </div>
              {!isNew && (
                <dl className="space-y-2 text-sm text-gray-600">
                  <div>
                    <dt className="text-gray-400">同步</dt>
                    <dd>{synced ? zh.wiki.synced : zh.wiki.draft}</dd>
                  </div>
                  {openUrl && (
                    <div>
                      <dt className="text-gray-400">URL</dt>
                      <dd className="break-all text-xs">{openUrl}</dd>
                    </div>
                  )}
                </dl>
              )}
            </div>
          </Section>
          <div className="flex justify-end gap-3">
            <Link
              href="/operations/wiki"
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              {zh.articleEdit.cancel}
            </Link>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? zh.common.loading : zh.wiki.save}
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}

function toPayload(form: WikiPagePayload) {
  return {
    ...form,
    faq: form.faq.filter((item) => item.q.trim() && item.a.trim()),
  };
}

function detailSuffix(err: unknown): string {
  const msg = err instanceof Error ? err.message : "";
  const match = msg.match(/·\s(.+)$/);
  return match ? ` · ${match[1]}` : "";
}

function Section({
  title,
  children,
  action,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
      <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
        <h3 className="text-lg font-medium text-gray-900">{title}</h3>
        {action}
      </div>
      <div className="px-6 py-4">{children}</div>
    </section>
  );
}
