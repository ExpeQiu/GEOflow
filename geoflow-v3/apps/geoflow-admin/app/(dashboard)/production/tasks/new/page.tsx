"use client";

import { TaskCreateForm } from "@/components/operations/TaskCreateForm";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_NAV } from "@/lib/nav-config";

export default function NewProductionTaskPage() {
  useAuthGuard();
  return (
    <div>
      <HubHeader title={zh.production.hubTitle} subtitle={zh.taskCreate.subtitle} />
      <HubNav items={PRODUCTION_NAV} tone="emerald" />
      <TaskCreateForm />
    </div>
  );
}
