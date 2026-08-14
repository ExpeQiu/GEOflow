"use client";

import { useParams } from "next/navigation";
import { TaskCreateForm } from "@/components/operations/TaskCreateForm";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_NAV } from "@/lib/nav-config";

export default function EditProductionTaskPage() {
  const token = useAuthGuard();
  const { id } = useParams<{ id: string }>();
  if (!token) return null;
  return (
    <div>
      <HubHeader title={zh.production.hubTitle} subtitle={zh.taskEdit.subtitle} />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <TaskCreateForm taskId={Number(id)} />
    </div>
  );
}
