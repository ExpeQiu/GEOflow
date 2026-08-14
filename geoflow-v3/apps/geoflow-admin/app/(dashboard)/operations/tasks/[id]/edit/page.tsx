import { redirect } from "next/navigation";

export default async function OperationsTaskEditRedirect({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  redirect(`/production/tasks/${id}/edit`);
}
