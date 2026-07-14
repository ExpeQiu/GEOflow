"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { AI_CONFIG_SUB_NAV } from "@/lib/nav-config";

function isSubActive(pathname: string, key: string, href: string): boolean {
  if (key === "orchestration") {
    return pathname === "/production/ai_config" || pathname.startsWith("/production/ai_config/");
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AiConfigSubNav() {
  const pathname = usePathname();

  return (
    <nav className="mb-6 flex flex-wrap gap-2">
      {AI_CONFIG_SUB_NAV.map((item) => {
        const active = isSubActive(pathname, item.key, item.href);
        return (
          <Link
            key={item.key}
            href={item.href}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              active ? "bg-emerald-100 text-emerald-800" : "text-gray-600 hover:bg-gray-50",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
