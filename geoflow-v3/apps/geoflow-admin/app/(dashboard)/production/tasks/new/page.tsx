"use client";

import { ThemeFirstProduceEntry } from "@/components/production/ThemeFirstProduceEntry";
import { HubHeader } from "@/components/admin/HubHeader";
import { HubNav } from "@/components/admin/HubNav";
import { useAuthGuard } from "@/hooks/use-auth-guard";
import { zh } from "@/lib/i18n/zh";
import { PRODUCTION_MORE_NAV, PRODUCTION_NAV } from "@/lib/nav-config";

export default function NewProductionTaskPage() {
  useAuthGuard();
  return (
    <div>
      <HubHeader title={zh.production.hubTitle} subtitle="从主题包确认选题并启生产（主链路）" />
      <HubNav items={PRODUCTION_NAV} moreItems={PRODUCTION_MORE_NAV} tone="emerald" />
      <ThemeFirstProduceEntry />
    </div>
  );
}
