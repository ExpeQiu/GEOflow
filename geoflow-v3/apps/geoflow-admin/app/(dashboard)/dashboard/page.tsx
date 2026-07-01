"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, RefreshCw } from "lucide-react";
import { DashboardAutomation, DashboardNavigationLanes } from "@/components/admin/DashboardAutomation";
import { DashboardHealthCards, QuickStartPanel } from "@/components/admin/DashboardSections";
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
            href="/operations/tasks/new"
            className="inline-flex h-10 items-center rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
          >
            <Plus className="mr-2 h-4 w-4" />
            {zh.dashboard.newTask}
          </Link>
        </div>
      </div>

      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {loading && !data && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      {!welcomeDismissed && (
        <div className="mb-6 flex items-start justify-between gap-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <p className="text-sm text-blue-900">欢迎使用 GEOFlow v3 管理后台。Phase 6–11 迁移 API 与页面已就绪，请先执行 Alembic 002 迁移以启用素材三库与站点设置。</p>
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

      {data && (
        <>
          <DashboardHealthCards stats={data.stats} />
          <QuickStartPanel />
          <DashboardAutomation automation={data.automation} />
          <DashboardNavigationLanes lanes={data.automation.lanes} />
        </>
      )}
    </div>
  );
}
