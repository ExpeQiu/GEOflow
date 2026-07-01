"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { HUB_TONE_CLASS, type HubNavItem, type HubTone } from "@/lib/nav-config";

export function HubNav({ items, tone }: { items: HubNavItem[]; tone: HubTone }) {
  const pathname = usePathname();
  const styles = HUB_TONE_CLASS[tone];

  return (
    <nav className="mb-6 flex flex-wrap gap-2 border-b border-gray-200 pb-3">
      {items.map((item) => {
        const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.key}
            href={item.href}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active ? styles.active : styles.inactive,
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
