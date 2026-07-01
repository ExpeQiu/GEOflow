"use client";

import { useEffect, useState } from "react";
import { apiGet, getToken } from "@/lib/api-client";
import { useRouter } from "next/navigation";

type DashboardData = { tasks_count: number; tech_ip_assets_count: number; version: string };

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    apiGet<DashboardData>("/api/admin/dashboard", token).then(setData).catch(() => router.push("/login"));
  }, [router]);

  return (
    <div>
      <h1 className="text-lg font-bold mb-4">Dashboard</h1>
      <div className="grid grid-cols-3 gap-4">
        <Card title="任务数" value={data?.tasks_count ?? "—"} />
        <Card title="技术 IP 资产" value={data?.tech_ip_assets_count ?? "—"} />
        <Card title="版本" value={data?.version ?? "3.0.0"} />
      </div>
    </div>
  );
}

function Card({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <p className="text-sm text-[var(--muted)]">{title}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  );
}
