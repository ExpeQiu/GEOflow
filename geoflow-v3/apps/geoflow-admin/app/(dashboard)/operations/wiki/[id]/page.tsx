"use client";

import { HubNav } from "@/components/admin/HubNav";
import { WikiEditForm } from "@/components/operations/WikiEditForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";
import { useRouteParams } from "@/lib/use-route-params";

export default function WikiEditPage({ params }: { params: Promise<{ id: string }> }) {
  const token = useAuthGuard();
  const { id } = useRouteParams(params);
  const articleId = Number(id);
  if (!token || !Number.isFinite(articleId) || articleId <= 0) return null;
  return (
    <div>
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      <WikiEditForm articleId={articleId} />
    </div>
  );
}
