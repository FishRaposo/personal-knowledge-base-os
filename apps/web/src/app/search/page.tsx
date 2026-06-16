"use client";

import { useCallback, useEffect, useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { SearchMode, SearchResult } from "@/types";
import SearchResultCard from "@/components/SearchResultCard";
import DemoBadge from "@/components/DemoBadge";
import { EmptyState, ErrorState, ListSkeleton } from "@/components/States";

const MODES: { value: SearchMode; label: string; hint: string }[] = [
  { value: "keyword", label: "Keyword", hint: "Exact lexical matches" },
  { value: "semantic", label: "Semantic", hint: "Search by meaning" },
  { value: "hybrid", label: "Hybrid", hint: "Best of both" },
];

const SUGGESTIONS = ["wikilinks", "semantic search", "local first", "embeddings"];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<SearchMode>("keyword");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [demo, setDemo] = useState(false);
  const [submitted, setSubmitted] = useState("");

  const runSearch = useCallback(async (q: string, m: SearchMode) => {
    if (!q.trim()) return;
    setLoading(true);
    setError(null);
    setSubmitted(q);
    try {
      const { data, source } = await api.search(q, m, 10);
      setResults(data.results);
      setDemo(source === "demo");
    } catch (err) {
      setError((err as Error).message);
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Re-run when the mode changes after an initial search.
  useEffect(() => {
    if (submitted) runSearch(submitted, mode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-ink-900">Search</h1>
        <p className="mt-1 text-sm text-ink-500">
          Find notes by keyword, semantic similarity, or a hybrid of both.
        </p>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          runSearch(query, mode);
        }}
        className="rounded-xl border border-ink-200 bg-white p-4 shadow-sm"
      >
        <div className="flex items-center gap-2 rounded-lg border border-ink-200 bg-ink-50 px-3 focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-100">
          <SearchIcon className="h-5 w-5 text-ink-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your notes…"
            aria-label="Search query"
            className="w-full bg-transparent py-2.5 text-sm text-ink-900 outline-none placeholder:text-ink-400"
          />
          <button type="submit" className="btn-primary shrink-0">
            Search
          </button>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-ink-400">Mode:</span>
          <div className="inline-flex rounded-lg border border-ink-200 bg-ink-50 p-0.5">
            {MODES.map((m) => (
              <button
                key={m.value}
                type="button"
                title={m.hint}
                onClick={() => setMode(m.value)}
                className={clsx(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  mode === m.value
                    ? "bg-white text-brand-700 shadow-sm"
                    : "text-ink-500 hover:text-ink-800"
                )}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </form>

      {!submitted ? (
        <div className="mt-6">
          <p className="mb-2 text-xs font-medium text-ink-400">Try searching for:</p>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setQuery(s);
                  runSearch(s, mode);
                }}
                className="chip-muted hover:border-brand-300 hover:text-brand-700"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-6">
        {demo && submitted ? <DemoBadge className="mb-4" /> : null}

        {loading ? (
          <ListSkeleton count={4} />
        ) : error ? (
          <ErrorState message={error} onRetry={() => runSearch(submitted, mode)} />
        ) : results && submitted ? (
          results.length === 0 ? (
            <EmptyState
              title="No matching notes"
              description={`Nothing matched "${submitted}" in ${mode} mode. Try a different term or switch modes.`}
              icon={<SearchIcon className="h-10 w-10" />}
            />
          ) : (
            <div className="space-y-3" data-testid="results-list">
              <p className="text-sm text-ink-500">
                {results.length} result{results.length === 1 ? "" : "s"} for{" "}
                <span className="font-medium text-ink-700">&ldquo;{submitted}&rdquo;</span>
              </p>
              {results.map((r, i) => (
                <SearchResultCard key={r.id} result={r} rank={i + 1} />
              ))}
            </div>
          )
        ) : null}
      </div>
    </div>
  );
}
