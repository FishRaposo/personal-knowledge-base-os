"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Tags as TagsIcon, Hash, FileText } from "lucide-react";
import clsx from "clsx";
import { api } from "@/lib/api";
import type { TagRollup } from "@/types";
import { titleOf } from "@/lib/mockData";
import DemoBadge from "@/components/DemoBadge";
import { EmptyState, ErrorState, Spinner } from "@/components/States";

function TagsView() {
  const params = useSearchParams();
  const initialTag = params.get("tag");
  const [tags, setTags] = useState<TagRollup[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [demo, setDemo] = useState(false);
  const [active, setActive] = useState<string | null>(initialTag);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data, source } = await api.getTags();
      setTags(data.tags);
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

  useEffect(() => {
    setActive(initialTag);
  }, [initialTag]);

  const maxCount = useMemo(
    () => (tags && tags.length ? Math.max(...tags.map((t) => t.count)) : 1),
    [tags]
  );

  const selected = useMemo(
    () => tags?.find((t) => t.tag === active) ?? null,
    [tags, active]
  );

  return (
    <div className="mx-auto max-w-5xl">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-ink-900">
            <TagsIcon className="h-6 w-6 text-brand-600" />
            Tags
          </h1>
          <p className="mt-1 text-sm text-ink-500">
            Browse the vault by tag. Select one to see the notes it groups.
          </p>
        </div>
        {demo ? <DemoBadge /> : null}
      </header>

      {loading ? (
        <Spinner label="Loading tags…" />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : !tags || tags.length === 0 ? (
        <EmptyState
          title="No tags yet"
          description="Add #hashtags or frontmatter tags to your notes to see them here."
          icon={<Hash className="h-10 w-10" />}
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
          <div className="rounded-xl border border-ink-200 bg-white p-5">
            <h2 className="mb-3 text-sm font-semibold text-ink-700">
              All tags ({tags.length})
            </h2>
            <div className="flex flex-wrap gap-2" data-testid="tag-cloud">
              {tags.map((t) => {
                const scale = 0.85 + (t.count / maxCount) * 0.6;
                const isActive = active === t.tag;
                return (
                  <button
                    key={t.tag}
                    data-testid="tag-cloud-item"
                    onClick={() => setActive(isActive ? null : t.tag)}
                    style={{ fontSize: `${scale}rem` }}
                    className={clsx(
                      "inline-flex items-center gap-1 rounded-full border px-3 py-1 font-medium transition-colors",
                      isActive
                        ? "border-brand-500 bg-brand-600 text-white"
                        : "border-ink-200 bg-ink-50 text-ink-700 hover:border-brand-300 hover:text-brand-700"
                    )}
                  >
                    <Hash className="h-3 w-3 opacity-60" />
                    {t.tag}
                    <span
                      className={clsx(
                        "rounded-full px-1.5 text-[10px] font-semibold",
                        isActive ? "bg-brand-500" : "bg-ink-200 text-ink-600"
                      )}
                    >
                      {t.count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <aside className="rounded-xl border border-ink-200 bg-white p-5">
            {selected ? (
              <div data-testid="tag-notes">
                <h2 className="mb-1 flex items-center gap-1.5 text-base font-semibold text-ink-900">
                  <Hash className="h-4 w-4 text-brand-500" />
                  {selected.tag}
                </h2>
                <p className="mb-3 text-xs text-ink-400">
                  {selected.count} note{selected.count === 1 ? "" : "s"}
                </p>
                <ul className="space-y-1.5">
                  {selected.notes.map((noteId) => (
                    <li key={noteId}>
                      <Link
                        href={`/notes/${noteId}`}
                        className="flex items-center gap-2 rounded-lg border border-ink-100 px-3 py-2 text-sm text-ink-700 transition-colors hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700"
                      >
                        <FileText className="h-3.5 w-3.5 shrink-0 text-brand-400" />
                        <span className="truncate">{titleOf(noteId)}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="py-8 text-center">
                <Hash className="mx-auto mb-2 h-8 w-8 text-ink-300" />
                <p className="text-sm text-ink-500">
                  Select a tag to list its notes.
                </p>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

export default function TagsPage() {
  return (
    <Suspense fallback={<Spinner label="Loading tags…" />}>
      <TagsView />
    </Suspense>
  );
}
