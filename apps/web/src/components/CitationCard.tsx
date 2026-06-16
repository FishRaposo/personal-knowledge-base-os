import Link from "next/link";
import { Quote, ArrowUpRight } from "lucide-react";
import type { Citation } from "@/types";

export default function CitationCard({ citation }: { citation: Citation }) {
  return (
    <Link
      href={`/notes/${citation.id}`}
      data-testid="citation-card"
      className="group flex gap-3 rounded-lg border border-ink-200 bg-white p-3 transition-colors hover:border-brand-300 hover:bg-brand-50/40"
    >
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-brand-600 text-xs font-bold text-white">
        {citation.index}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <h4 className="truncate text-sm font-semibold text-ink-900 group-hover:text-brand-700">
            {citation.title}
          </h4>
          <div className="flex shrink-0 items-center gap-2">
            {typeof citation.score === "number" ? (
              <span className="text-[11px] font-medium text-ink-400">
                {Math.round(Math.max(0, Math.min(1, citation.score)) * 100)}%
              </span>
            ) : null}
            <ArrowUpRight className="h-3.5 w-3.5 text-ink-400 group-hover:text-brand-600" />
          </div>
        </div>
        <p className="mt-1 flex gap-1.5 text-xs leading-relaxed text-ink-500">
          <Quote className="mt-0.5 h-3 w-3 shrink-0 text-ink-300" />
          <span className="line-clamp-2">{citation.snippet}</span>
        </p>
      </div>
    </Link>
  );
}
