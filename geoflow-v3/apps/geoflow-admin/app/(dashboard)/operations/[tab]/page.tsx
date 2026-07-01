"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiGet, apiPost, getToken } from "@/lib/api-client";

type Task = { id: number; name: string; status: string; created_count: number };

export default function OperationsPage() {
  const { tab } = useParams<{ tab: string }>();
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    if (tab === "tasks") {
      apiGet<{ tasks: Task[] }>("/api/admin/tasks/overview", token).then((d) => setTasks(d.tasks));
    }
  }, [tab, router]);

  async function enqueue(taskId: number) {
    const token = getToken();
    if (!token) return;
    await apiPost("/api/admin/tasks/enqueue", token, { task_id: taskId });
    alert(`任务 ${taskId} 已入队`);
  }

  return (
    <div>
      <h1 className="text-lg font-bold mb-4">Operations · {tab}</h1>
      {tab === "tasks" && (
        <div className="bg-white border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="p-3">ID</th>
                <th className="p-3">名称</th>
                <th className="p-3">状态</th>
                <th className="p-3">已生成</th>
                <th className="p-3">操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} className="border-t">
                  <td className="p-3">{t.id}</td>
                  <td className="p-3">{t.name}</td>
                  <td className="p-3">{t.status}</td>
                  <td className="p-3">{t.created_count}</td>
                  <td className="p-3">
                    <button type="button" className="text-[var(--primary)]" onClick={() => enqueue(t.id)}>
                      入队
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {tab === "articles" && <p className="text-[var(--muted)]">文章列表 — 对接 /api/v1/articles</p>}
      {tab === "distribution" && <p className="text-[var(--muted)]">分发队列 — 对接 distribution API</p>}
    </div>
  );
}
