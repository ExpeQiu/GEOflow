"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { HUB_TONE_CLASS, LAB_NAV_LABEL, type HubNavItem, type HubTone } from "@/lib/nav-config";

function isItemActive(pathname: string, item: HubNavItem): boolean {
  if (item.matchPrefixes?.length) {
    const sorted = [...item.matchPrefixes].sort((a, b) => b.length - a.length);
    return sorted.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
  }
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

const MORE_MENU_ACTIVE: Record<HubTone, string> = {
  emerald: "bg-emerald-50 font-medium text-emerald-800",
  blue: "bg-blue-50 font-medium text-blue-800",
  violet: "bg-violet-50 font-medium text-violet-800",
};

export function HubNav({
  items,
  moreItems,
  moreLabel = LAB_NAV_LABEL,
  tone,
}: {
  items: HubNavItem[];
  moreItems?: HubNavItem[];
  moreLabel?: string;
  tone: HubTone;
}) {
  const pathname = usePathname();
  const styles = HUB_TONE_CLASS[tone];
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);
  const moreActive = Boolean(moreItems?.some((item) => isItemActive(pathname, item)));

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!moreRef.current?.contains(e.target as Node)) setMoreOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

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

        {!!moreItems?.length && (
          <div ref={moreRef} className="relative ml-1">
            <button
              type="button"
              onClick={() => setMoreOpen((v) => !v)}
              className={cn(
                "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                moreActive || moreOpen ? styles.active : styles.inactive,
              )}
              aria-expanded={moreOpen}
              aria-haspopup="menu"
            >
              {moreLabel} ▾
            </button>
            {moreOpen && (
              <div
                role="menu"
                className="absolute left-0 z-20 mt-1 min-w-[10rem] rounded-md border border-gray-200 bg-white py-1 shadow-lg"
              >
                {moreItems.map((item) => {
                  const active = isItemActive(pathname, item);
                  return (
                    <Link
                      key={item.key}
                      href={item.href}
                      role="menuitem"
                      onClick={() => setMoreOpen(false)}
                      className={cn(
                        "block px-3 py-2 text-sm",
                        active ? MORE_MENU_ACTIVE[tone] : "text-gray-700 hover:bg-gray-50",
                      )}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </nav>
  );
}
