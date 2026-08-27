"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { HubHeader } from "@/components/admin/HubHeader";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { SecurityRuntimePanel, type SecurityRuntime } from "@/components/admin/SecurityRuntimePanel";
import { SettingsSubNav } from "@/components/admin/SettingsSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, apiPut, getToken } from "@/lib/api-client";
import type { SiteSettingsPayload } from "@/lib/dashboard-types";
import { zh } from "@/lib/i18n/zh";
import { Globe, Shield, Sparkles, Zap } from "lucide-react";

type DbSetting = { key: string; value: string; group: string; value_type?: string };
type ExtendedSiteSettings = SiteSettingsPayload & {
  editable?: boolean;
  db_settings?: DbSetting[];
  security_runtime?: SecurityRuntime;
  llm_gateway_mode?: string;
  lobster_token_configured?: boolean;
};

const GROUP_LABEL: Record<string, string> = {
  general: zh.settings.groups.general,
  security: zh.settings.groups.security,
  knowledge: zh.settings.groups.knowledge,
  monitor: zh.settings.groups.monitor,
  geo: zh.settings.groups.geo,
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
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const res = await apiGet<ExtendedSiteSettings>("/api/admin/settings/site", t);
    setData(res);
  }, []);

  useEffect(() => {
    load().catch(() => setError("无法加载站点设置"));
  }, [load]);

  const grouped = useMemo(() => {
    const map = new Map<string, DbSetting[]>();
    for (const s of data?.db_settings ?? []) {
      if (s.key === "sensitive_words") continue;
      const list = map.get(s.group) ?? [];
      list.push(s);
      map.set(s.group, list);
    }
    return Array.from(map.entries());
  }, [data]);

  async function saveSetting(e: FormEvent, key: string, value: string, group: string) {
    e.preventDefault();
    const t = getToken();
    if (!t) return;
    setError("");
    setSaving(true);
    try {
      await apiPut("/api/admin/settings/site", t, { setting_key: key, setting_value: value, group_name: group });
      setFlash("已保存");
      await load();
    } catch {
      setError("保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function addSetting(e: FormEvent) {
    e.preventDefault();
    if (!newKey.trim()) return;
    const t = getToken();
    if (!t) return;
    setError("");
    setSaving(true);
    try {
      await apiPut("/api/admin/settings/site", t, {
        setting_key: newKey.trim(),
        setting_value: newValue,
        group_name: newGroup,
      });
      setNewKey("");
      setNewValue("");
      setFlash("已添加配置项");
      await load();
    } catch {
      setError("添加失败");
    } finally {
      setSaving(false);
    }
  }

  async function copyUrl(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      setFlash("已复制 GEOweb 地址");
    } catch {
      setError("复制失败");
    }
  }

  return (
    <div>
      <HubHeader title={zh.settings.title} subtitle={zh.settings.subtitle} />
      <SettingsSubNav />
      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {flash && <FlashAlert variant="success">{flash}</FlashAlert>}
      {!data && !error && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {data && (
        <>
          <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-600 shadow-sm">
            {data.editable ? zh.settings.editableHint : zh.settings.readonlyHint(data.app_name, data.version)}
            <span className="ml-2 text-xs text-gray-400">{zh.settings.envReadonly}</span>
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
                <div className="flex items-center justify-between gap-4">
                  <dt className="text-gray-500">{zh.settings.fields.hardGate}</dt>
                  <dd>
                    <BoolBadge enabled={Boolean(data.geo_eval_hard_gate)} onLabel={zh.settings.enabled} offLabel={zh.settings.disabled} />
                  </dd>
                </div>
              </dl>
            </section>

            <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm lg:col-span-2">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-100 text-violet-700">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-gray-900">{zh.settings.sections.runtime.title}</h2>
                  <p className="text-sm text-gray-500">{zh.settings.sections.runtime.desc}</p>
                </div>
              </div>
              <dl className="grid gap-3 text-sm sm:grid-cols-3">
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
                  <dd className="flex items-center gap-2">
                    <BoolBadge
                      enabled={Boolean(data.geoweb_sync_enabled ?? data.gweb_sync_enabled)}
                      onLabel={zh.settings.enabled}
                      offLabel={zh.settings.disabled}
                    />
                    {data.geoweb_base_url ? (
                      <button type="button" onClick={() => copyUrl(data.geoweb_base_url!)} className="text-xs text-blue-600 hover:underline">
                        {data.geoweb_base_url}
                      </button>
                    ) : null}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-4 sm:col-span-3">
                  <dt className="text-gray-500">{zh.settings.fields.llmGateway}</dt>
                  <dd className="font-mono text-xs text-gray-800">
                    {data.llm_gateway_mode || data.security_runtime?.llm_gateway_mode || "auto"}
                    {data.lobster_token_configured || data.security_runtime?.lobster_token_configured
                      ? " · Token ✓"
                      : " · Token —"}
                  </dd>
                </div>
              </dl>
            </section>

            <div className="lg:col-span-2">
              <SecurityRuntimePanel runtime={data.security_runtime} variant="site" />
            </div>

            <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm lg:col-span-2">
              <div className="mb-4 flex items-center gap-3">
                <Zap className="h-5 w-5 text-amber-600" />
                <h2 className="text-base font-semibold text-gray-900">{zh.settings.sections.dbSettings.title}</h2>
              </div>
              {!data.editable ? (
                <p className="text-sm text-gray-500">{zh.settings.sections.dbSettings.notMigrated}</p>
              ) : (
                <>
                  {grouped.length === 0 ? (
                    <p className="text-sm text-gray-500">暂无 DB 配置项，可在下方添加。</p>
                  ) : (
                    <div className="space-y-6">
                      {grouped.map(([group, items]) => (
                        <div key={group}>
                          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
                            {GROUP_LABEL[group] || group}
                          </h3>
                          <div className="space-y-3">
                            {items.map((s) => (
                              <form
                                key={s.key}
                                onSubmit={(e) =>
                                  saveSetting(e, s.key, (e.currentTarget.elements.namedItem("val") as HTMLInputElement).value, s.group)
                                }
                                className="flex flex-wrap items-center gap-2 rounded-md border border-gray-100 bg-gray-50 p-3"
                              >
                                <span className="min-w-[140px] font-mono text-xs font-medium text-gray-600">{s.key}</span>
                                <input name="val" defaultValue={s.value} className="min-w-[160px] flex-1 rounded-md border px-2 py-1 text-sm" />
                                <button type="submit" disabled={saving} className="rounded-md bg-gray-900 px-3 py-1 text-xs text-white disabled:opacity-50">
                                  {zh.common.save}
                                </button>
                              </form>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  <form onSubmit={addSetting} className="mt-4 flex flex-wrap gap-2 border-t pt-4">
                    <input placeholder="key" value={newKey} onChange={(e) => setNewKey(e.target.value)} className="rounded-md border px-2 py-1 text-sm" />
                    <input placeholder="value" value={newValue} onChange={(e) => setNewValue(e.target.value)} className="flex-1 rounded-md border px-2 py-1 text-sm" />
                    <input placeholder="group" value={newGroup} onChange={(e) => setNewGroup(e.target.value)} className="w-24 rounded-md border px-2 py-1 text-sm" />
                    <button type="submit" disabled={saving} className="rounded-md bg-emerald-600 px-3 py-1 text-sm text-white disabled:opacity-50">
                      添加
                    </button>
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
