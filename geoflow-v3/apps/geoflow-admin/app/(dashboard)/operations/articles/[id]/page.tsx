"use client";

import { ArticleEditForm } from "@/components/operations/ArticleEditForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { useRouteParams } from "@/lib/use-route-params";

export default function ArticleEditPage({ params }: { params: Promise<{ id: string }> }) {
  useAuthGuard();
  const { id } = useRouteParams(params);
  const articleId = Number(id);

  if (!Number.isFinite(articleId) || articleId <= 0) {
    return null;
  }

  return <ArticleEditForm articleId={articleId} />;
}
