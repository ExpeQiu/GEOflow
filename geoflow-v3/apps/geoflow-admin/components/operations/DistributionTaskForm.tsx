"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { cn } from "@/lib/cn";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import type { AdminArticle, DistributionChannelRow } from "@/lib/operations-types";

const inputClass =
  "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

type DistributionMode = "geoweb_only" | "geoweb_and_external" | "external_only";

type LinkPreview = {
  channel_id: number;
  channel_name: string;
  channel_type: string;
  canonical_url: string | null;
  tracked_url: string | null;
};

const MODE_OPTIONS: { value: DistributionMode; label: string }[] = [
  { value: "geoweb_and_external", label: zh.distributionTask.modeGeowebAndExternal },
  { value: "geoweb_only", label: zh.distributionTask.modeGeowebOnly },
  { value: "external_only", label: zh.distributionTask.modeExternalOnly },
];

function isGeoweb(type: string) {
  return type === "geoweb";
}

export function DistributionTaskForm() {
  const router = useRouter();
  const [articles, setArticles] = useState<AdminArticle[]>([]);
  const [channels, setChannels] = useState<DistributionChannelRow[]>([]);
  const [selectedArticles, setSelectedArticles] = useState<Set<number>>(new Set());
  const [selectedChannels, setSelectedChannels] = useState<Set<number>>(new Set());
  const [distributionMode, setDistributionMode] = useState<DistributionMode>("geoweb_and_external");
  const [rhythm, setRhythm] = useState<"immediate" | "interval">("immediate");
  const [intervalSeconds, setIntervalSeconds] = useState(60);
  const [linkPreviews, setLinkPreviews] = useState<LinkPreview[]>([]);
  const [previewCanonical, setPreviewCanonical] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    Promise.all([
      apiGet<{ articles: AdminArticle[] }>("/api/admin/articles", token),
      apiGet<{ channels: DistributionChannelRow[] }>("/api/admin/distribution", token),
    ])
      .then(([articleData, distData]) => {
        const published = (articleData.articles || []).filter((a) => a.status === "published");
        setArticles(published);
        const active = (distData.channels || []).filter((c) => c.status === "active");
        setChannels(active);
        const geoweb = active.find((c) => isGeoweb(c.channel_type));
        if (geoweb) setSelectedChannels(new Set([geoweb.id]));
      })
      .catch(() => setError(zh.distributionTask.loadError))
      .finally(() => setLoading(false));
  }, []);

  const activeChannels = useMemo(() => channels.filter((c) => c.status === "active"), [channels]);
  const geowebChannels = useMemo(() => activeChannels.filter((c) => isGeoweb(c.channel_type)), [activeChannels]);
  const externalChannels = useMemo(() => activeChannels.filter((c) => !isGeoweb(c.channel_type)), [activeChannels]);

  const selectedExternalIds = useMemo(
    () => [...selectedChannels].filter((id) => externalChannels.some((c) => c.id === id)),
    [selectedChannels, externalChannels],
  );

  useEffect(() => {
    const token = getToken();
    const articleId = [...selectedArticles][0];
    if (!token || !articleId || selectedExternalIds.length === 0) {
      setLinkPreviews([]);
      setPreviewCanonical(null);
      return;
    }
    const qs = new URLSearchParams({
      article_id: String(articleId),
      channel_ids: selectedExternalIds.join(","),
    });
    apiGet<{ canonical_url: string | null; previews: LinkPreview[] }>(
      `/api/admin/distribution/preview-links?${qs}`,
      token,
    )
      .then((data) => {
        setPreviewCanonical(data.canonical_url);
        setLinkPreviews(data.previews || []);
      })
      .catch(() => {
        setLinkPreviews([]);
        setPreviewCanonical(null);
      });
  }, [selectedArticles, selectedExternalIds]);

  function toggleArticle(id: number, checked: boolean) {
    setSelectedArticles((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function toggleChannel(id: number, checked: boolean) {
    setSelectedChannels((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function toggleAllArticles() {
    if (selectedArticles.size === articles.length) setSelectedArticles(new Set());
    else setSelectedArticles(new Set(articles.map((a) => a.id)));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setFlash("");
    if (selectedArticles.size === 0) {
      setError(zh.distributionTask.articlesRequired);
      return;
    }
    if (selectedChannels.size === 0) {
      setError(zh.distributionTask.channelsRequired);
      return;
    }
    const token = getToken();
    if (!token) return;

    setSubmitting(true);
    try {
      const res = await apiPost<{
        queued: number;
        jobs_created: number;
        jobs_skipped: number;
        channel_ids?: number[];
      }>("/api/admin/distribution/batch", token, {
        article_ids: [...selectedArticles],
        channel_ids: [...selectedChannels],
        interval_seconds: rhythm === "interval" ? Math.max(0, intervalSeconds) : 0,
        distribution_mode: distributionMode,
      });
      setFlash(`已入队 ${res.queued} 篇 · 新建 ${res.jobs_created} · 跳过已成功 ${res.jobs_skipped}`);
      setTimeout(() => {
        router.push("/operations/distribution/jobs");
        router.refresh();
      }, 600);
    } catch {
      setError(zh.distributionTask.submitError);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <FlashAlert variant="info">{zh.common.loading}</FlashAlert>;
  }

  function renderChannelGroup(list: DistributionChannelRow[], title: string) {
    if (list.length === 0) return null;
    return (
      <div className="space-y-2">
        <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{title}</p>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {list.map((ch) => (
            <label
              key={ch.id}
              className="flex cursor-pointer items-start gap-3 rounded-md border border-gray-200 px-4 py-3 text-sm hover:border-blue-300 hover:bg-blue-50"
            >
              <input
                type="checkbox"
                checked={selectedChannels.has(ch.id)}
                onChange={(e) => toggleChannel(ch.id, e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600"
              />
              <span>
                <span className="block font-medium text-gray-900">{ch.name}</span>
                <span className="block text-gray-500">{ch.channel_type}</span>
              </span>
            </label>
          ))}
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3 text-sm text-blue-900">
        {zh.distributionTask.subtitle}{" "}
        <Link href="/production/tasks" className="font-medium text-blue-700 hover:underline">
          {zh.distributionTask.goContentTasks}
        </Link>
      </div>

      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}

      <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <div className="border-b border-gray-100 px-6 py-4">
          <h3 className="text-lg font-medium text-gray-900">{zh.distributionTask.distributionMode}</h3>
        </div>
        <div className="grid grid-cols-1 gap-3 px-6 py-4 md:grid-cols-3">
          {MODE_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-md border px-4 py-3 text-sm",
                distributionMode === opt.value ? "border-blue-300 bg-blue-50" : "border-gray-200 hover:border-blue-200",
              )}
            >
              <input
                type="radio"
                name="distribution_mode"
                checked={distributionMode === opt.value}
                onChange={() => setDistributionMode(opt.value)}
                className="mt-1 h-4 w-4 border-gray-300 text-blue-600"
              />
              <span className="font-medium text-gray-900">{opt.label}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <div>
            <h3 className="text-lg font-medium text-gray-900">{zh.distributionTask.selectArticles}</h3>
            <p className="mt-1 text-sm text-gray-500">仅展示已发布文章 · 已选 {selectedArticles.size}</p>
          </div>
          {articles.length > 0 && (
            <button type="button" onClick={toggleAllArticles} className="text-sm text-blue-600 hover:underline">
              {selectedArticles.size === articles.length ? "取消全选" : "全选"}
            </button>
          )}
        </div>
        <div className="max-h-80 overflow-y-auto px-6 py-4">
          {articles.length === 0 ? (
            <p className="text-sm text-gray-500">
              {zh.distributionTask.noArticles}{" "}
              <Link href="/production/tasks" className="text-blue-600 hover:underline">
                {zh.distributionTask.goContentTasks}
              </Link>
            </p>
          ) : (
            <div className="space-y-2">
              {articles.map((a) => (
                <label key={a.id} className="flex cursor-pointer items-start gap-3 rounded-md border border-gray-100 px-3 py-2 hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selectedArticles.has(a.id)}
                    onChange={(e) => toggleArticle(a.id, e.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-gray-900">{a.title}</span>
                    <span className="text-xs text-gray-500">
                      #{a.id} · {a.content_format || "article"}
                      {a.task_id ? ` · 任务 #${a.task_id}` : ""}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <div className="border-b border-gray-100 px-6 py-4">
          <h3 className="text-lg font-medium text-gray-900">{zh.distributionTask.selectChannels}</h3>
          <p className="mt-1 text-sm text-gray-500">已选 {selectedChannels.size}</p>
        </div>
        <div className="space-y-6 px-6 py-4">
          {activeChannels.length === 0 ? (
            <p className="text-sm text-gray-500">
              {zh.distributionTask.noChannels}{" "}
              <Link href="/operations/distribution/new" className="text-blue-600 hover:underline">
                {zh.distribution.createButton}
              </Link>
            </p>
          ) : (
            <>
              {renderChannelGroup(geowebChannels, zh.distributionTask.geowebChannels)}
              {renderChannelGroup(externalChannels, zh.distributionTask.externalChannels)}
            </>
          )}
        </div>
      </section>

      {selectedExternalIds.length > 0 && selectedArticles.size > 0 && (
        <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
          <div className="border-b border-gray-100 px-6 py-4">
            <h3 className="text-lg font-medium text-gray-900">{zh.distributionTask.linkPreview}</h3>
            <p className="mt-1 text-sm text-gray-500">{zh.distributionTask.linkPreviewHint}</p>
          </div>
          <div className="space-y-3 px-6 py-4 text-sm">
            {previewCanonical ? (
              <p>
                <span className="font-medium text-gray-700">{zh.distributionTask.canonicalUrl}：</span>
                <span className="break-all text-blue-700">{previewCanonical}</span>
              </p>
            ) : (
              <p className="text-amber-700">暂无主站链接，「GEOweb + 外渠」模式下会先同步 GEOweb。</p>
            )}
            {linkPreviews
              .filter((p) => !isGeoweb(p.channel_type))
              .map((p) => (
                <div key={p.channel_id} className="rounded-md border border-gray-100 bg-gray-50 px-3 py-2">
                  <p className="font-medium text-gray-900">{p.channel_name}</p>
                  <p className="mt-1 break-all text-gray-600">
                    {zh.distributionTask.trackedUrl}：{p.tracked_url || "—"}
                  </p>
                </div>
              ))}
          </div>
        </section>
      )}

      <section className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
        <div className="border-b border-gray-100 px-6 py-4">
          <h3 className="text-lg font-medium text-gray-900">{zh.distributionTask.rhythm}</h3>
        </div>
        <div className="grid grid-cols-1 gap-4 px-6 py-4 md:grid-cols-2">
          {(
            [
              ["immediate", zh.distributionTask.rhythmImmediate],
              ["interval", zh.distributionTask.rhythmInterval],
            ] as const
          ).map(([value, label]) => (
            <label
              key={value}
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-md border px-4 py-3 text-sm",
                rhythm === value ? "border-blue-300 bg-blue-50" : "border-gray-200 hover:border-blue-200",
              )}
            >
              <input
                type="radio"
                name="rhythm"
                checked={rhythm === value}
                onChange={() => setRhythm(value)}
                className="mt-1 h-4 w-4 border-gray-300 text-blue-600"
              />
              <span className="font-medium text-gray-900">{label}</span>
            </label>
          ))}
          {rhythm === "interval" && (
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700">{zh.distributionTask.intervalSeconds}</label>
              <input
                type="number"
                min={0}
                max={86400}
                value={intervalSeconds}
                onChange={(e) => setIntervalSeconds(Number(e.target.value))}
                className={inputClass}
              />
            </div>
          )}
        </div>
      </section>

      <div className="flex justify-end gap-3">
        <Link
          href="/operations/distribution/jobs"
          className="rounded-md border border-gray-300 bg-white px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          {zh.distributionTask.goJobs}
        </Link>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? zh.common.loading : zh.distributionTask.submit}
        </button>
      </div>
    </form>
  );
}
