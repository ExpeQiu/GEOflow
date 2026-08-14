"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";
import { HUB_TONE_CLASS, type HubNavItem, type HubTone } from "@/lib/nav-config";

function isItemActive(pathname: string, item: HubNavItem): boolean {
  if (item.matchPrefixes?.length) {
    const sorted = [...item.matchPrefixes].sort((a, b) => b.length - a.length);
    return sorted.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
  }
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function HubNav({ items, tone }: { items: HubNavItem[]; tone: HubTone }) {
  const pathname = usePathname();
  const styles = HUB_TONE_CLASS[tone];

  return (
    <nav className="mb-6 border-b border-gray-200 pb-3" aria-label="板块导航">
      <div className="flex flex-wrap items-center gap-x-1 gap-y-2">
        {items.map((item, index) => {
          const active = isItemActive(pathname, item);
          const prevGroup = index > 0 ? items[index - 1]?.group : undefined;
          const showGroup = Boolean(item.group && item.group !== prevGroup);

          return (
            <span key={item.key} className="contents">
              {showGroup && (
                <>
                  {index > 0 && <span className="mx-1 hidden h-4 w-px bg-gray-200 sm:inline" aria-hidden="true" />}
                  <span className="mr-1 shrink-0 text-[11px] font-medium uppercase tracking-wide text-gray-400">
                    {item.group}
                  </span>
                </>
              )}
              <Link
                href={item.href}
                className={cn(
                  "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active ? styles.active : styles.inactive,
                )}
              >
                {item.label}
              </Link>
            </span>
          );
        })}
      </div>
    </nav>
  );
}
