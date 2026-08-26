"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, getToken } from "@/lib/api-client";
import { LayerSection } from "./shared/AivisPrimitives";

type CrossItem = {
  question_id: number;
  question_text: string;
  scene_id?: number | null;
  flags: string[];
  unused_dims?: string[];
  ours_cited?: boolean;
  mentioned?: boolean;
  tracks_present?: string[];
  source_hints?: Array<{ domain?: string; owner?: string; url?: string }>;
};

type CrossPayload = {
  items: CrossItem[];
  summary: {
    mention_no_ours: number;
    framework_not_in_answer: number;
    ours_cited: number;
    gold: number;
  };
};

const FLAG_LABEL: Record<string, string> = {
  mention_no_ours: "信源缺口",
  framework_not_in_answer: "内容形态缺口",
  ours_cited: "我方已引用",
  gold: "金标 A∩B∩C",
};

const ACTIONABLE = new Set(["mention_no_ours", "framework_not_in_answer"]);

export function CrossTrackPanel() {
  const [data, setData] = useState<CrossPayload | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [spawned, setSpawned] = useState<Record<number, number>>({});
  const [error, setError] = useState("");

  useEffect(() => {
    const t = getToken();
    if (!t) return;
    apiGet<CrossPayload>("/api/admin/strategy/cross-track", t)
      .then(setData)
      .catch(() => setData({ items: [], summary: { mention_no_ours: 0, framework_not_in_answer: 0, ours_cited: 0, gold: 0 } }));
  }, []);

  async function spawnTheme(it: CrossItem) {
    const t = getToken();
    if (!t) return;
    setBusyId(it.question_id);
    setError("");
    try {
      const res = await apiPost<{ theme?: { id: number } }>(
        "/api/admin/strategy/cross-track/spawn-theme",
        t,
        { question_id: it.question_id, flags: it.flags || [], unused_dims: it.unused_dims || [] },
      );
      const themeId = res.theme?.id;
      if (themeId) setSpawned((prev) => ({ ...prev, [it.question_id]: themeId }));
    } catch (err) {
      setError((err as Error).message || "生成 Theme 失败");
    } finally {
      setBusyId(null);
    }
  }

  if (!data) return null;
  const s = data.summary;

  return (
    <LayerSection title="交叉判定" subtitle="A∩C / B∩C，不计入 visibility_open_api；信源/形态缺口可生成 Theme 草稿">
      <div className="mb-3 flex flex-wrap gap-2 text-xs">
        <span className="rounded bg-rose-50 px-2 py-1 text-rose-800">信源缺口 {s.mention_no_ours}</span>
        <span className="rounded bg-amber-50 px-2 py-1 text-amber-800">形态缺口 {s.framework_not_in_answer}</span>
        <span className="rounded bg-emerald-50 px-2 py-1 text-emerald-800">我方引用 {s.ours_cited}</span>
        <span className="rounded bg-violet-50 px-2 py-1 text-violet-800">金标 {s.gold}</span>
      </div>
      {error ? <p className="mb-2 text-xs text-rose-600">{error}</p> : null}
      {data.items.length === 0 ? (
        <p className="text-sm text-gray-400">暂无交叉样本。先跑框架轨与引用轨扫描。</p>
      ) : (
        <ul className="space-y-2">
          {data.items.slice(0, 12).map((it) => {
            const canSpawn = (it.flags || []).some((f) => ACTIONABLE.has(f));
            const themeId = spawned[it.question_id];
            return (
              <li key={it.question_id} className="rounded-md border border-gray-100 px-3 py-2 text-xs">
                <p className="line-clamp-1 text-gray-800">{it.question_text}</p>
                {(it.unused_dims || []).length > 0 ? (
                  <p className="mt-0.5 line-clamp-2 text-[11px] text-gray-500">
                    A 轨未用维度：{(it.unused_dims || []).slice(0, 3).join(" · ")}
                  </p>
                ) : null}
                <div className="mt-1 flex flex-wrap items-center gap-1">
                  {(it.tracks_present || []).map((t) => (
                    <span key={t} className="rounded bg-slate-50 px-1.5 py-0.5 text-slate-600">
                      {t}
                    </span>
                  ))}
                  {(it.flags || []).map((f) => (
                    <span
                      key={f}
                      className={`rounded px-1.5 py-0.5 ${
                        f === "gold" || f === "ours_cited"
                          ? "bg-emerald-50 text-emerald-800"
                          : "bg-rose-50 text-rose-800"
                      }`}
                    >
                      {FLAG_LABEL[f] || f}
                    </span>
                  ))}
                  {canSpawn ? (
                    themeId ? (
                      <a
                        href={`/production/themes?id=${themeId}`}
                        className="ml-auto rounded bg-violet-50 px-1.5 py-0.5 text-violet-800"
                      >
                        Theme #{themeId}
                      </a>
                    ) : (
                      <button
                        type="button"
                        disabled={busyId === it.question_id}
                        onClick={() => spawnTheme(it)}
                        className="ml-auto rounded border border-violet-200 px-1.5 py-0.5 text-violet-700 disabled:opacity-50"
                      >
                        {busyId === it.question_id ? "生成中…" : "生成 Theme 草稿"}
                      </button>
                    )
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </LayerSection>
  );
}
