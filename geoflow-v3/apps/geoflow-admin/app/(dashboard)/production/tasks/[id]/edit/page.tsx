"use client";

import { TaskCreateForm } from "@/components/operations/TaskCreateForm";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_MORE_NAV, PRODUCTION_NAV } from "@/lib/nav-config";
import { useRouteParams } from "@/lib/use-route-params";

export default function EditProductionTaskPage({ params }: { params: Promise<{ id: string }> }) {
  const token = useAuthGuard();
  const { id } = useRouteParams(params);
  if (!token) return null;
  return (
    <div>
      <HubHeader title={zh.production.hubTitle} subtitle={zh.taskEdit.subtitle} />
      <HubNav items={PRODUCTION_NAV} moreItems={PRODUCTION_MORE_NAV} tone="emerald" />
      <TaskCreateForm taskId={Number(id)} />
    </div>
  );
}
