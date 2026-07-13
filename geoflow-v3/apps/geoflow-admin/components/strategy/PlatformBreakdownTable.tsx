import type { PlatformBreakdownRow } from "@/lib/strategy-types";
import { platformLabel } from "./shared/AivisPrimitives";

export function PlatformBreakdownTable({ rows }: { rows: PlatformBreakdownRow[] }) {
  if (!rows.length) {
    return <p className="text-sm text-gray-400">暂无分平台表现数据</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="bg-slate-50 text-left text-xs text-gray-500">
            <th className="px-3 py-2">平台</th>
            <th className="px-3 py-2">可见性</th>
            <th className="px-3 py-2">排名</th>
            <th className="px-3 py-2">领先者</th>
            <th className="px-3 py-2">领先可见性</th>
            <th className="px-3 py-2">差距</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const gap = Math.max(0, row.leader_visibility_pct - row.visibility_pct);
            return (
              <tr key={row.platform} className="border-t border-gray-100">
                <td className="px-3 py-2 font-medium">{row.label || platformLabel(row.platform)}</td>
                <td className="px-3 py-2">{row.visibility_pct}%</td>
                <td className="px-3 py-2">{row.rank_label || "—"}</td>
                <td className="px-3 py-2">{row.leader_brand || "—"}</td>
                <td className="px-3 py-2">{row.leader_visibility_pct ? `${row.leader_visibility_pct}%` : "—"}</td>
                <td className="px-3 py-2 text-amber-700">{gap ? `-${gap.toFixed(1)}pp` : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
