"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Network, ArrowUpRight, Link2, CornerUpLeft, X } from "lucide-react";
import { api } from "@/lib/api";
import type { GraphResponse } from "@/types";
import GraphCanvas from "@/components/GraphCanvas";
import DemoBadge from "@/components/DemoBadge";
import TagPill from "@/components/TagPill";
import { EmptyState, ErrorState, Spinner } from "@/components/States";

export default function GraphPage() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demo, setDemo] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data, source } = await api.getGraph();
      setGraph(data);
      setDemo(source === "demo");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const selected = useMemo(
    () => graph?.nodes.find((n) => n.id === selectedId) ?? null,
    [graph, selectedId]
  );

  const outbound = useMemo(
    () =>
      selected
        ? graph!.edges.filter((e) => e.source === selected.id).map((e) => e.target)
        : [],
    [graph, selected]
  );
  const inbound = useMemo(
    () =>
      selected
        ? graph!.edges.filter((e) => e.target === selected.id).map((e) => e.source)
        : [],
    [graph, selected]
  );

  return (
    <div className="mx-auto max-w-6xl">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-ink-900">
            <Network className="h-6 w-6 text-brand-600" />
            Knowledge Graph
          </h1>
          <p className="mt-1 text-sm text-ink-500">
            Every note and its wikilinks. Click a node to inspect it, then open the
            note.
          </p>
        </div>
        {demo ? <DemoBadge /> : null}
      </header>

      {loading ? (
        <Spinner label="Building graph…" />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !graph || graph.nodes.length === 0 ? (
        <EmptyState
          title="The graph is empty"
          description="Index a vault with linked notes to see the graph populate."
          icon={<Network className="h-10 w-10" />}
        />
      ) : (
        <div className="grid gap-5 lg:grid-cols-[1fr_300px]">
          <div>
            <GraphCanvas
              graph={graph}
              onSelect={setSelectedId}
              selectedId={selectedId}
            />
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink-500">
              <span>{graph.nodes.length} notes</span>
              <span>{graph.edges.length} links</span>
              <span className="flex items-center gap-1.5">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-brand-500" />
                node (size = backlinks)
              </span>
            </div>
          </div>

          <aside className="rounded-xl border border-ink-200 bg-white p-4">
            {selected ? (
              <div data-testid="node-detail" className="animate-fade-in">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-base font-semibold text-ink-900">
                    {selected.title}
                  </h2>
                  <button
                    onClick={() => setSelectedId(null)}
                    aria-label="Clear selection"
                    className="rounded p-1 text-ink-400 hover:bg-ink-50 hover:text-ink-600"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {selected.tags.map((t) => (
                    <TagPill key={t} tag={t} />
                  ))}
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-2 text-center">
                  <div className="rounded-lg bg-ink-50 p-2">
                    <dt className="text-[11px] text-ink-400">Links out</dt>
                    <dd className="text-lg font-bold text-ink-900">
                      {selected.out_degree}
                    </dd>
                  </div>
                  <div className="rounded-lg bg-ink-50 p-2">
                    <dt className="text-[11px] text-ink-400">Backlinks</dt>
                    <dd className="text-lg font-bold text-ink-900">
                      {selected.in_degree}
                    </dd>
                  </div>
                </dl>

                {outbound.length > 0 ? (
                  <div className="mt-4">
                    <h3 className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                      <Link2 className="h-3 w-3" /> Links to
                    </h3>
                    <ul className="space-y-1">
                      {outbound.map((t) => (
                        <li key={t}>
                          <button
                            onClick={() => setSelectedId(t)}
                            className="w-full truncate rounded px-1.5 py-1 text-left text-sm text-ink-600 hover:bg-brand-50 hover:text-brand-700"
                          >
                            {graph.nodes.find((n) => n.id === t)?.title ?? t}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {inbound.length > 0 ? (
                  <div className="mt-3">
                    <h3 className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-ink-400">
                      <CornerUpLeft className="h-3 w-3" /> Linked from
                    </h3>
                    <ul className="space-y-1">
                      {inbound.map((s) => (
                        <li key={s}>
                          <button
                            onClick={() => setSelectedId(s)}
                            className="w-full truncate rounded px-1.5 py-1 text-left text-sm text-ink-600 hover:bg-brand-50 hover:text-brand-700"
                          >
                            {graph.nodes.find((n) => n.id === s)?.title ?? s}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <Link
                  href={`/notes/${selected.id}`}
                  className="btn-primary mt-5 w-full"
                >
                  Open note <ArrowUpRight className="h-4 w-4" />
                </Link>
              </div>
            ) : (
              <div className="py-8 text-center">
                <Network className="mx-auto mb-2 h-8 w-8 text-ink-300" />
                <p className="text-sm text-ink-500">
                  Click a node in the graph to see its links and open the note.
                </p>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
