import { redirect } from "next/navigation";

/** 策略侧运营数据入口 → L3 运营与分发 */
export default function StrategyAnalyticsLegacyRedirect() {
  redirect("/operations/analytics");
}
