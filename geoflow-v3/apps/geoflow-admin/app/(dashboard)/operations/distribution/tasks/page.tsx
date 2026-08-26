"use client";

import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { DistributionSubNav } from "@/components/operations/DistributionSubNav";
import { DistributionTaskForm } from "@/components/operations/DistributionTaskForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { zh } from "@/lib/i18n/zh";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";

export default function DistributionTasksPage() {
  useAuthGuard();
  return (
    <div>
      <HubHeader title={zh.distributionTask.title} subtitle={zh.distributionTask.subtitle} />
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      <DistributionSubNav />
      <DistributionTaskForm />
    </div>
  );
}
