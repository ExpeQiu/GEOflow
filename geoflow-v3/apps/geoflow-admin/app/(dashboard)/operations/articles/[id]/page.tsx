"use client";

import { useParams } from "next/navigation";
import { ArticleEditForm } from "@/components/operations/ArticleEditForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";

export default function ArticleEditPage() {
  useAuthGuard();
  const params = useParams<{ id: string }>();
  const articleId = Number(params.id);

  if (!Number.isFinite(articleId) || articleId <= 0) {
    return null;
  }

  return <ArticleEditForm articleId={articleId} />;
}
