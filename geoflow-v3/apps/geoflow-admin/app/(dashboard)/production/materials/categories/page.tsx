"use client";

import { CategoriesManagePanel } from "@/components/production/CategoriesManagePanel";
import { useAuthGuard } from "@/hooks/use-auth-guard";

export default function CategoriesPage() {
  useAuthGuard();
  return <CategoriesManagePanel />;
}
