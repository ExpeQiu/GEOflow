"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchAdminSession, getToken, markCookieSessionActive, setAdminProfile } from "@/lib/api-client";

export function useAuthGuard() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const mem = getToken();
      const session = await fetchAdminSession();
      if (cancelled) return;
      if (!session && !mem) {
        router.push("/login");
        return;
      }
      if (session) {
        setAdminProfile(session);
        markCookieSessionActive(true);
      } else if (mem) {
        markCookieSessionActive(true);
      }
      setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  return ready ? getToken() || "cookie" : null;
}
