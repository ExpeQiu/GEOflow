"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import {
  DEFAULT_DISTRIBUTION_FORM,
  type DistributionChannelType,
  type DistributionCreatePayload,
  type DistributionFormOptions,
} from "@/lib/distribution-form-types";
import { zh } from "@/lib/i18n/zh";

const inputClass =
  "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";
const labelClass = "block text-sm font-medium text-gray-700";

const CHANNEL_LABELS: Record<DistributionChannelType, { title: string; desc: string }> = {
  geoflow_agent: { title: zh.distributionCreate.types.geoflowAgent, desc: zh.distributionCreate.types.geoflowAgentDesc },
  geoweb: { title: zh.distributionCreate.types.geoweb, desc: zh.distributionCreate.types.geowebDesc },
  wordpress_rest: { title: zh.distributionCreate.types.wordpress, desc: zh.distributionCreate.types.wordpressDesc },
  generic_http_api: { title: zh.distributionCreate.types.generic, desc: zh.distributionCreate.types.genericDesc },
};

export function DistributionChannelCreateForm() {
  const router = useRouter();
  const [options, setOptions] = useState<DistributionFormOptions | null>(null);
  const [form, setForm] = useState<DistributionCreatePayload>(DEFAULT_DISTRIBUTION_FORM);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [showAdvancedChannels, setShowAdvancedChannels] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    apiGet<DistributionFormOptions>("/api/admin/distribution/form-options", token)
      .then((opts) => {
        setOptions(opts);
        setForm((prev) => ({
          ...prev,
          channel_type: opts.default_channel_type,
          endpoint_url: prev.endpoint_url || opts.default_geoweb_base_url || "",
        }));
      })
      .catch(() => setError(zh.distributionCreate.loadError))
      .finally(() => setLoading(false));
  }, []);

  function patch<K extends keyof DistributionCreatePayload>(key: K, value: DistributionCreatePayload[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!form.name.trim() || !form.domain.trim() || !form.endpoint_url.trim()) {
      setError(zh.distributionCreate.errors.required);
      return;
    }

    const token = getToken();
    if (!token) return;

    setSubmitting(true);
    try {
      await apiPost("/api/admin/distribution/channels", token, { ...form, name: form.name.trim() });
      router.push("/operations/distribution");
      router.refresh();
    } catch {
      setError(zh.distributionCreate.submitError);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <FlashAlert variant="info">{zh.common.loading}</FlashAlert>;
  }

  const channelType = form.channel_type;
  const visibleTypes: DistributionChannelType[] = showAdvancedChannels
    ? ([
        ...(options?.channel_types ?? ["geoweb"]),
        ...(options?.advanced_channel_types ?? []),
      ] as DistributionChannelType[])
    : ((options?.channel_types ?? ["geoweb"]) as DistributionChannelType[]);

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/operations/distribution" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{zh.distributionCreate.title}</h1>
          <p className="mt-1 text-sm text-gray-600">{zh.distributionCreate.subtitle}</p>
        </div>
      </div>

      {error && <FlashAlert variant="error">{error}</FlashAlert>}

      <section className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
        <div>
          <label htmlFor="name" className={labelClass}>
            {zh.distributionCreate.fields.name} *
          </label>
          <input id="name" required value={form.name} onChange={(e) => patch("name", e.target.value)} className={inputClass} />
        </div>

        <fieldset className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <legend className="text-sm font-medium text-gray-900">{zh.distributionCreate.fields.channelType}</legend>
          <p className="mt-1 text-sm text-gray-600">{zh.distributionCreate.hints.channelType}</p>
          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-3">
            {visibleTypes.map((type) => {
              const key = type as DistributionChannelType;
              const meta = CHANNEL_LABELS[key];
              if (!meta) return null;
              return (
                <label
                  key={key}
                  className="flex cursor-pointer gap-3 rounded-md border border-gray-200 bg-white p-4 hover:border-blue-300"
                >
                  <input
                    type="radio"
                    name="channel_type"
                    value={key}
                    checked={channelType === key}
                    onChange={() => patch("channel_type", key)}
                    className="mt-1 text-blue-600"
                  />
                  <span>
                    <span className="block text-sm font-semibold text-gray-900">{meta.title}</span>
                    <span className="mt-1 block text-sm text-gray-600">{meta.desc}</span>
                  </span>
                </label>
              );
            })}
          </div>
          <label className="mt-4 flex cursor-pointer items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showAdvancedChannels}
              onChange={(e) => setShowAdvancedChannels(e.target.checked)}
            />
            显示高级渠道（WordPress / HTTP / Agent）
          </label>
        </fieldset>

        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <label htmlFor="domain" className={labelClass}>
              {zh.distributionCreate.fields.domain} *
            </label>
            <input id="domain" required value={form.domain} onChange={(e) => patch("domain", e.target.value)} className={inputClass} placeholder="example.com" />
          </div>
          <div>
            <label htmlFor="endpoint_url" className={labelClass}>
              {zh.distributionCreate.fields.endpoint} *
            </label>
            <input
              id="endpoint_url"
              required
              value={form.endpoint_url}
              onChange={(e) => patch("endpoint_url", e.target.value)}
              className={inputClass}
              placeholder="https://example.com/api"
            />
            <p className="mt-1 text-xs text-gray-500">{zh.distributionCreate.hints.endpoint}</p>
          </div>
        </div>

        {channelType === "geoflow_agent" && (
          <div className="mt-6 space-y-6">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <label className={labelClass}>{zh.distributionCreate.fields.templateKey}</label>
                <input value={form.template_key} onChange={(e) => patch("template_key", e.target.value)} className={inputClass} placeholder="default" />
              </div>
            </div>
            <fieldset className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <legend className="text-sm font-medium text-gray-900">{zh.distributionCreate.fields.frontMode}</legend>
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                {(["static", "rewrite"] as const).map((mode) => (
                  <label key={mode} className="flex cursor-pointer gap-3 rounded-md border border-gray-200 bg-white p-4">
                    <input type="radio" name="front_mode" checked={form.front_mode === mode} onChange={() => patch("front_mode", mode)} className="mt-1" />
                    <span>
                      <span className="block text-sm font-semibold text-gray-900">
                        {mode === "static" ? zh.distributionCreate.frontMode.static : zh.distributionCreate.frontMode.rewrite}
                      </span>
                      <span className="mt-1 block text-sm text-gray-600">
                        {mode === "static" ? zh.distributionCreate.frontMode.staticDesc : zh.distributionCreate.frontMode.rewriteDesc}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
        )}

        {channelType === "geoweb" && (
          <div className="mt-6 rounded-lg border border-sky-100 bg-sky-50 p-5">
            <h2 className="text-lg font-medium text-gray-900">{zh.distributionCreate.geoweb.title}</h2>
            <p className="mt-1 text-sm text-gray-600">{zh.distributionCreate.geoweb.desc}</p>
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <label className={labelClass}>{zh.distributionCreate.geoweb.syncToken} *</label>
                <input
                  type="password"
                  value={form.geoweb_sync_token}
                  onChange={(e) => patch("geoweb_sync_token", e.target.value)}
                  className={inputClass}
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className={labelClass}>{zh.distributionCreate.geoweb.timeout}</label>
                <input
                  type="number"
                  min={5}
                  max={120}
                  value={form.geoweb_timeout_seconds}
                  onChange={(e) => patch("geoweb_timeout_seconds", Number(e.target.value))}
                  className={inputClass}
                />
              </div>
              <div className="md:col-span-2">
                <label className={labelClass}>{zh.distributionCreate.geoweb.defaultPageType}</label>
                <select
                  value={form.geoweb_default_page_type}
                  onChange={(e) => patch("geoweb_default_page_type", e.target.value)}
                  className={inputClass}
                >
                  <option value="article">article → /articles</option>
                  <option value="concept">concept → /concepts</option>
                  <option value="compare">compare → /compare</option>
                  <option value="guide">guide → /guides</option>
                  <option value="glossary">glossary → /glossary</option>
                  <option value="data">data → /data</option>
                  <option value="thread">thread → /threads</option>
                  <option value="topic">topic → /topics</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">{zh.distributionCreate.geoweb.defaultPageTypeHint}</p>
              </div>
            </div>
          </div>
        )}

        {channelType === "wordpress_rest" && (
          <div className="mt-6 rounded-lg border border-blue-100 bg-blue-50 p-5">
            <h2 className="text-lg font-medium text-gray-900">{zh.distributionCreate.wordpress.title}</h2>
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2">
              <div>
                <label className={labelClass}>{zh.distributionCreate.wordpress.username} *</label>
                <input value={form.wordpress_username} onChange={(e) => patch("wordpress_username", e.target.value)} className={inputClass} />
              </div>
              <div>
                <label className={labelClass}>{zh.distributionCreate.wordpress.password} *</label>
                <input
                  type="password"
                  value={form.wordpress_application_password}
                  onChange={(e) => patch("wordpress_application_password", e.target.value)}
                  className={inputClass}
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className={labelClass}>{zh.distributionCreate.wordpress.postStatus}</label>
                <select
                  value={form.wordpress_post_status}
                  onChange={(e) => patch("wordpress_post_status", e.target.value as DistributionCreatePayload["wordpress_post_status"])}
                  className={inputClass}
                >
                  <option value="draft">{zh.distributionCreate.wordpress.statusDraft}</option>
                  <option value="publish">{zh.distributionCreate.wordpress.statusPublish}</option>
                  <option value="pending">{zh.distributionCreate.wordpress.statusPending}</option>
                  <option value="private">{zh.distributionCreate.wordpress.statusPrivate}</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>{zh.distributionCreate.wordpress.imageStrategy}</label>
                <select
                  value={form.wordpress_image_strategy}
                  onChange={(e) => patch("wordpress_image_strategy", e.target.value as DistributionCreatePayload["wordpress_image_strategy"])}
                  className={inputClass}
                >
                  <option value="upload_to_media">{zh.distributionCreate.wordpress.imageUpload}</option>
                  <option value="keep_original">{zh.distributionCreate.wordpress.imageKeep}</option>
                </select>
              </div>
            </div>
          </div>
        )}

        {channelType === "generic_http_api" && (
          <div className="mt-6 rounded-lg border border-indigo-100 bg-indigo-50 p-5">
            <h2 className="text-lg font-medium text-gray-900">{zh.distributionCreate.generic.title}</h2>
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-3">
              <div>
                <label className={labelClass}>{zh.distributionCreate.generic.authType}</label>
                <select
                  value={form.generic_auth_type}
                  onChange={(e) => patch("generic_auth_type", e.target.value as DistributionCreatePayload["generic_auth_type"])}
                  className={inputClass}
                >
                  <option value="bearer">Bearer</option>
                  <option value="none">{zh.distributionCreate.generic.authNone}</option>
                  <option value="basic">Basic</option>
                  <option value="header_key">Header Key</option>
                  <option value="hmac">HMAC</option>
                </select>
              </div>
              {form.generic_auth_type === "basic" && (
                <div>
                  <label className={labelClass}>{zh.distributionCreate.generic.basicUser}</label>
                  <input value={form.generic_basic_username} onChange={(e) => patch("generic_basic_username", e.target.value)} className={inputClass} />
                </div>
              )}
              {form.generic_auth_type !== "none" && (
                <div>
                  <label className={labelClass}>{zh.distributionCreate.generic.secret}</label>
                  <input
                    type="password"
                    value={form.generic_secret}
                    onChange={(e) => patch("generic_secret", e.target.value)}
                    className={inputClass}
                    autoComplete="new-password"
                  />
                </div>
              )}
            </div>
            <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-3">
              <div>
                <label className={labelClass}>{zh.distributionCreate.generic.publishMethod}</label>
                <select
                  value={form.generic_publish_method}
                  onChange={(e) => patch("generic_publish_method", e.target.value as DistributionCreatePayload["generic_publish_method"])}
                  className={inputClass}
                >
                  {["POST", "PUT", "PATCH"].map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <label className={labelClass}>{zh.distributionCreate.generic.publishPath}</label>
                <input value={form.generic_publish_path} onChange={(e) => patch("generic_publish_path", e.target.value)} className={inputClass} />
              </div>
            </div>
          </div>
        )}

        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <label className={labelClass}>{zh.distributionCreate.fields.status}</label>
            <select value={form.status} onChange={(e) => patch("status", e.target.value as DistributionCreatePayload["status"])} className={inputClass}>
              <option value="active">{zh.distributionCreate.status.active}</option>
              <option value="paused">{zh.distributionCreate.status.paused}</option>
            </select>
          </div>
        </div>

        <div className="mt-6">
          <label className={labelClass}>{zh.distributionCreate.fields.description}</label>
          <textarea rows={4} value={form.description} onChange={(e) => patch("description", e.target.value)} className={inputClass} />
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Link href="/operations/distribution" className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
            {zh.distributionCreate.cancel}
          </Link>
          <button type="submit" disabled={submitting} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {submitting ? zh.common.loading : zh.distributionCreate.submit}
          </button>
        </div>
      </section>
    </form>
  );
}
