import { redirect } from "next/navigation";

/** 策略数据分析入口并入诊断总览（含 StrategyOverview） */
export default function StrategyAnalyticsLegacyRedirect() {
  redirect("/strategy/diagnosis");
}
