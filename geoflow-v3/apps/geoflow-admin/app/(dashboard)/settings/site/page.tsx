"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import type { SiteSettingsPayload } from "@/lib/dashboard-types";
import { zh } from "@/lib/i18n/zh";
import { Globe, Shield, Sparkles, Zap } from "lucide-react";

type DbSetting = { key: string; value: string; group: string; value_type?: string };
type ExtendedSiteSettings = SiteSettingsPayload & {
  editable?: boolean;
  db_settings?: DbSetting[];
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
  const [flash, setFlash] = useState("");
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newGroup, setNewGroup] = useState("general");

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const res = await apiGet<ExtendedSiteSettings>("/api/admin/settings/site", t);
    setData(res);
  }, []);

  useEffect(() => {
    load().catch(() => setError("无法加载站点设置"));
  }, [load]);

  async function saveSetting(e: FormEvent, key: string, value: string, group: string) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    try {
      await fetch("/api/admin/settings/site", {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
        body: JSON.stringify({ setting_key: key, setting_value: value, group_name: group }),
      });
      setFlash("已保存");
      await load();
    } catch {
      setError("保存失败");
    }
  }

  async function addSetting(e: FormEvent) {
    e.preventDefault();
    if (!newKey.trim()) return;
    const t = getToken();
    if (!t) return;
    await fetch("/api/admin/settings/site", {
      method: "PUT",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
      body: JSON.stringify({ setting_key: newKey.trim(), setting_value: newValue, group_name: newGroup }),
    });
    setNewKey("");
    setNewValue("");
    setFlash("已添加配置项");
    await load();
  }

  return (
    <div>
      <HubHeader title={zh.settings.title} subtitle={zh.settings.subtitle} />
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {!data && !error && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {data && (
        <>
          <div className="mb-6 flex flex-wrap gap-3">
            <Link href="/settings/security" className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">安全设置</Link>
            <Link href="/settings/admins" className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">超管</Link>
            <Link href="/settings/api-tokens" className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">API Token</Link>
          </div>
          <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-600 shadow-sm">
            {data.editable ? zh.settings.editableHint : zh.settings.readonlyHint(data.app_name, data.version)}
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

            <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm lg:col-span-2">
              <div className="mb-4 flex items-center gap-3">
                <Zap className="h-5 w-5 text-amber-600" />
                <h2 className="text-base font-semibold text-gray-900">{zh.settings.sections.dbSettings.title}</h2>
              </div>
              {!data.editable ? (
                <p className="text-sm text-gray-500">{zh.settings.sections.dbSettings.notMigrated}</p>
              ) : (
                <>
                  <div className="space-y-3">
                    {(data.db_settings ?? []).map((s) => (
                      <form
                        key={s.key}
                        onSubmit={(e) => saveSetting(e, s.key, (e.currentTarget.elements.namedItem("val") as HTMLInputElement).value, s.group)}
                        className="flex flex-wrap items-center gap-2 rounded-md border border-gray-100 bg-gray-50 p-3"
                      >
                        <span className="min-w-[120px] text-xs font-medium text-gray-500">{s.group}/{s.key}</span>
                        <input name="val" defaultValue={s.value} className="flex-1 rounded-md border px-2 py-1 text-sm" />
                        <button type="submit" className="rounded-md bg-gray-900 px-3 py-1 text-xs text-white">保存</button>
                      </form>
                    ))}
                  </div>
                  <form onSubmit={addSetting} className="mt-4 flex flex-wrap gap-2 border-t pt-4">
                    <input placeholder="key" value={newKey} onChange={(e) => setNewKey(e.target.value)} className="rounded-md border px-2 py-1 text-sm" />
                    <input placeholder="value" value={newValue} onChange={(e) => setNewValue(e.target.value)} className="flex-1 rounded-md border px-2 py-1 text-sm" />
                    <input placeholder="group" value={newGroup} onChange={(e) => setNewGroup(e.target.value)} className="w-24 rounded-md border px-2 py-1 text-sm" />
                    <button type="submit" className="rounded-md bg-emerald-600 px-3 py-1 text-sm text-white">添加</button>
                  </form>
                </>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
