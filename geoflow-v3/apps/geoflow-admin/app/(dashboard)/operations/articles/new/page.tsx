"use client";

import { ArticleCreateForm } from "@/components/operations/ArticleCreateForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";

export default function ArticleNewPage() {
  const token = useAuthGuard();
  if (!token) return null;
  return <ArticleCreateForm />;
}
