import Link from "next/link";
import { FileText, ArrowRight, Link2 } from "lucide-react";
import type { SearchResult } from "@/types";
import ScoreBadge from "@/components/ScoreBadge";
import TagPill from "@/components/TagPill";

export default function SearchResultCard({
  result,
  rank,
}: {
  result: SearchResult;
  rank: number;
}) {
  return (
    <Link
      href={`/notes/${result.id}`}
      data-testid="search-result"
      className="group block rounded-xl border border-ink-200 bg-white p-5 shadow-sm transition-all hover:border-brand-300 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink-100 text-xs font-semibold text-ink-500">
            {rank}
          </span>
          <FileText className="h-4 w-4 shrink-0 text-brand-500" />
          <h3 className="truncate text-base font-semibold text-ink-900 group-hover:text-brand-700">
            {result.title}
          </h3>
        </div>
        <ScoreBadge score={result.score} matchType={result.match_type} />
      </div>

      <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-ink-600">
        {result.snippet}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {result.tags.slice(0, 4).map((tag) => (
          <TagPill key={tag} tag={tag} />
        ))}
        {result.links.length > 0 ? (
          <span className="chip-muted">
            <Link2 className="h-3 w-3" />
            {result.links.length} link{result.links.length === 1 ? "" : "s"}
          </span>
        ) : null}
        <span className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-brand-600 opacity-0 transition-opacity group-hover:opacity-100">
          Open note <ArrowRight className="h-3 w-3" />
        </span>
      </div>
    </Link>
  );
}
