import { redirect } from "next/navigation";

/** 探针配置已并入探针 Hub「探针设置」Tab */
export default function LegacySettingsRedirect() {
  redirect("/strategy/probes?view=settings");
}
