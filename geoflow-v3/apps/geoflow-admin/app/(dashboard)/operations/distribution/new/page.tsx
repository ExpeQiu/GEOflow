"use client";

import { DistributionChannelCreateForm } from "@/components/operations/DistributionChannelCreateForm";
import { useAuthGuard } from "@/hooks/use-auth-guard";

export default function NewDistributionChannelPage() {
  useAuthGuard();
  return <DistributionChannelCreateForm />;
}
