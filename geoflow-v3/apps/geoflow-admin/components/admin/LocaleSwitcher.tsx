"use client";

import { ADMIN_LOCALES, LOCALE_LABELS, useI18n } from "@/lib/i18n";

export function LocaleSwitcher({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale } = useI18n();
  return (
    <label className={compact ? "inline-flex items-center gap-1 text-xs text-gray-500" : "block text-sm text-gray-600"}>
      {!compact && <span className="mb-1 block text-xs text-gray-400">语言 / Language（实验室）</span>}
      <select
        aria-label="Admin locale"
        value={locale}
        onChange={(e) => setLocale(e.target.value as (typeof ADMIN_LOCALES)[number])}
        className="rounded-md border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700"
      >
        {ADMIN_LOCALES.map((code) => (
          <option key={code} value={code}>
            {LOCALE_LABELS[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
