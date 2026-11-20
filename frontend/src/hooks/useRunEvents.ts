import { useEffect, useRef, useState } from "react";

import { API_BASE } from "../api/client";
import type { RunEvent } from "../api/types";

/**
 * Live run events via Server-Sent Events. Every event is a real backend step (no timers).
 * Reconnects from the last seen sequence number whenever the run status changes; the stream ends
 * when the backend says the run paused or finished, then ``onStatus`` is called.
 */
export function useRunEvents(runId: string | undefined, status: string | undefined, onStatus?: (status: string) => void) {
  const active = status === "queued" || status === "running";
  const [events, setEvents] = useState<RunEvent[]>([]);
  const lastSeq = useRef(0);
  const statusCb = useRef(onStatus);
  statusCb.current = onStatus;

  useEffect(() => {
    setEvents([]);
    lastSeq.current = 0;
  }, [runId]);

  useEffect(() => {
    if (!runId) return;
    let closed = false;
    let source: EventSource | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      source = new EventSource(`${API_BASE}/runs/${runId}/events?after_seq=${lastSeq.current}`, {
        withCredentials: true,
      });
      source.addEventListener("run_event", (e) => {
        const ev = JSON.parse((e as MessageEvent<string>).data) as RunEvent;
        if (ev.seq <= lastSeq.current) return;
        lastSeq.current = ev.seq;
        setEvents((prev) => [...prev, ev]);
      });
      source.addEventListener("run_status", (e) => {
        const data = JSON.parse((e as MessageEvent<string>).data) as { status: string };
        source?.close();
        statusCb.current?.(data.status);
      });
      source.onerror = () => {
        source?.close();
        if (!closed && active) retry = setTimeout(connect, 2000);
      };
    };
    connect();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      source?.close();
    };
    // Reconnect whenever the run's status changes so events after a resume are streamed too.
  }, [runId, status, active]);

  return events;
}
