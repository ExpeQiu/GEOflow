"use client";

import { DistributionChannelCreateForm } from "@/components/operations/DistributionChannelCreateForm";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { DistributionSubNav } from "@/components/operations/DistributionSubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";
import { useRouteParams } from "@/lib/use-route-params";

export default function DistributionChannelPage({ params }: { params: Promise<{ id: string }> }) {
  const token = useAuthGuard();
  const { id } = useRouteParams(params);

  if (!token) return null;

  return (
    <div>
      <HubHeader title="渠道详情" subtitle="" />
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      <DistributionSubNav />
      <DistributionChannelCreateForm channelId={id} />
    </div>
  );
}
