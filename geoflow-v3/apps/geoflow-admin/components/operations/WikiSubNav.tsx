"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";

const items = [
  { href: "/operations/wiki", label: zh.wiki.navList, match: "list" as const },
  { href: "/operations/wiki/packs", label: zh.wiki.navPacks, match: "packs" as const },
  { href: "/operations/wiki/reconcile", label: zh.wiki.navReconcile, match: "reconcile" as const },
];

function activeMatch(pathname: string, match: "list" | "packs" | "reconcile"): boolean {
  if (match === "packs") return pathname.startsWith("/operations/wiki/packs");
  if (match === "reconcile") return pathname.startsWith("/operations/wiki/reconcile");
  return (
    pathname === "/operations/wiki" ||
    pathname.startsWith("/operations/wiki/new") ||
    /^\/operations\/wiki\/\d+/.test(pathname)
  );
}

export function WikiSubNav() {
  const pathname = usePathname();
  return (
    <div className="mb-4 flex flex-wrap gap-2">
      {items.map((item) => {
        const active = activeMatch(pathname, item.match);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm font-medium",
              active ? "bg-blue-600 text-white" : "bg-white text-gray-700 ring-1 ring-gray-200 hover:bg-gray-50",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}
