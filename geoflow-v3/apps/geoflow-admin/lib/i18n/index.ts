"use client";

import { createContext, createElement, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { de } from "@/lib/i18n/de";
import { en } from "@/lib/i18n/en";
import { fr } from "@/lib/i18n/fr";
import { ja } from "@/lib/i18n/ja";
import { ko } from "@/lib/i18n/ko";
import { zh } from "@/lib/i18n/zh";
import {
  ADMIN_LOCALES,
  LOCALE_STORAGE_KEY,
  type AdminLocale,
  isAdminLocale,
} from "@/lib/i18n/locales";

type Overlay = typeof en;
export type Messages = typeof zh;

const OVERLAYS: Partial<Record<AdminLocale, Overlay>> = { en, ja, ko, de, fr };

function mergeNav(base: Messages, overlay: Overlay | undefined): Messages {
  if (!overlay) return base;
  return {
    ...base,
    brand: overlay.brand ?? base.brand,
    nav: { ...base.nav, ...overlay.nav },
    header: { ...base.header, ...overlay.header },
    login: { ...base.login, ...overlay.login },
  };
}

const LocaleContext = createContext<{
  locale: AdminLocale;
  setLocale: (next: AdminLocale) => void;
  messages: Messages;
}>({ locale: "zh", setLocale: () => undefined, messages: zh });

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<AdminLocale>("zh");

  useEffect(() => {
    const stored = window.localStorage.getItem(LOCALE_STORAGE_KEY);
    if (isAdminLocale(stored)) setLocaleState(stored);
  }, []);

  function setLocale(next: AdminLocale) {
    setLocaleState(next);
    window.localStorage.setItem(LOCALE_STORAGE_KEY, next);
    document.documentElement.lang = next === "zh" ? "zh-CN" : next;
  }

  const messages = useMemo(() => mergeNav(zh, OVERLAYS[locale]), [locale]);
  const value = useMemo(() => ({ locale, setLocale, messages }), [locale, messages]);
  return createElement(LocaleContext.Provider, { value }, children);
}

export function useI18n() {
  return useContext(LocaleContext);
}

export { ADMIN_LOCALES, LOCALE_LABELS, type AdminLocale } from "@/lib/i18n/locales";
