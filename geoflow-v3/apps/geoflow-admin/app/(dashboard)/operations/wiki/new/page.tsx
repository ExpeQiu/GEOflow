"use client";

import { HubNav } from "@/components/admin/HubNav";
import { WikiEditForm } from "@/components/operations/WikiEditForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { OPERATIONS_MORE_NAV, OPERATIONS_NAV } from "@/lib/nav-config";

export default function WikiNewPage() {
  const token = useAuthGuard();
  if (!token) return null;
  return (
    <div>
      <HubNav items={OPERATIONS_NAV} moreItems={OPERATIONS_MORE_NAV} tone="blue" />
      <WikiEditForm />
    </div>
  );
}
