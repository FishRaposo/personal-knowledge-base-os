"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CornerUpLeft,
  Link2,
  FileText,
  AlignLeft,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Note } from "@/types";
import { titleOf } from "@/lib/mockData";
import NoteMarkdown from "@/components/NoteMarkdown";
import TagPill from "@/components/TagPill";
import DemoBadge from "@/components/DemoBadge";
import { ErrorState, Spinner } from "@/components/States";

export default function NoteView({ id }: { id: string }) {
  const [note, setNote] = useState<Note | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [demo, setDemo] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNotFound(false);
    try {
      const { data, source } = await api.getNote(id);
      setNote(data);
      setDemo(source === "demo");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNotFound(true);
      } else {
        setError((err as Error).message);
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <Spinner label="Loading note…" />;

  if (notFound) {
    return (
      <div className="mx-auto max-w-2xl text-center">
        <div className="rounded-xl border border-ink-200 bg-white p-10">
          <FileText className="mx-auto mb-3 h-10 w-10 text-ink-300" />
          <h2 className="text-lg font-semibold text-ink-900">Note not found</h2>
          <p className="mt-1 text-sm text-ink-500">
            No note exists with id{" "}
            <code className="rounded bg-ink-100 px-1.5 py-0.5 text-brand-700">
              {id}
            </code>
            .
          </p>
          <Link href="/search" className="btn-secondary mt-5">
            <ArrowLeft className="h-4 w-4" />
            Back to search
          </Link>
        </div>
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!note) return null;

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <Link
          href="/search"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-500 hover:text-brand-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
        {demo ? <DemoBadge /> : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <article className="rounded-xl border border-ink-200 bg-white p-6 sm:p-8">
          <header className="mb-6 border-b border-ink-100 pb-5">
            <h1 className="text-2xl font-bold tracking-tight text-ink-900">
              {note.title}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {note.tags.length > 0 ? (
                note.tags.map((tag) => (
                  <TagPill key={tag} tag={tag} href={`/tags?tag=${tag}`} />
                ))
              ) : (
                <span className="text-xs text-ink-400">No tags</span>
              )}
              {typeof note.word_count === "number" ? (
                <span className="chip-muted ml-1">
                  <AlignLeft className="h-3 w-3" />
                  {note.word_count} words
                </span>
              ) : null}
            </div>
          </header>
          <NoteMarkdown content={note.content} />
        </article>

        <aside className="space-y-5">
          <section
            data-testid="outbound-links"
            className="rounded-xl border border-ink-200 bg-white p-4"
          >
            <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">
              <Link2 className="h-3.5 w-3.5" />
              Links out ({note.links.length})
            </h2>
            {note.links.length > 0 ? (
              <ul className="space-y-1.5">
                {note.links.map((target) => (
                  <li key={target}>
                    <Link
                      href={`/notes/${target}`}
                      className="block truncate rounded-md px-2 py-1.5 text-sm text-ink-700 transition-colors hover:bg-brand-50 hover:text-brand-700"
                    >
                      {titleOf(target)}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-ink-400">This note links to nothing yet.</p>
            )}
          </section>

          <section
            data-testid="backlinks"
            className="rounded-xl border border-ink-200 bg-white p-4"
          >
            <h2 className="mb-3 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ink-500">
              <CornerUpLeft className="h-3.5 w-3.5" />
              Backlinks ({note.backlinks.length})
            </h2>
            {note.backlinks.length > 0 ? (
              <ul className="space-y-1.5">
                {note.backlinks.map((src) => (
                  <li key={src}>
                    <Link
                      href={`/notes/${src}`}
                      className="block truncate rounded-md px-2 py-1.5 text-sm text-ink-700 transition-colors hover:bg-brand-50 hover:text-brand-700"
                    >
                      {titleOf(src)}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-ink-400">
                No other notes link here yet.
              </p>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
