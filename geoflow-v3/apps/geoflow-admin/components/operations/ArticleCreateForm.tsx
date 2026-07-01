"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import type { ArticleFormOptions, ArticleUpdatePayload } from "@/lib/article-form-types";
import { zh } from "@/lib/i18n/zh";

const inputClass =
  "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";
const labelClass = "block text-sm font-medium text-gray-700";

export function ArticleCreateForm() {
  const router = useRouter();
  const [options, setOptions] = useState<ArticleFormOptions | null>(null);
  const [form, setForm] = useState<ArticleUpdatePayload>({
    title: "",
    excerpt: "",
    content: "",
    keywords: "",
    meta_description: "",
    status: "draft",
    review_status: "pending",
    category_id: 0,
    author_id: 0,
  });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    apiGet<ArticleFormOptions>("/api/admin/articles/form-options", token)
      .then((opts) => {
        setOptions(opts);
        setForm((prev) => ({
          ...prev,
          category_id: opts.categories[0]?.id ?? 0,
          author_id: opts.authors[0]?.id ?? 0,
        }));
      })
      .catch(() => setError(zh.articleEdit.loadError))
      .finally(() => setLoading(false));
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token || !form.title.trim() || !form.content.trim()) return;
    setSubmitting(true);
    setError("");
    try {
      const res = await apiPost<{ article: { id: number } }>("/api/admin/articles", token, form);
      router.push(`/operations/articles/${res.article.id}`);
    } catch {
      setError(zh.articleCreate.submitError);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <FlashAlert variant="info">{zh.common.loading}</FlashAlert>;

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/operations/articles" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">{zh.articleCreate.title}</h1>
      </div>
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      <div className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
        <label className={labelClass}>标题</label>
        <input className={inputClass} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <label className={`${labelClass} mt-4`}>正文</label>
        <textarea className={`${inputClass} min-h-[240px]`} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} />
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <label className={labelClass}>分类</label>
            <select className={inputClass} value={form.category_id} onChange={(e) => setForm({ ...form, category_id: Number(e.target.value) })}>
              {options?.categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={labelClass}>作者</label>
            <select className={inputClass} value={form.author_id} onChange={(e) => setForm({ ...form, author_id: Number(e.target.value) })}>
              {options?.authors.map((a) => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>
        </div>
        <button type="submit" disabled={submitting} className="mt-6 rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          {submitting ? zh.common.loading : zh.articleCreate.submit}
        </button>
      </div>
    </form>
  );
}
