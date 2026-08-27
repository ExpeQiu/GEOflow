"use client";

import type { ReactNode } from "react";
import { zh } from "@/lib/i18n/zh";

export type SecurityRuntime = {
  debug?: boolean;
  allow_insecure_jwt?: boolean;
  jwt_secret_strong?: boolean;
  jwt_expire_hours?: number;
  api_token_default_ttl_days?: number;
  cors_allowed_origins?: string[];
  callback_secret_configured?: boolean;
  login_max_failures?: number;
  login_lockout_seconds?: number;
  http_only_cookie?: boolean;
  admin_cookie_name?: string;
  uploads_auth_required?: boolean;
  ws_auth_required?: boolean;
  llm_gateway_mode?: string;
  enterprise_text_base?: string;
  enterprise_key_configured?: boolean;
  lobster_proxy_base?: string;
  lobster_token_configured?: boolean;
  api_key_encryption_separate?: boolean;
  production_ready?: boolean;
  env_hints?: Record<string, string>;
};

function StatusDot({ ok, warn }: { ok: boolean; warn?: boolean }) {
  const color = ok ? "bg-emerald-500" : warn ? "bg-amber-500" : "bg-red-500";
  return <span className={`inline-block h-2 w-2 shrink-0 rounded-full ${color}`} aria-hidden />;
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-gray-50 py-2 last:border-0">
      <dt className="text-gray-500">{label}</dt>
      <dd className="max-w-[60%] text-right font-medium text-gray-900">{children}</dd>
    </div>
  );
}

type Props = {
  runtime: SecurityRuntime | null | undefined;
  /** site | security | tokens — 控制展示侧重点 */
  variant?: "site" | "security" | "tokens";
};

export function SecurityRuntimePanel({ runtime, variant = "site" }: Props) {
  if (!runtime) return null;
  const t = zh.settings.runtime;
  const ready = Boolean(runtime.production_ready);

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-gray-900">{t.title}</h2>
          <p className="text-sm text-gray-500">{t.desc}</p>
        </div>
        <span
          className={
            ready
              ? "rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800"
              : "rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800"
          }
        >
          {ready ? t.prodReady : t.prodNotReady}
        </span>
      </div>
      {!ready && <p className="mb-3 text-xs text-amber-700">{t.prodHint}</p>}

      <dl className="text-sm">
        {(variant === "site" || variant === "security") && (
          <>
            <Row label={t.cors}>
              <span className="break-all font-mono text-xs">
                {(runtime.cors_allowed_origins || []).join(", ") || "—"}
              </span>
            </Row>
            <Row label={t.llmGateway}>
              <span className="inline-flex items-center gap-1.5">
                <StatusDot
                  ok={
                    runtime.llm_gateway_mode === "enterprise-gateway" ||
                    runtime.llm_gateway_mode === "geely"
                      ? Boolean(runtime.enterprise_key_configured)
                      : runtime.llm_gateway_mode === "lobster"
                        ? Boolean(runtime.lobster_token_configured)
                        : true
                  }
                  warn
                />
                {runtime.llm_gateway_mode || "auto"}
                {runtime.enterprise_key_configured
                  ? ` · ${t.enterpriseOk}`
                  : runtime.lobster_token_configured
                    ? ` · ${t.lobsterOk}`
                    : ` · ${t.enterpriseMissing}`}
              </span>
            </Row>
            {variant === "site" && runtime.enterprise_text_base ? (
              <Row label={t.enterpriseBase}>
                <span className="font-mono text-xs">{runtime.enterprise_text_base}</span>
              </Row>
            ) : null}
            {variant === "site" && runtime.lobster_proxy_base ? (
              <Row label={t.lobsterBase}>
                <span className="font-mono text-xs">{runtime.lobster_proxy_base}</span>
              </Row>
            ) : null}
          </>
        )}

        {(variant === "security" || variant === "site") && (
          <>
            <Row label={t.jwtStrong}>
              <span className="inline-flex items-center gap-1.5">
                <StatusDot ok={Boolean(runtime.jwt_secret_strong)} />
                {runtime.jwt_secret_strong ? t.ok : t.weak}
                {runtime.allow_insecure_jwt ? ` · ${t.allowInsecure}` : ""}
              </span>
            </Row>
            <Row label={t.callback}>
              <span className="inline-flex items-center gap-1.5">
                <StatusDot ok={Boolean(runtime.callback_secret_configured)} />
                {runtime.callback_secret_configured ? t.configured : t.defaultSecret}
              </span>
            </Row>
            <Row label={t.lockout}>
              {t.lockoutValue(runtime.login_max_failures ?? 5, runtime.login_lockout_seconds ?? 900)}
            </Row>
            <Row label={t.cookie}>
              <span className="inline-flex items-center gap-1.5">
                <StatusDot ok={Boolean(runtime.http_only_cookie)} />
                HttpOnly · {runtime.admin_cookie_name || "gf_token"} · {runtime.jwt_expire_hours ?? 24}h
              </span>
            </Row>
            <Row label={t.uploadsWs}>
              <span className="inline-flex items-center gap-1.5">
                <StatusDot ok={Boolean(runtime.uploads_auth_required && runtime.ws_auth_required)} />
                {t.uploadsWsOk}
              </span>
            </Row>
          </>
        )}

        {variant === "tokens" && (
          <>
            <Row label={t.tokenTtl}>{t.days(runtime.api_token_default_ttl_days ?? 30)}</Row>
            <Row label={t.authHeader}>
              <code className="text-xs">Authorization: Bearer &lt;token&gt;</code>
            </Row>
            <Row label={t.apiBase}>
              <code className="text-xs">/api/v1</code>
            </Row>
            <Row label={t.cookieAlt}>
              <code className="text-xs">{runtime.admin_cookie_name || "gf_token"}</code>（Admin 浏览器会话）
            </Row>
          </>
        )}

        {variant === "security" && (
          <Row label={t.encKey}>
            <span className="inline-flex items-center gap-1.5">
              <StatusDot ok={Boolean(runtime.api_key_encryption_separate)} warn={!runtime.api_key_encryption_separate} />
              {runtime.api_key_encryption_separate ? t.encSeparate : t.encFallback}
            </span>
          </Row>
        )}
      </dl>

      {(variant === "security" || (!ready && variant === "site")) && (
        <p className="mt-3 border-t pt-3 text-xs text-gray-400">
          {t.envNote}{" "}
          <code className="text-[11px]">
            {[
              runtime.env_hints?.jwt_secret,
              runtime.env_hints?.callback_secret,
              runtime.env_hints?.cors,
              runtime.env_hints?.allow_insecure,
            ]
              .filter(Boolean)
              .join(" / ")}
          </code>
        </p>
      )}
    </section>
  );
}
