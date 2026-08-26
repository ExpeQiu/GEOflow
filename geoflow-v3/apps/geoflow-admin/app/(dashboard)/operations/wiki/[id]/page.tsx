"use client";

import { useParams } from "next/navigation";
import { HubNav } from "@/components/admin/HubNav";
import { WikiEditForm } from "@/components/operations/WikiEditForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";

export default function WikiEditPage() {
  const token = useAuthGuard();
  const params = useParams<{ id: string }>();
  const articleId = Number(params.id);
  if (!token || !Number.isFinite(articleId) || articleId <= 0) return null;
  return (
    <div>
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      <WikiEditForm articleId={articleId} />
    </div>
  );
}
