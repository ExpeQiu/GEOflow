"use client";

import { useEffect, useRef } from "react";

type TaskOverview = {
  tasks: { id: number; name: string; status: string }[];
  recent_runs: { id: number; task_id: number; status: string }[];
};

export function useTaskWebSocket(onUpdate: (data: TaskOverview) => void) {
  const cbRef = useRef(onUpdate);
  cbRef.current = onUpdate;

  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${proto}://${window.location.host}/ws/admin/tasks`;
    let ws: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let pingTimer: ReturnType<typeof setInterval> | null = null;
    let closed = false;

    function connect() {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.event === "tasks.overview.updated" && msg.data) {
            cbRef.current(msg.data as TaskOverview);
          }
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        if (!closed) retryTimer = setTimeout(connect, 5000);
      };
      pingTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) ws.send("ping");
      }, 30000);
    }

    connect();

    return () => {
      closed = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (pingTimer) clearInterval(pingTimer);
      ws?.close();
    };
  }, []);
}
