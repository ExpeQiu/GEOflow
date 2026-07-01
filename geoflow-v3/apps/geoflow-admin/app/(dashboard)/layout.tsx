"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearToken } from "@/lib/api-client";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/operations/tasks", label: "L3 运营" },
  { href: "/production/materials", label: "L2 生产" },
  { href: "/strategy/overview", label: "L1 策略" },
  { href: "/settings/site", label: "设置" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-bold text-[var(--primary)]">GEOFlow v3</span>
          <nav className="flex gap-4 text-sm">
            {NAV.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={pathname.startsWith(item.href.split("/").slice(0, 2).join("/")) ? "text-[var(--primary)] font-medium" : "text-[var(--muted)]"}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <button
          type="button"
          className="text-sm text-[var(--muted)]"
          onClick={() => {
            clearToken();
            window.location.href = "/login";
          }}
        >
          退出
        </button>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
