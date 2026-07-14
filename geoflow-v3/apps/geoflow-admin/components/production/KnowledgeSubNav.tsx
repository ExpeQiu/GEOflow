"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { KNOWLEDGE_SUB_NAV } from "@/lib/nav-config";

function isSubActive(pathname: string, key: string, href: string): boolean {
  if (key === "bases") {
    return (
      pathname === "/production/knowledge" ||
      pathname === "/production/knowledge/new" ||
      /^\/production\/knowledge\/[^/]+$/.test(pathname) ||
      pathname.startsWith("/production/url-import")
    );
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function KnowledgeSubNav() {
  const pathname = usePathname();

  return (
    <nav className="mb-6 flex flex-wrap gap-2">
      {KNOWLEDGE_SUB_NAV.map((item) => {
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
