"use client";

import { useParams } from "next/navigation";
import { TaskCreateForm } from "@/components/operations/TaskCreateForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";

export default function TaskEditPage() {
  const token = useAuthGuard();
  const { id } = useParams<{ id: string }>();
  if (!token) return null;
  return <TaskCreateForm taskId={Number(id)} />;
