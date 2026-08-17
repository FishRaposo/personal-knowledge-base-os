"use client";

import { useEffect, useState } from "react";
import { Activity, Radio } from "lucide-react";
import { API_BASE, api } from "@/lib/api";
import { useActiveVault } from "@/components/VaultPicker";
import type { LiveEvent } from "@/types";

export default function LiveVaultStatus() {
  const vaultId = useActiveVault();
  const [running, setRunning] = useState(false);
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null);
  const [fallback, setFallback] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLastEvent(null); setFallback(false); setError(null);
    api.getWatcher(vaultId).then(({ data }) => setRunning(data.running)).catch(() => undefined);
  }, [vaultId]);

  useEffect(() => {
    let source: EventSource | undefined;
    let interval: ReturnType<typeof setInterval> | undefined;
    try {
      source = new EventSource(`${API_BASE}/events?vault_id=${encodeURIComponent(vaultId)}`);
      const receive = (message: MessageEvent<string>) => {
        try {
          const raw = JSON.parse(message.data) as Partial<LiveEvent> & { type?: string };
          const event = raw.event ?? raw.type;
          if (typeof event === "string") setLastEvent({ id: String(raw.id ?? ""), event: event as LiveEvent["event"], data: raw.data ?? raw as Record<string, unknown> });
        } catch { /* ignore malformed events */ }
      };
      ["index_started", "note_changed", "index_completed", "index_failed", "watcher_started", "watcher_stopped"].forEach((event) => source?.addEventListener(event, receive));
      source.onmessage = receive;
      source.onerror = () => {
        source?.close();
        setFallback(true);
        interval = setInterval(() => api.getWatcher(vaultId).then(({ data }) => setRunning(data.running)).catch(() => undefined), 10_000);
      };
    } catch {
      setFallback(true);
    }
    return () => { source?.close(); if (interval) clearInterval(interval); };
  }, [vaultId]);

  async function toggle() {
    try { const { data } = await api.setWatcher(vaultId, !running); setRunning(data.running); } catch (err) { setError((err as Error).message); }
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-ink-200 bg-white px-3 py-2 text-xs text-ink-600" data-testid="live-vault-status">
      <Radio className={running ? "h-3.5 w-3.5 text-green-600" : "h-3.5 w-3.5 text-ink-400"} />
      <span>{running ? "Watcher running" : "Watcher stopped"}</span>
      <button className="rounded border border-ink-200 px-2 py-1 hover:bg-ink-50" onClick={toggle}>{running ? "Stop" : "Start"} watcher</button>
      {lastEvent ? <span className="inline-flex items-center gap-1 text-brand-700"><Activity className="h-3.5 w-3.5" />{String(lastEvent.event).replace(/_/g, " ")}</span> : null}
      {fallback ? <span className="text-ink-400">Polling fallback</span> : <span className="text-green-700">Live SSE</span>}
      {error ? <span role="alert" className="text-red-700">{error}</span> : null}
    </div>
  );
}
