/** Admin 六语言实验室：完整文案仅中文，其它 locale 顶栏/登录骨架，正文回退中文。 */
export const ADMIN_LOCALES = ["zh", "en", "ja", "ko", "de", "fr"] as const;
export type AdminLocale = (typeof ADMIN_LOCALES)[number];

export const LOCALE_STORAGE_KEY = "geoflow-admin-locale";

export const LOCALE_LABELS: Record<AdminLocale, string> = {
  zh: "中文",
  en: "English",
  ja: "日本語",
  ko: "한국어",
  de: "Deutsch",
  fr: "Français",
};

export function isAdminLocale(value: string | null | undefined): value is AdminLocale {
  return Boolean(value && (ADMIN_LOCALES as readonly string[]).includes(value));
}
