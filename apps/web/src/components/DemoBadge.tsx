import { FlaskConical } from "lucide-react";

/**
 * Visible indicator shown whenever a view is rendering bundled demo fixtures
 * instead of live API data (because the backend was unreachable).
 */
export default function DemoBadge({ className = "" }: { className?: string }) {
  return (
    <span
      data-testid="demo-badge"
      className={`inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800 ${className}`}
    >
      <FlaskConical className="h-3.5 w-3.5" />
      Demo mode — bundled sample data
    </span>
  );
}

/**
 * Inline notice for write actions (e.g. chat) when running against demo data:
 * the action ran locally and was not persisted to a backend.
 */
export function DemoWriteNotice({ className = "" }: { className?: string }) {
  return (
    <p
      data-testid="demo-write-notice"
      className={`text-xs text-amber-700 ${className}`}
    >
      Demo — this response was generated locally and not persisted.
    </p>
  );
}
