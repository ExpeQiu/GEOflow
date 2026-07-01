"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import type { CategoryItem, CategoryPayload } from "@/lib/materials-types";

const emptyForm: CategoryPayload = { name: "", slug: "", description: "", sort_order: 0 };

export function CategoriesManagePanel() {
  const [items, setItems] = useState<CategoryItem[]>([]);
  const [form, setForm] = useState<CategoryPayload>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const data = await apiGet<{ items: CategoryItem[] }>("/api/admin/materials/categories", token);
      setItems(data.items);
    } catch {
      setError(zh.materialsManage.loadError);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function startEdit(item: CategoryItem) {
    setEditingId(item.id);
    setForm({ name: item.name, slug: item.slug, description: item.description, sort_order: item.sort_order });
    setError("");
    setSuccess("");
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      setError(zh.materialsManage.errors.nameRequired);
      return;
    }
    const token = getToken();
    if (!token) return;
    setSubmitting(true);
    setError("");
    setSuccess("");
    try {
      const payload = { ...form, name: form.name.trim(), slug: form.slug?.trim() || undefined };
      if (editingId) {
        await apiPatch(`/api/admin/materials/categories/${editingId}`, token, payload);
        setSuccess(zh.materialsManage.categoryUpdated);
      } else {
        await apiPost("/api/admin/materials/categories", token, payload);
        setSuccess(zh.materialsManage.categoryCreated);
      }
      resetForm();
      await load();
    } catch {
      setError(zh.materialsManage.saveError);
    } finally {
      setSubmitting(false);
    }
  }

  async function onDelete(id: number) {
    const token = getToken();
    if (!token) return;
    setError("");
    try {
      await apiDelete(`/api/admin/materials/categories/${id}`, token);
      setSuccess(zh.materialsManage.categoryDeleted);
      if (editingId === id) resetForm();
      await load();
    } catch {
      setError(zh.materialsManage.deleteError);
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center gap-4">
        <Link href="/production/materials" className="text-gray-400 hover:text-gray-600">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{zh.materialsManage.categoriesTitle}</h1>
          <p className="mt-1 text-sm text-gray-600">{zh.materialsManage.categoriesSubtitle}</p>
        </div>
      </div>

      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {success && <FlashAlert variant="success">{success}</FlashAlert>}
      {loading && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <form onSubmit={onSubmit} className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200 lg:col-span-1">
          <h2 className="text-lg font-medium text-gray-900">
            {editingId ? zh.materialsManage.editCategory : zh.materialsManage.newCategory}
          </h2>
          <div className="mt-4 space-y-4">
            <Field label={`${zh.materialsManage.fields.name} *`} value={form.name} onChange={(v) => setForm({ ...form, name: v })} />
            <Field label={zh.materialsManage.fields.slug} value={form.slug ?? ""} onChange={(v) => setForm({ ...form, slug: v })} placeholder="auto" />
            <Field label={zh.materialsManage.fields.description} value={form.description} onChange={(v) => setForm({ ...form, description: v })} multiline />
            <Field
              label={zh.materialsManage.fields.sortOrder}
              value={String(form.sort_order)}
              onChange={(v) => setForm({ ...form, sort_order: Number(v) || 0 })}
              type="number"
            />
          </div>
          <div className="mt-6 flex gap-2">
            <button type="submit" disabled={submitting} className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">
              {editingId ? zh.materialsManage.save : zh.materialsManage.create}
            </button>
            {editingId && (
              <button type="button" onClick={resetForm} className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                {zh.materialsManage.cancel}
              </button>
            )}
          </div>
        </form>

        <div className="overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-200 lg:col-span-2">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {[zh.materialsManage.fields.name, zh.materialsManage.fields.slug, zh.materialsManage.fields.sortOrder, zh.materialsManage.actions].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-sm text-gray-500">
                    {zh.materialsManage.emptyCategories}
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.slug}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{item.sort_order}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <IconBtn title={zh.materialsManage.edit} onClick={() => startEdit(item)}>
                          <Pencil className="h-4 w-4" />
                        </IconBtn>
                        <IconBtn title={zh.materialsManage.delete} onClick={() => onDelete(item.id)} tone="red">
                          <Trash2 className="h-4 w-4" />
                        </IconBtn>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  multiline,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  multiline?: boolean;
  type?: string;
  placeholder?: string;
}) {
  const className = "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500";
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      {multiline ? (
        <textarea rows={2} value={value} onChange={(e) => onChange(e.target.value)} className={className} />
      ) : (
        <input type={type} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} className={className} />
      )}
    </div>
  );
}

function IconBtn({
  children,
  onClick,
  title,
  tone,
}: {
  children: React.ReactNode;
  onClick: () => void;
  title: string;
  tone?: "red";
}) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className={`inline-flex h-8 w-8 items-center justify-center rounded-md border ${
        tone === "red" ? "border-red-200 text-red-600 hover:bg-red-50" : "border-gray-200 text-gray-600 hover:bg-gray-50"
      }`}
    />
  );
}
