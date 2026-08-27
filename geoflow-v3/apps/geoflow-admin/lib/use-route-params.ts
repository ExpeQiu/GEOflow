"use client";

import { use } from "react";

/** Next.js 16：动态段 params 为 Promise，客户端页需 React.use() 解包。 */
export function useRouteParams<T extends Record<string, string>>(params: Promise<T>): T {
  return use(params);
}
