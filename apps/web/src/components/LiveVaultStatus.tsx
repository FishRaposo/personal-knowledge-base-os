"use client";

import { useEffect, useState } from "react";
import { Activity, Radio } from "lucide-react";
import { API_BASE, api } from "@/lib/api";
import { selectedVault } from "@/components/VaultPicker";
import type { LiveEvent } from "@/types";

export default function LiveVaultStatus() {
  const [vaultId, setVaultId] = useState("default");
  const [running, setRunning] = useState(false);
  const [lastEvent, setLastEvent] = useState<LiveEvent | null>(null);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    const refresh = () => {
      const id = selectedVault();
      setVaultId(id);
      api.getWatcher(id).then(({ data }) => setRunning(data.running)).catch(() => undefined);
    };
    refresh();
    window.addEventListener("pkb:vault-changed", refresh);
    return () => window.removeEventListener("pkb:vault-changed", refresh);
  }, []);

  useEffect(() => {
    let source: EventSource | undefined;
    let interval: ReturnType<typeof setInterval> | undefined;
    try {
      source = new EventSource(`${API_BASE}/events?vault_id=${encodeURIComponent(vaultId)}`);
      source.onmessage = (message) => {
        try { setLastEvent(JSON.parse(message.data) as LiveEvent); } catch { /* ignore malformed events */ }
      };
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
    const { data } = await api.setWatcher(vaultId, !running);
    setRunning(data.running);
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-ink-200 bg-white px-3 py-2 text-xs text-ink-600" data-testid="live-vault-status">
      <Radio className={running ? "h-3.5 w-3.5 text-green-600" : "h-3.5 w-3.5 text-ink-400"} />
      <span>{running ? "Watcher running" : "Watcher stopped"}</span>
      <button className="rounded border border-ink-200 px-2 py-1 hover:bg-ink-50" onClick={toggle}>{running ? "Stop" : "Start"} watcher</button>
      {lastEvent ? <span className="inline-flex items-center gap-1 text-brand-700"><Activity className="h-3.5 w-3.5" />{lastEvent.event.replaceAll("_", " ")}</span> : null}
      {fallback ? <span className="text-ink-400">Polling fallback</span> : <span className="text-green-700">Live SSE</span>}
    </div>
  );
}
