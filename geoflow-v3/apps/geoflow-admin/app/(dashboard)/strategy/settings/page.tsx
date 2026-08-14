import { redirect } from "next/navigation";

/** 探针配置已并入「数据采集」页 */
export default function LegacySettingsRedirect() {
  redirect("/strategy/probes");
}
