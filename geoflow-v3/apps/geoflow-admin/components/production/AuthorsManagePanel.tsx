"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowLeft, Pencil, Trash2 } from "lucide-react";
import { FlashAlert } from "@/components/admin/FlashAlert";
import { apiDelete, apiGet, apiPatch, apiPost, getToken } from "@/lib/api-client";
import { zh } from "@/lib/i18n/zh";
import type { AuthorItem, AuthorPayload } from "@/lib/materials-types";

const emptyForm: AuthorPayload = { name: "", bio: "", email: "" };

export function AuthorsManagePanel() {
  const [items, setItems] = useState<AuthorItem[]>([]);
  const [form, setForm] = useState<AuthorPayload>(emptyForm);
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
      const data = await apiGet<{ items: AuthorItem[] }>("/api/admin/materials/authors", token);
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

  function startEdit(item: AuthorItem) {
    setEditingId(item.id);
    setForm({ name: item.name, bio: item.bio, email: item.email });
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
      const payload = { ...form, name: form.name.trim() };
      if (editingId) {
        await apiPatch(`/api/admin/materials/authors/${editingId}`, token, payload);
        setSuccess(zh.materialsManage.authorUpdated);
      } else {
        await apiPost("/api/admin/materials/authors", token, payload);
        setSuccess(zh.materialsManage.authorCreated);
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
    try {
      await apiDelete(`/api/admin/materials/authors/${id}`, token);
      setSuccess(zh.materialsManage.authorDeleted);
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
          <h1 className="text-2xl font-bold text-gray-900">{zh.materialsManage.authorsTitle}</h1>
          <p className="mt-1 text-sm text-gray-600">{zh.materialsManage.authorsSubtitle}</p>
        </div>
      </div>

      {error && <FlashAlert variant="error">{error}</FlashAlert>}
      {success && <FlashAlert variant="success">{success}</FlashAlert>}
      {loading && <FlashAlert variant="info">{zh.common.loading}</FlashAlert>}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <form onSubmit={onSubmit} className="rounded-lg bg-white p-6 shadow-sm ring-1 ring-gray-200">
          <h2 className="text-lg font-medium text-gray-900">{editingId ? zh.materialsManage.editAuthor : zh.materialsManage.newAuthor}</h2>
          <div className="mt-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">{zh.materialsManage.fields.name} *</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{zh.materialsManage.fields.bio}</label>
              <textarea rows={3} value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">{zh.materialsManage.fields.email}</label>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
            </div>
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
                {[zh.materialsManage.fields.name, zh.materialsManage.fields.bio, zh.materialsManage.actions].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{item.name}</td>
                  <td className="max-w-md truncate px-4 py-3 text-sm text-gray-600">{item.bio || "—"}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button type="button" onClick={() => startEdit(item)} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-gray-200 text-gray-600 hover:bg-gray-50">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button type="button" onClick={() => onDelete(item.id)} className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-red-200 text-red-600 hover:bg-red-50">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
