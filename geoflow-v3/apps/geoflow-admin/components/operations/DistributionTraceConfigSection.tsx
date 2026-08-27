"use client";

import {
  DEFAULT_LINK_TEMPLATE,
  TRACE_PLACEHOLDERS,
  type DistributionCreatePayload,
} from "@/lib/distribution-form-types";
import { zh } from "@/lib/i18n/zh";

const inputClass =
  "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";
const labelClass = "block text-sm font-medium text-gray-700";

type Props = {
  form: DistributionCreatePayload;
  onPatch: <K extends keyof DistributionCreatePayload>(key: K, value: DistributionCreatePayload[K]) => void;
};

function buildPreviewUrl(template: string, slug: string): string {
  const suffix = template
    .replaceAll("{channel_slug}", slug || "demo-channel")
    .replaceAll("{task_id}", "42")
    .replaceAll("{dist_id}", "99")
    .replaceAll("{article_id}", "7")
    .replaceAll("{theme_id}", "11");
  return `https://geo.example.com/articles/demo-slug${suffix.startsWith("?") ? suffix : `?${suffix}`}`;
}

export function DistributionTraceConfigSection({ form, onPatch }: Props) {
  const slug = form.channel_slug.trim() || form.domain.trim() || "demo-channel";
  const previewUrl = buildPreviewUrl(form.link_template || DEFAULT_LINK_TEMPLATE, slug);

  return (
    <div className="mt-6 rounded-lg border border-amber-100 bg-amber-50/60 p-5">
      <h2 className="text-lg font-medium text-gray-900">{zh.distributionCreate.trace.title}</h2>
      <p className="mt-1 text-sm text-gray-600">{zh.distributionCreate.trace.desc}</p>

      <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2">
        <div>
          <label className={labelClass}>{zh.distributionCreate.trace.mode}</label>
          <select
            value={form.trace_mode}
            onChange={(e) => onPatch("trace_mode", e.target.value as DistributionCreatePayload["trace_mode"])}
            className={inputClass}
          >
            <option value="suffix">{zh.distributionCreate.trace.modeSuffix}</option>
            <option value="off">{zh.distributionCreate.trace.modeOff}</option>
          </select>
        </div>
        <div>
          <label className={labelClass}>{zh.distributionCreate.trace.channelSlug}</label>
          <input
            value={form.channel_slug}
            onChange={(e) => onPatch("channel_slug", e.target.value)}
            className={inputClass}
            placeholder="weibo / wechat-mp"
          />
          <p className="mt-1 text-xs text-gray-500">{zh.distributionCreate.trace.channelSlugHint}</p>
        </div>
      </div>

      <div className="mt-4">
        <label className={labelClass}>{zh.distributionCreate.trace.linkTemplate}</label>
        <textarea
          rows={3}
          value={form.link_template}
          onChange={(e) => onPatch("link_template", e.target.value)}
          className={inputClass}
          spellCheck={false}
        />
        <p className="mt-1 text-xs text-gray-500">{zh.distributionCreate.trace.linkTemplateHint}</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {TRACE_PLACEHOLDERS.map((token) => (
            <button
              key={token}
              type="button"
              onClick={() => {
                const key = token.replace(/[{}]/g, "");
                const piece = form.link_template.includes("?") ? `&${key}=${token}` : `?${key}=${token}`;
                onPatch("link_template", `${form.link_template}${piece}`);
              }}
              className="rounded border border-gray-200 bg-white px-2 py-0.5 font-mono text-xs text-gray-600 hover:border-blue-300 hover:text-blue-700"
            >
              {token}
            </button>
          ))}
          <button
            type="button"
            onClick={() => onPatch("link_template", DEFAULT_LINK_TEMPLATE)}
            className="rounded border border-gray-200 bg-white px-2 py-0.5 text-xs text-gray-600 hover:border-blue-300"
          >
            {zh.distributionCreate.trace.resetTemplate}
          </button>
        </div>
      </div>

      <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-md border border-amber-100 bg-white px-4 py-3 text-sm">
        <input
          type="checkbox"
          checked={form.require_geoweb_first}
          onChange={(e) => onPatch("require_geoweb_first", e.target.checked)}
          className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600"
        />
        <span>
          <span className="block font-medium text-gray-900">{zh.distributionCreate.trace.requireGeowebFirst}</span>
          <span className="mt-1 block text-gray-600">{zh.distributionCreate.trace.requireGeowebFirstHint}</span>
        </span>
      </label>

      {form.trace_mode === "suffix" && (
        <div className="mt-4 rounded-md border border-amber-100 bg-white px-4 py-3 text-sm">
          <p className="font-medium text-gray-700">{zh.distributionCreate.trace.preview}</p>
          <p className="mt-2 break-all font-mono text-xs text-blue-700">{previewUrl}</p>
        </div>
      )}
    </div>
  );
}
