"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { SETTINGS_SUB_NAV } from "@/lib/nav-config";
import { useI18n } from "@/lib/i18n";

const LABEL_KEY: Record<string, "site" | "security" | "tokens" | "admins"> = {
  site: "site",
  security: "security",
  tokens: "tokens",
  admins: "admins",
};

export function SettingsSubNav() {
  const pathname = usePathname();
  const { messages: zh } = useI18n();

  return (
    <nav className="mb-6 flex flex-wrap gap-2">
      {SETTINGS_SUB_NAV.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        const key = LABEL_KEY[item.key];
        return (
          <Link
            key={item.key}
            href={item.href}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              active ? "bg-slate-900 text-white" : "text-gray-600 hover:bg-gray-100",
            )}
          >
            {key ? zh.settings.tabs[key] : item.label}
          </Link>
        );
      })}
    </nav>
  );
}
