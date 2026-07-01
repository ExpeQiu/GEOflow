import { zh } from "@/lib/i18n/zh";
import type { WebSource } from "@/lib/strategy-types";

export function WebIntelPanel({
  sources,
  reports,
}: {
  sources: WebSource[];
  reports: { id: number; title: string; status: string; created_at: string | null }[];
}) {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">{zh.strategy.webIntel.sourcesTitle}</h2>
        {sources.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">{zh.strategy.webIntel.emptySources}</p>
        ) : (
          <ul className="mt-4 divide-y divide-gray-100">
            {sources.map((s) => (
              <li key={s.id} className="py-3 text-sm">
                <p className="font-medium text-gray-900 break-all">{s.url}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {s.label} · {s.fetch_status}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">{zh.strategy.webIntel.reportsTitle}</h2>
        {reports.length === 0 ? (
          <p className="mt-4 text-sm text-gray-500">{zh.strategy.webIntel.emptyReports}</p>
        ) : (
          <ul className="mt-4 divide-y divide-gray-100">
            {reports.map((r) => (
              <li key={r.id} className="py-3 text-sm">
                <p className="font-medium text-gray-900">{r.title || `#${r.id}`}</p>
                <p className="mt-1 text-xs text-gray-500">{r.status}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
