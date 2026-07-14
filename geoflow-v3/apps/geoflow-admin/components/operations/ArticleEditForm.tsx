"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft, Eye, EyeOff } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { cn } from "@/lib/cn";
import { apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import type { ArticleDetail, ArticleFormOptions, ArticleUpdatePayload } from "@/lib/article-form-types";
import { zh } from "@/lib/i18n/zh";

const inputClass =
  "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";
const labelClass = "block text-sm font-medium text-gray-700";

export function ArticleEditForm({ articleId }: { articleId: number }) {
  const router = useRouter();
  const [article, setArticle] = useState<ArticleDetail | null>(null);
  const [options, setOptions] = useState<ArticleFormOptions | null>(null);
  const [form, setForm] = useState<ArticleUpdatePayload | null>(null);
  const [preview, setPreview] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    Promise.all([
      apiGet<{ article: ArticleDetail }>(`/api/admin/articles/${articleId}`, token),
      apiGet<ArticleFormOptions>("/api/admin/articles/form-options", token),
    ])
      .then(([detail, opts]) => {
        setArticle(detail.article);
        setOptions(opts);
        setForm({
          title: detail.article.title,
          excerpt: detail.article.excerpt,
          content: detail.article.content,
          keywords: detail.article.keywords,
          meta_description: detail.article.meta_description,
          status: normalizeStatus(detail.article.status),
          review_status: normalizeReview(detail.article.review_status),
          category_id: detail.article.category_id,
          author_id: detail.article.author_id,
        });
      })
      .catch(() => setError(zh.articleEdit.loadError))
      .finally(() => setLoading(false));
  }, [articleId]);

  function patch<K extends keyof ArticleUpdatePayload>(key: K, value: ArticleUpdatePayload[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form) return;
    const token = getToken();
    if (!token) return;

    setSubmitting(true);
    setError("");
    setSuccess("");
    try {
      const res = await apiPatch<{ article: ArticleDetail }>(`/api/admin/articles/${articleId}`, token, form);
      setArticle(res.article);
      setSuccess(zh.articleEdit.saveSuccess);
    } catch {
      setError(zh.articleEdit.saveError);
    } finally {
      setSubmitting(false);
    }
  }

  async function runAction(action: "review" | "publish" | "trash") {
    const token = getToken();
    if (!token) return;
    setActionBusy(true);
    setError("");
    try {
      await apiPost(`/api/admin/articles/${articleId}/${action}`, token);
      if (action === "trash") {
        router.push("/operations/articles");
        return;
      }
      const detail = await apiGet<{ article: ArticleDetail }>(`/api/admin/articles/${articleId}`, token);
      setArticle(detail.article);
      if (form) {
        setForm({
          ...form,
          status: normalizeStatus(detail.article.status),
          review_status: normalizeReview(detail.article.review_status),
        });
      }
      setSuccess(zh.articleEdit.actionSuccess(action));
    } catch {
      setError(zh.articleEdit.actionError);
    } finally {
      setActionBusy(false);
    }
  }

  if (loading || !form || !article || !options) {
    return <FlashAlert variant="info">{zh.common.loading}</FlashAlert>;
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-4">
          <Link href="/operations/articles" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{zh.articleEdit.title}</h1>
            <p className="mt-1 line-clamp-1 text-sm text-gray-600">{article.title}</p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {article.review_status === "pending" && (
            <QuickAction disabled={actionBusy} onClick={() => runAction("review")}>
              {zh.articles.actionReview}
            </QuickAction>
          )}
          {article.status !== "published" && article.review_status === "approved" && (
            <QuickAction disabled={actionBusy} primary onClick={() => runAction("publish")}>
              {zh.articles.actionPublish}
            </QuickAction>
          )}
          <QuickAction disabled={actionBusy} danger onClick={() => runAction("trash")}>
            {zh.articles.actionTrash}
          </QuickAction>
        </div>
      </div>

      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {success && <FlashAlert variant="success">{success}</FlashAlert>}

      {article.geo_eval_enabled && article.eval_status && (
        <EvalBanner article={article} />
      )}

      <form onSubmit={onSubmit} className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        <div className="space-y-6 lg:col-span-3">
          <Section title={zh.articleEdit.sections.basic}>
            <div className="space-y-4">
              <div>
                <label htmlFor="title" className={labelClass}>
                  {zh.articleEdit.fields.title} *
                </label>
                <input id="title" required value={form.title} onChange={(e) => patch("title", e.target.value)} className={inputClass} />
              </div>
              <div>
                <label htmlFor="excerpt" className={labelClass}>
                  {zh.articleEdit.fields.excerpt}
                </label>
                <textarea id="excerpt" rows={3} value={form.excerpt} onChange={(e) => patch("excerpt", e.target.value)} className={inputClass} />
              </div>
            </div>
          </Section>

          <Section
            title={zh.articleEdit.sections.content}
            action={
              <button
                type="button"
                onClick={() => setPreview((p) => !p)}
                className="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                {preview ? <EyeOff className="mr-1 h-4 w-4" /> : <Eye className="mr-1 h-4 w-4" />}
                {preview ? zh.articleEdit.hidePreview : zh.articleEdit.showPreview}
              </button>
            }
          >
            {preview ? (
              <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-gray-200 bg-gray-50 p-4 text-sm leading-6 text-gray-800">
                {form.content}
              </pre>
            ) : (
              <textarea
                required
                value={form.content}
                onChange={(e) => patch("content", e.target.value)}
                className={cn(inputClass, "min-h-96 font-mono text-sm leading-6")}
              />
            )}
            <p className="mt-2 text-xs text-gray-500">{zh.articleEdit.hints.markdown}</p>
          </Section>

          <Section title={zh.articleEdit.sections.seo}>
            <div className="space-y-4">
              <div>
                <label htmlFor="keywords" className={labelClass}>
                  {zh.articleEdit.fields.keywords}
                </label>
                <input id="keywords" value={form.keywords} onChange={(e) => patch("keywords", e.target.value)} className={inputClass} />
              </div>
              <div>
                <label htmlFor="meta_description" className={labelClass}>
                  {zh.articleEdit.fields.metaDescription}
                </label>
                <textarea
                  id="meta_description"
                  rows={3}
                  value={form.meta_description}
                  onChange={(e) => patch("meta_description", e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
          </Section>
        </div>

        <div className="space-y-6">
          <Section title={zh.articleEdit.sections.publish}>
            <div className="space-y-4">
              <div>
                <label className={labelClass}>{zh.articleEdit.fields.status}</label>
                <select value={form.status} onChange={(e) => patch("status", e.target.value as ArticleUpdatePayload["status"])} className={inputClass}>
                  <option value="draft">{zh.articleEdit.status.draft}</option>
                  <option value="published">{zh.articleEdit.status.published}</option>
                  <option value="private">{zh.articleEdit.status.private}</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>{zh.articleEdit.fields.reviewStatus}</label>
                <select
                  value={form.review_status}
                  onChange={(e) => patch("review_status", e.target.value as ArticleUpdatePayload["review_status"])}
                  className={inputClass}
                >
                  <option value="pending">{zh.articleEdit.review.pending}</option>
                  <option value="approved">{zh.articleEdit.review.approved}</option>
                  <option value="rejected">{zh.articleEdit.review.rejected}</option>
                  <option value="auto_approved">{zh.articleEdit.review.autoApproved}</option>
                </select>
              </div>
            </div>
          </Section>

          <Section title={zh.articleEdit.sections.categoryAuthor}>
            <div className="space-y-4">
              <div>
                <label className={labelClass}>{zh.articleEdit.fields.category} *</label>
                <select required value={form.category_id} onChange={(e) => patch("category_id", Number(e.target.value))} className={inputClass}>
                  <option value="">{zh.articleEdit.options.selectCategory}</option>
                  {options.categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>{zh.articleEdit.fields.author} *</label>
                <select required value={form.author_id} onChange={(e) => patch("author_id", Number(e.target.value))} className={inputClass}>
                  <option value="">{zh.articleEdit.options.selectAuthor}</option>
                  {options.authors.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </Section>

          <Section title={zh.articleEdit.sections.info}>
            <dl className="space-y-2 text-sm text-gray-600">
              <div>
                <dt className="text-gray-400">{zh.articleEdit.info.id}</dt>
                <dd>#{article.id}</dd>
              </div>
              <div>
                <dt className="text-gray-400">{zh.articleEdit.info.slug}</dt>
                <dd className="break-all">{article.slug}</dd>
              </div>
              <div>
                <dt className="text-gray-400">{zh.articleEdit.info.task}</dt>
                <dd>{article.task_name || zh.articleEdit.info.manual}</dd>
              </div>
              <div>
                <dt className="text-gray-400">{zh.articleEdit.info.views}</dt>
                <dd>{article.view_count}</dd>
              </div>
              <div>
                <dt className="text-gray-400">{zh.articleEdit.info.publishedAt}</dt>
                <dd>{article.published_at ? new Date(article.published_at).toLocaleString("zh-CN") : "—"}</dd>
              </div>
            </dl>
          </Section>

          <div className="flex justify-end gap-3">
            <Link href="/operations/articles" className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              {zh.articleEdit.cancel}
            </Link>
            <button type="submit" disabled={submitting} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {submitting ? zh.common.loading : zh.articleEdit.save}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
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

function formatScore(v: number | null | undefined): string {
  return typeof v === "number" && Number.isFinite(v) ? v.toFixed(2) : "—";
}

function EvalBanner({ article }: { article: ArticleDetail }) {
  const tone =
    article.eval_status === "passed"
      ? "border-cyan-200 bg-cyan-50 text-cyan-900"
      : article.eval_status === "failed"
        ? "border-red-200 bg-red-50 text-red-900"
        : article.eval_status === "advisory"
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : article.eval_status === "pending_eval"
            ? "border-amber-200 bg-amber-50 text-amber-900"
            : "border-slate-200 bg-slate-50 text-slate-800";

  const recs = article.eval_recommendations || [];
  const soft = (article.eval_gate_mode || "soft") === "soft" || !article.geo_eval_hard_gate;
  const hasScores =
    typeof article.eval_simulation_score === "number" ||
    typeof article.eval_audit_score === "number" ||
    typeof article.eval_retrieval_score === "number";

  return (
    <div className={cn("mb-6 rounded-lg border px-4 py-3 text-sm", tone)}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-semibold">
          {zh.articleEdit.eval.title}
          <span className="ml-2 font-normal">
            · {zh.articleEdit.eval.statusLabel} {article.eval_status}
          </span>
        </p>
        {soft && <p className="text-xs opacity-80">{zh.articleEdit.eval.softMode}</p>}
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div className="rounded-md border border-black/10 bg-white/50 px-3 py-2">
          <p className="text-xs font-semibold uppercase tracking-wide opacity-70">
            {zh.articleEdit.eval.resultSection}
          </p>
          {hasScores ? (
            <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1.5 text-xs sm:grid-cols-3">
              <div>
                <dt className="opacity-60">{zh.articleEdit.eval.simulationScore}</dt>
                <dd className="text-base font-semibold tabular-nums">
                  {formatScore(article.eval_simulation_score)}
                </dd>
              </div>
              <div>
                <dt className="opacity-60">{zh.articleEdit.eval.auditScore}</dt>
                <dd className="text-base font-semibold tabular-nums">
                  {formatScore(article.eval_audit_score)}
                </dd>
              </div>
              <div>
                <dt className="opacity-60">{zh.articleEdit.eval.retrievalScore}</dt>
                <dd className="text-base font-semibold tabular-nums">
                  {formatScore(article.eval_retrieval_score)}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="mt-2 text-xs opacity-70">{zh.articleEdit.eval.noScoreYet}</p>
          )}
          {typeof article.eval_audit_passed === "boolean" && (
            <p className="mt-2 text-xs">
              {article.eval_audit_passed ? zh.articleEdit.eval.auditPass : zh.articleEdit.eval.auditFail}
            </p>
          )}
          {article.eval_query && (
            <p className="mt-2 text-xs">
              <span className="opacity-60">{zh.articleEdit.eval.query}：</span>
              {article.eval_query}
            </p>
          )}
          {article.eval_simulated_answer && (
            <p className="mt-1 line-clamp-3 text-xs opacity-80">
              <span className="opacity-60">{zh.articleEdit.eval.simulatedAnswer}：</span>
              {article.eval_simulated_answer}
            </p>
          )}
          {article.eval_status === "failed" && article.eval_failure_reason && (
            <p className="mt-2 text-xs">{zh.articleEdit.eval.reason(article.eval_failure_reason)}</p>
          )}
          {article.eval_status === "advisory" && article.eval_failure_reason && (
            <p className="mt-2 text-xs">{zh.articleEdit.eval.advisoryReason(article.eval_failure_reason)}</p>
          )}
        </div>

          <div className="rounded-md border border-black/10 bg-white/50 px-3 py-2">
          <p className="text-xs font-semibold uppercase tracking-wide opacity-70">
            {zh.articleEdit.eval.adviceSection}
          </p>
          {recs.length > 0 ? (
            <ul className="mt-2 list-inside list-disc space-y-1.5 text-xs leading-5">
              {recs.map((r) => (
                <li key={r.code}>
                  <span className="font-medium">{r.suggestion}</span>
                  {r.detail && r.detail !== r.code && (
                    <span className="ml-1 opacity-60">（{r.detail}）</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-xs opacity-70">{zh.articleEdit.eval.noAdvice}</p>
          )}
        </div>
      </div>

      {!article.geo_eval_gate_enabled && (
        <p className="mt-2 text-xs opacity-80">{zh.articleEdit.eval.gateOff}</p>
      )}
      {article.publish_scope === "distribution_only" && (
        <p className="mt-1 text-xs">{zh.articleEdit.eval.distributionOnly}</p>
      )}
      <Link href="/production/geo-eval" className="mt-3 inline-block text-xs font-medium underline">
        {zh.articleEdit.eval.openDiagnostics}
      </Link>
    </div>
  );
}

function normalizeStatus(status: string): ArticleUpdatePayload["status"] {
  if (status === "published" || status === "private") return status;
  return "draft";
}

function normalizeReview(status: string): ArticleUpdatePayload["review_status"] {
  if (status === "approved" || status === "rejected" || status === "auto_approved") return status;
  return "pending";
}

function QuickAction({
  children,
  onClick,
  disabled,
  primary,
  danger,
}: {
  children: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  primary?: boolean;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50",
        primary && "bg-blue-600 text-white hover:bg-blue-700",
        danger && "border border-red-200 text-red-700 hover:bg-red-50",
        !primary && !danger && "border border-gray-300 text-gray-700 hover:bg-gray-50",
      )}
    >
      {children}
    </button>
  );
}
