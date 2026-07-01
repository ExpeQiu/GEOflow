import { cn } from "@/lib/cn";

export function PlaceholderPanel({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="rounded-lg bg-white p-8 shadow-sm ring-1 ring-gray-200">
      <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-gray-500">{hint ?? "功能对接中，API 将在 Phase 2 补齐。"}</p>
    </div>
  );
}

export function DataTable({
  headers,
  rows,
  emptyText = "暂无数据",
}: {
  headers: string[];
  rows: React.ReactNode[][];
  emptyText?: string;
}) {
  if (rows.length === 0) {
    return (
      <div className="rounded-lg bg-white p-8 text-center text-sm text-gray-500 shadow-sm ring-1 ring-gray-200">
        {emptyText}
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-left">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-4 py-3 font-medium text-gray-600">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((cells, i) => (
            <tr key={i} className="border-t border-gray-100">
              {cells.map((cell, j) => (
                <td key={j} className={cn("px-4 py-3 text-gray-800")}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
