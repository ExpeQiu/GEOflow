"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { apiDelete, apiGet, apiPost, getToken } from "@/lib/api-client";
import { PRODUCTION_NAV } from "@/lib/nav-config";
import { zh } from "@/lib/i18n/zh";

type LibraryConfig = {
  listPath: string;
  createPath: string;
  deletePath: (id: number) => string;
  itemPath?: (libId: number) => string;
  itemCreatePath?: (libId: number) => string;
  itemDeletePath?: (itemId: number) => string;
  title: string;
  itemLabel: string;
  itemField: "title" | "keyword" | "original_name";
};

const CONFIGS: Record<string, LibraryConfig> = {
  titles: {
    listPath: "/api/admin/materials/title-libraries",
    createPath: "/api/admin/materials/title-libraries",
    deletePath: (id) => `/api/admin/materials/title-libraries/${id}`,
    itemPath: (id) => `/api/admin/materials/title-libraries/${id}/titles`,
    itemCreatePath: (id) => `/api/admin/materials/title-libraries/${id}/titles`,
    itemDeletePath: (id) => `/api/admin/materials/titles/${id}`,
    title: "标题库",
    itemLabel: "标题",
    itemField: "title",
  },
  keywords: {
    listPath: "/api/admin/materials/keyword-libraries",
    createPath: "/api/admin/materials/keyword-libraries",
    deletePath: (id) => `/api/admin/materials/keyword-libraries/${id}`,
    itemPath: (id) => `/api/admin/materials/keyword-libraries/${id}/keywords`,
    itemCreatePath: (id) => `/api/admin/materials/keyword-libraries/${id}/keywords`,
    title: "关键词库",
    itemLabel: "关键词",
    itemField: "keyword",
  },
  images: {
    listPath: "/api/admin/materials/image-libraries",
    createPath: "/api/admin/materials/image-libraries",
    deletePath: (id) => `/api/admin/materials/image-libraries/${id}`,
    itemPath: (id) => `/api/admin/materials/image-libraries/${id}/images`,
    itemCreatePath: (id) => `/api/admin/materials/image-libraries/${id}/images`,
    title: "图片库",
    itemLabel: "图片路径",
    itemField: "original_name",
  },
};

export function MaterialsLibraryPage({ kind }: { kind: keyof typeof CONFIGS }) {
  const token = useAuthGuard();
  const cfg = CONFIGS[kind];
  const [libraries, setLibraries] = useState<{ id: number; name: string; count: number }[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [items, setItems] = useState<{ id: number; title?: string; keyword?: string; original_name?: string }[]>([]);
  const [newLibName, setNewLibName] = useState("");
  const [newItem, setNewItem] = useState("");
  const [flash, setFlash] = useState("");

  const loadLibraries = useCallback(async () => {
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: { id: number; name: string; count: number }[] }>(cfg.listPath, t);
    setLibraries(data.items);
    if (data.items.length && !selectedId) setSelectedId(data.items[0].id);
  }, [cfg.listPath, selectedId]);

  const loadItems = useCallback(async (libId: number) => {
    if (!cfg.itemPath) return;
    const t = getToken();
    if (!t) return;
    const data = await apiGet<{ items: typeof items }>(cfg.itemPath(libId), t);
    setItems(data.items);
  }, [cfg]);

  useEffect(() => {
    if (token) loadLibraries().catch(() => setFlash("加载失败"));
  }, [token, loadLibraries]);

  useEffect(() => {
    if (selectedId) loadItems(selectedId).catch(() => undefined);
  }, [selectedId, loadItems]);

  async function createLibrary(e: FormEvent) {
    e.preventDefault();
    const t = getToken();
    if (!t || !newLibName.trim()) return;
    await apiPost(cfg.createPath, t, { name: newLibName.trim() });
    setNewLibName("");
    await loadLibraries();
  }

  async function createItem(e: FormEvent) {
    e.preventDefault();
    if (!selectedId || !cfg.itemCreatePath || !newItem.trim()) return;
    const t = getToken();
    if (!t) return;
    const body =
      cfg.itemField === "title"
        ? { title: newItem.trim() }
        : cfg.itemField === "keyword"
          ? { keyword: newItem.trim() }
          : { original_name: newItem.trim(), file_path: newItem.trim() };
    await apiPost(cfg.itemCreatePath(selectedId), t, body);
    setNewItem("");
    await loadItems(selectedId);
  }

  if (!token) return null;

  return (
    <div>
      <HubHeader title={cfg.title} subtitle="管理素材库与库内条目" />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <Link href="/production/materials" className="mb-4 inline-block text-sm text-emerald-700">← 素材 Hub</Link>
      {flash && <FlashAlert variant="error">{flash}</FlashAlert>}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <h3 className="font-medium text-gray-900">库列表</h3>
          <form onSubmit={createLibrary} className="mt-3 flex gap-2">
            <input className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="新库名称" value={newLibName} onChange={(e) => setNewLibName(e.target.value)} />
            <button type="submit" className="inline-flex items-center rounded-md bg-emerald-600 px-3 py-2 text-sm text-white"><Plus className="mr-1 h-4 w-4" />新建</button>
          </form>
          <ul className="mt-4 divide-y divide-gray-100">
            {libraries.map((lib) => (
              <li key={lib.id} className="flex items-center justify-between py-2">
                <button type="button" onClick={() => setSelectedId(lib.id)} className={`text-sm ${selectedId === lib.id ? "font-semibold text-emerald-800" : "text-gray-700"}`}>
                  {lib.name} ({lib.count})
                </button>
                <button type="button" onClick={() => apiDelete(cfg.deletePath(lib.id), getToken()!).then(loadLibraries)} className="text-xs text-red-600">删除</button>
              </li>
            ))}
          </ul>
        </section>
        <section className="rounded-lg bg-white p-4 shadow-sm ring-1 ring-gray-200">
          <h3 className="font-medium text-gray-900">{cfg.itemLabel}条目</h3>
          {selectedId && cfg.itemCreatePath && (
            <form onSubmit={createItem} className="mt-3 flex gap-2">
              <input className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder={`新${cfg.itemLabel}`} value={newItem} onChange={(e) => setNewItem(e.target.value)} />
              <button type="submit" className="rounded-md bg-emerald-600 px-3 py-2 text-sm text-white">添加</button>
            </form>
          )}
          <ul className="mt-4 max-h-96 space-y-2 overflow-y-auto text-sm text-gray-700">
            {items.map((item) => (
              <li key={item.id} className="flex justify-between rounded-md bg-gray-50 px-3 py-2">
                <span>{item.title || item.keyword || item.original_name}</span>
                {cfg.itemDeletePath && (
                  <button type="button" onClick={() => apiDelete(cfg.itemDeletePath!(item.id), getToken()!).then(() => selectedId && loadItems(selectedId))} className="text-xs text-red-600">删</button>
                )}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
