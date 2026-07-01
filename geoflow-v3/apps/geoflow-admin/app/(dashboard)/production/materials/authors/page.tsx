"use client";

import { AuthorsManagePanel } from "@/components/production/AuthorsManagePanel";
import { useAuthGuard } from "@/hooks/use-auth-guard";

export default function AuthorsPage() {
  useAuthGuard();
  return <AuthorsManagePanel />;
}
