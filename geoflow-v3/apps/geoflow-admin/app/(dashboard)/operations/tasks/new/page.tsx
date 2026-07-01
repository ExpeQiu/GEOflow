"use client";

import { TaskCreateForm } from "@/components/operations/TaskCreateForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";

export default function NewTaskPage() {
  useAuthGuard();
  return (
    <div>
      <TaskCreateForm />
    </div>
  );
}
