"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, RefreshCw } from "lucide-react";
import { DashboardNavigationLanes } from "@/components/admin/DashboardAutomation";
import { DashboardHealthCards } from "@/components/admin/DashboardSections";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { LayerCards } from "@/components/admin/LayerCards";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiGet, getToken } from "@/lib/api-client";
import type { DashboardPayload } from "@/lib/dashboard-types";
import { zh } from "@/lib/i18n/zh";

export default function DashboardPage() {
  const router = useRouter();
  const token = useAuthGuard();
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [welcomeDismissed, setWelcomeDismissed] = useState(true);

  useEffect(() => {
    setWelcomeDismissed(localStorage.getItem("gf_welcome_dismissed") === "1");
  }, []);

  const load = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    setLoading(true);
    setError("");
    try {
      const payload = await apiGet<DashboardPayload>("/api/admin/dashboard", t);
      setData(payload);
    } catch {
      setError("无法加载仪表盘数据");
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  return (
    <div>
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{zh.dashboard.heading}</h1>
          <p className="mt-1 text-sm leading-6 text-gray-600">
            {zh.dashboard.subtitle(data?.site_name ?? zh.brand)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={load}
            className="inline-flex h-10 items-center rounded-lg border border-gray-300 bg-white px-4 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {zh.dashboard.refresh}
          </button>
          <Link
            href="/production/themes"
            className="inline-flex h-10 items-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            <Plus className="mr-2 h-4 w-4" />
            主题包确认
          </Link>
        </div>
      </div>

      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {loading && !data && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {!welcomeDismissed && (
        <div className="mb-6 flex items-start justify-between gap-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <p className="text-sm text-blue-900">欢迎使用 GEOFlow v3 管理后台。前后端闭环升级已完成，请确保已执行 alembic upgrade head（含 002/003 迁移）。</p>
          <button
            type="button"
            className="shrink-0 text-sm font-medium text-blue-700 hover:text-blue-900"
            onClick={() => {
              localStorage.setItem("gf_welcome_dismissed", "1");
              setWelcomeDismissed(true);
            }}
          >
            知道了
          </button>
        </div>
      )}

      <LayerCards />

      {data?.theme_funnel && (
        <div className="mb-8 rounded-lg border border-violet-100 bg-white p-5 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-gray-900">Theme 主题漏斗</h2>
              <p className="mt-1 text-sm text-gray-600">草稿 → 生产 → 门禁 → 发布 → 测量（主叙事）</p>
            </div>
            <Link href="/production/themes" className="text-sm font-medium text-violet-700 hover:underline">
              管理主题包 →
            </Link>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              { label: "草稿", value: data.theme_funnel.draft },
              { label: "生产中", value: data.theme_funnel.producing },
              { label: "已发布", value: data.theme_funnel.published },
              { label: "测量中", value: data.theme_funnel.measuring },
            ].map((c) => (
              <div key={c.label} className="rounded-lg bg-violet-50 px-3 py-3 text-center">
                <div className="text-2xl font-semibold text-violet-900">{c.value}</div>
                <div className="text-xs text-violet-700">{c.label}</div>
              </div>
            ))}
          </div>
          {(data.theme_funnel.blockers || []).length > 0 && (
            <ul className="mt-3 space-y-1 text-sm text-amber-800">
              {data.theme_funnel.blockers.map((b) => (
                <li key={b.code}>
                  阻塞：{b.code}
                  {b.hint ? (
                    <>
                      {" · "}
                      <Link href={b.hint} className="underline">
                        去处理
                      </Link>
                    </>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="mb-8 rounded-lg border border-blue-100 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-900">运营数据</h2>
        <p className="mt-1 text-sm text-gray-600">文章产量、访问、任务队列与可见性趋势已迁至「运营与分发」。</p>
        <Link href="/operations/analytics" className="mt-3 inline-block text-sm font-medium text-blue-700 hover:underline">
          打开运营数据 →
        </Link>
      </div>

      {data && (
        <>
          <DashboardHealthCards stats={data.stats} />
          <DashboardNavigationLanes lanes={data.automation.lanes} />
        </>
      )}
    </div>
  );
}
