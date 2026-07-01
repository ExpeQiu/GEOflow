"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, getToken } from "@/lib/api-client";
import type { SiteSettingsPayload } from "@/lib/dashboard-types";
import { zh } from "@/lib/i18n/zh";
import { Globe, Shield, Sparkles, Zap } from "lucide-react";

type ExtendedSiteSettings = SiteSettingsPayload & {
  editable?: boolean;
  db_settings?: { key: string; value: string; group: string }[];
};

function BoolBadge({ enabled, onLabel, offLabel }: { enabled: boolean; onLabel: string; offLabel: string }) {
  return (
    <span
      className={
        enabled
          ? "inline-flex rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700"
          : "inline-flex rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-600"
      }
    >
      {enabled ? onLabel : offLabel}
    </span>
  );
}

export default function SettingsPage() {
  useAuthGuard();
  const [data, setData] = useState<ExtendedSiteSettings | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<ExtendedSiteSettings>("/api/admin/settings/site", t)
      .then(setData)
      .catch(() => setError("无法加载站点设置"));
  }, []);

  return (
    <div>
      <HubHeader title={zh.settings.title} subtitle={zh.settings.subtitle} />
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {!data && !error && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {data && (
        <>
          <div className="mb-6 flex flex-wrap gap-3">
            <Link href="/settings/security" className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">安全设置</Link>
            <Link href="/settings/admins" className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">超管</Link>
          </div>
          <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-600 shadow-sm">
            {data.editable ? "环境变量只读；下方可编辑 DB 站点配置。" : zh.settings.readonlyHint(data.app_name, data.version)}
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
                  <Globe className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-900">{zh.settings.sections.site.title}</h2>
                  <p className="text-sm text-gray-500">{zh.settings.sections.site.desc}</p>
                </div>
              </div>
              <dl className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-gray-500">{zh.settings.fields.appName}</dt>
                  <dd className="font-semibold text-gray-900">{data.app_name}</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-gray-500">{zh.settings.fields.version}</dt>
                  <dd className="font-semibold text-gray-900">v{data.version}</dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-gray-500">{zh.settings.fields.publicSite}</dt>
                  <dd>
                    <BoolBadge enabled={data.public_site_enabled} onLabel={zh.settings.enabled} offLabel={zh.settings.disabled} />
                  </dd>
                </div>
              </dl>
            </section>

            <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-100 text-cyan-700">
                  <Shield className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-900">{zh.settings.sections.geo.title}</h2>
                  <p className="text-sm text-gray-500">{zh.settings.sections.geo.desc}</p>
                </div>
              </div>
              <dl className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-gray-500">{zh.settings.fields.geoEval}</dt>
                  <dd>
                    <BoolBadge enabled={data.geo_eval_enabled} onLabel={zh.settings.enabled} offLabel={zh.settings.disabled} />
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-gray-500">{zh.settings.fields.wikiGate}</dt>
                  <dd>
                    <BoolBadge enabled={data.geo_eval_wiki_gate_enabled} onLabel={zh.settings.enabled} offLabel={zh.settings.disabled} />
                  </dd>
                </div>
              </dl>
            </section>

            <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100 text-violet-700">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-900">{zh.settings.sections.runtime.title}</h2>
                  <p className="text-sm text-gray-500">{zh.settings.sections.runtime.desc}</p>
                </div>
              </div>
              <dl className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-gray-500">{zh.settings.fields.techBrandMode}</dt>
                  <dd>
                    <BoolBadge enabled={data.tech_brand_mode} onLabel={zh.settings.enabled} offLabel={zh.settings.disabled} />
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-gray-500">{zh.settings.fields.aiMock}</dt>
                  <dd>
                    <BoolBadge enabled={data.ai_mock_mode} onLabel={zh.settings.enabled} offLabel={zh.settings.disabled} />
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-gray-500">{zh.settings.fields.gwebSync}</dt>
                  <dd>
                    <BoolBadge enabled={data.gweb_sync_enabled} onLabel={zh.settings.enabled} offLabel={zh.settings.disabled} />
                  </dd>
                </div>
              </dl>
            </section>

            <section className="rounded-lg border border-dashed border-gray-200 bg-gray-50 p-5">
              <div className="flex items-start gap-3">
                <Zap className="mt-0.5 h-5 w-5 text-amber-600" />
                <div>
                  <h2 className="text-base font-semibold text-gray-900">{zh.settings.sections.coming.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-gray-600">{zh.settings.sections.coming.desc}</p>
                </div>
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
