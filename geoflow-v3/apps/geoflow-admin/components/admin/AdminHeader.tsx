"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import {
  Bell,
  ChevronDown,
  Home,
  LogOut,
  Menu,
  Settings,
  User,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { clearToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import { resolveActiveNav, TOP_NAV } from "@/lib/nav-config";

export function AdminHeader({ version = "3.0.0" }: { version?: string }) {
  const pathname = usePathname();
  const active = resolveActiveNav(pathname);
  const [userOpen, setUserOpen] = useState(false);
  const [notifyOpen, setNotifyOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const rootRef = useRef<HTMLElement>(null);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) {
        setUserOpen(false);
        setNotifyOpen(false);
        setMobileOpen(false);
      }
    }
    document.addEventListener("click", onDocClick);
    return () => document.removeEventListener("click", onDocClick);
  }, []);

  function logout() {
    clearToken();
    window.location.href = "/login";
  }

  return (
    <header ref={rootRef} className="border-b bg-white shadow-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-3 px-4 sm:px-6 lg:gap-4 lg:px-8">
        <Link href="/dashboard" className="shrink-0 text-lg font-semibold text-gray-900 sm:text-xl">
          {zh.brand}
        </Link>

        <nav className="hidden min-w-0 flex-1 items-center lg:flex">
          <div className="flex w-full min-w-0 items-center gap-3 overflow-x-auto py-2 lg:gap-5 [scrollbar-width:thin]">
            {TOP_NAV.map((item, index) => (
              <span key={item.key} className="contents">
                {(index === 1 || index === 2 || index === 3) && (
                  <span className="hidden shrink-0 text-gray-300 lg:inline" aria-hidden>
                    |
                  </span>
                )}
                <Link
                  href={item.href}
                  title={item.group ?? ""}
                  className={cn(
                    "shrink-0 whitespace-nowrap text-[15px] transition-colors duration-200",
                    active === item.key ? "font-medium text-blue-600" : "text-gray-500 hover:text-gray-700",
                  )}
                >
                  {item.label}
                </Link>
              </span>
            ))}
          </div>
        </nav>

        <div className="ml-auto flex shrink-0 items-center gap-2 sm:gap-3">
          <div className="relative">
            <button
              type="button"
              aria-label={zh.header.notifications}
              className="relative rounded-full p-2 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              onClick={(e) => {
                e.stopPropagation();
                setNotifyOpen((v) => !v);
                setUserOpen(false);
              }}
            >
              <Bell className="h-5 w-5" />
            </button>
            {notifyOpen && (
              <div className="absolute right-0 z-50 mt-3 w-80 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-xl">
                <div className="border-b border-gray-100 px-4 py-3">
                  <div className="text-sm font-semibold text-gray-900">{zh.header.notificationsTitle}</div>
                </div>
                <div className="px-4 py-4">
                  <div className="text-sm font-semibold text-gray-900">{zh.header.upToDate}</div>
                  <p className="mt-2 text-sm leading-6 text-gray-600">{zh.header.noUpdateDesc}</p>
                  <div className="mt-4 rounded-xl bg-gray-50 px-3 py-3 text-xs text-gray-500">
                    {zh.header.currentVersion(version)}
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="relative hidden md:block">
            <button
              type="button"
              className="flex items-center space-x-1 text-sm text-gray-600 transition-colors hover:text-gray-900"
              onClick={(e) => {
                e.stopPropagation();
                setUserOpen((v) => !v);
                setNotifyOpen(false);
              }}
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100">
                <User className="h-4 w-4 text-blue-600" />
              </div>
              <ChevronDown className="h-4 w-4" />
            </button>
            {userOpen && (
              <div className="absolute right-0 z-50 mt-2 w-56 rounded-md bg-white py-1 shadow-lg">
                <div className="border-b border-gray-100 px-4 py-2">
                  <div className="text-sm text-gray-700">{zh.header.welcome("admin")}</div>
                  <div className="text-xs text-gray-400">{zh.header.admin}</div>
                </div>
                <Link href="/dashboard" className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                  <Home className="mr-2 h-4 w-4" />
                  {zh.nav.backHome}
                </Link>
                <Link href="/settings/site" className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                  <Settings className="mr-2 h-4 w-4" />
                  {zh.nav.systemSettings}
                </Link>
                <Link href="/settings/security" className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                  <Settings className="mr-2 h-4 w-4" />
                  安全与密码
                </Link>
                <Link href="/settings/api-tokens" className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                  <Settings className="mr-2 h-4 w-4" />
                  API Tokens
                </Link>
                <Link href="/settings/admins" className="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                  <Settings className="mr-2 h-4 w-4" />
                  管理员
                </Link>
                <div className="border-t border-gray-100" />
                <button
                  type="button"
                  onClick={logout}
                  className="flex w-full items-center px-4 py-2 text-left text-sm text-red-600 hover:bg-gray-100"
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  {zh.nav.logout}
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            className="rounded-md bg-white p-2 shadow-md lg:hidden"
            onClick={(e) => {
              e.stopPropagation();
              setMobileOpen((v) => !v);
            }}
          >
            <Menu className="h-5 w-5 text-gray-600" />
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t bg-gray-50 px-2 pb-3 pt-2 sm:px-3 lg:hidden">
          {TOP_NAV.map((item) => (
            <Link
              key={item.key}
              href={item.href}
              className={cn(
                "mb-1 block rounded-md px-3 py-2 text-base font-medium transition-colors",
                active === item.key ? "bg-blue-100 text-blue-600" : "text-gray-600 hover:bg-gray-100",
              )}
            >
              {item.label}
            </Link>
          ))}
          <button type="button" onClick={logout} className="mt-2 block w-full rounded-md px-3 py-2 text-left text-base text-red-600 hover:bg-gray-100">
            {zh.nav.logout}
          </button>
        </div>
      )}
    </header>
  );
}
