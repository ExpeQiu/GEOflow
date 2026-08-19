"use client";

import { useMemo, useState } from "react";
import { Plus, X } from "lucide-react";
import { zh } from "@/lib/i18n/zh";
import type { WikiRelatedOption } from "@/lib/wiki-form-types";

const inputClass =
  "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

export function WikiRelatedPicker({
  value,
  options,
  onChange,
}: {
  value: string[];
  options: WikiRelatedOption[];
  onChange: (next: string[]) => void;
}) {
  const [query, setQuery] = useState("");
  const [custom, setCustom] = useState("");
  const selected = new Set(value);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return options
      .filter((item) => !selected.has(item.path))
      .filter((item) => {
        if (!needle) return true;
        return (
          item.path.toLowerCase().includes(needle) ||
          item.title.toLowerCase().includes(needle) ||
          item.slug.toLowerCase().includes(needle)
        );
      })
      .slice(0, 8);
  }, [options, query, selected]);

  function add(path: string) {
    const cleaned = path.trim().replace(/^\/+/, "");
    if (!cleaned || selected.has(cleaned)) return;
    onChange([...value, cleaned]);
    setQuery("");
    setCustom("");
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {value.map((path) => (
          <span
            key={path}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 font-mono text-xs text-slate-700"
          >
            {path}
            <button type="button" onClick={() => onChange(value.filter((item) => item !== path))} className="text-slate-400 hover:text-red-600">
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
      </div>
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={zh.wiki.relatedSearch}
        className={inputClass}
      />
      {filtered.length > 0 && (
        <ul className="max-h-48 overflow-auto rounded-md border border-gray-200 bg-white">
          {filtered.map((item) => (
            <li key={item.path}>
              <button
                type="button"
                onClick={() => add(item.path)}
                className="flex w-full items-start justify-between gap-3 px-3 py-2 text-left hover:bg-slate-50"
              >
                <span>
                  <span className="block text-sm text-gray-900">{item.title}</span>
                  <span className="font-mono text-xs text-gray-500">{item.path}</span>
                </span>
                <span className="text-xs text-gray-400">{item.type}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <input
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          placeholder={zh.wiki.relatedCustomPlaceholder}
          className={inputClass + " mt-0 font-mono"}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              add(custom);
            }
          }}
        />
        <button
          type="button"
          onClick={() => add(custom)}
          className="mt-0 inline-flex shrink-0 items-center rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
        >
          <Plus className="mr-1 h-4 w-4" />
          {zh.wiki.relatedAddCustom}
        </button>
      </div>
    </div>
  );
}
