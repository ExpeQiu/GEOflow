"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { zh } from "@/lib/i18n/zh";

const ITEMS = [
  { key: "overview", label: zh.distribution.overviewTab, href: "/operations/distribution" },
  { key: "jobs", label: zh.distribution.jobsTab, href: "/operations/distribution/jobs" },
];

export function DistributionSubNav() {
  const pathname = usePathname();

  return (
    <nav className="mb-6 flex flex-wrap gap-2">
      {ITEMS.map((item) => {
        const active =
          item.key === "overview"
            ? pathname === item.href
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.key}
            href={item.href}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              active ? "bg-blue-100 text-blue-800" : "text-gray-600 hover:bg-gray-50",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
