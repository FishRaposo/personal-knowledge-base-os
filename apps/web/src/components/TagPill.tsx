import Link from "next/link";
import { Hash } from "lucide-react";

export default function TagPill({
  tag,
  count,
  href,
}: {
  tag: string;
  count?: number;
  href?: string;
}) {
  const inner = (
    <span className="chip" data-testid="tag-pill">
      <Hash className="h-3 w-3" />
      {tag}
      {typeof count === "number" ? (
        <span className="ml-0.5 rounded-full bg-brand-100 px-1.5 text-[10px] font-semibold text-brand-700">
          {count}
        </span>
      ) : null}
    </span>
  );
  if (href) {
    return (
      <Link href={href} className="transition-opacity hover:opacity-80">
        {inner}
      </Link>
    );
  }
  return inner;
}
