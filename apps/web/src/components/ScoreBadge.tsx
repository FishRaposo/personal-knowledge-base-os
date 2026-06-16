import clsx from "clsx";

/**
 * Renders a relevance/match score. Semantic scores are 0..1 (shown as a %),
 * keyword scores are raw integers (shown as "kw N"). Colour reflects confidence
 * for semantic scores.
 */
export default function ScoreBadge({
  score,
  matchType,
}: {
  score: number;
  matchType: "keyword" | "semantic";
}) {
  if (matchType === "semantic") {
    const pct = Math.round(Math.max(0, Math.min(1, score)) * 100);
    const tone =
      pct >= 70
        ? "bg-green-50 text-green-600 border-green-200"
        : pct >= 40
          ? "bg-amber-50 text-amber-600 border-amber-200"
          : "bg-red-50 text-red-600 border-red-200";
    return (
      <span
        data-testid="score-badge"
        className={clsx(
          "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold",
          tone
        )}
      >
        {pct}%
      </span>
    );
  }
  return (
    <span
      data-testid="score-badge"
      className="inline-flex items-center rounded-full border border-ink-200 bg-ink-50 px-2 py-0.5 text-xs font-semibold text-ink-600"
    >
      kw {Math.round(score)}
    </span>
  );
}
