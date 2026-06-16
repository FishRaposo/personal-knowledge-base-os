import Link from "next/link";
import {
  Search,
  Network,
  MessagesSquare,
  Tags,
  ArrowRight,
  FileText,
  Sparkles,
} from "lucide-react";

const FEATURES = [
  {
    href: "/search",
    icon: Search,
    title: "Search",
    body: "Keyword, semantic, or hybrid retrieval over every note with ranked, scored results.",
  },
  {
    href: "/graph",
    icon: Network,
    title: "Graph",
    body: "An interactive force-directed map of your notes and their wikilinks. Click a node to open it.",
  },
  {
    href: "/chat",
    icon: MessagesSquare,
    title: "Chat",
    body: "Ask questions over your notes and get grounded answers with inline source citations.",
  },
  {
    href: "/tags",
    icon: Tags,
    title: "Tags",
    body: "Browse the whole vault by tag, with note counts and quick jump-throughs.",
  },
];

export default function HomePage() {
  return (
    <div className="mx-auto max-w-5xl">
      <section className="rounded-2xl border border-ink-200 bg-gradient-to-br from-white to-brand-50 px-6 py-14 text-center sm:px-12">
        <span className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-white px-3 py-1 text-xs font-medium text-brand-700">
          <Sparkles className="h-3.5 w-3.5" />
          Local-first · offline by default
        </span>
        <h1 className="mb-4 text-4xl font-bold tracking-tight text-ink-900 sm:text-5xl">
          Your second brain,
          <br />
          <span className="text-brand-600">linked and searchable.</span>
        </h1>
        <p className="mx-auto max-w-2xl text-lg text-ink-600">
          A personal knowledge base over a vault of markdown notes — connected by
          wikilinks, mapped as a backlinks graph, and queryable by keyword,
          meaning, or conversation.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/search" className="btn-primary px-6 py-3 text-base">
            <Search className="h-4 w-4" />
            Start searching
          </Link>
          <Link href="/graph" className="btn-secondary px-6 py-3 text-base">
            <Network className="h-4 w-4" />
            Explore the graph
          </Link>
        </div>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2">
        {FEATURES.map(({ href, icon: Icon, title, body }) => (
          <Link
            key={href}
            href={href}
            className="group rounded-xl border border-ink-200 bg-white p-6 shadow-sm transition-all hover:border-brand-300 hover:shadow-md"
          >
            <div className="mb-3 flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
                <Icon className="h-5 w-5" />
              </span>
              <h3 className="text-lg font-semibold text-ink-900">{title}</h3>
              <ArrowRight className="ml-auto h-4 w-4 text-ink-300 transition-transform group-hover:translate-x-1 group-hover:text-brand-600" />
            </div>
            <p className="text-sm leading-relaxed text-ink-600">{body}</p>
          </Link>
        ))}
      </section>

      <section className="mt-10 rounded-xl border border-ink-200 bg-white p-6">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-brand-500" />
          <h2 className="text-lg font-semibold text-ink-900">How it works</h2>
        </div>
        <ol className="mt-4 grid gap-4 text-sm text-ink-600 sm:grid-cols-3">
          <li className="rounded-lg bg-ink-50 p-4">
            <span className="font-semibold text-ink-900">1. Ingest</span>
            <p className="mt-1">
              Plain markdown files are parsed into notes — wikilinks, tags, and
              frontmatter included.
            </p>
          </li>
          <li className="rounded-lg bg-ink-50 p-4">
            <span className="font-semibold text-ink-900">2. Connect</span>
            <p className="mt-1">
              <code className="rounded bg-white px-1 text-brand-700">[[wikilinks]]</code>{" "}
              become a bidirectional backlinks graph you can explore.
            </p>
          </li>
          <li className="rounded-lg bg-ink-50 p-4">
            <span className="font-semibold text-ink-900">3. Retrieve</span>
            <p className="mt-1">
              Search and chat over embedded chunks with grounded, cited answers.
            </p>
          </li>
        </ol>
      </section>
    </div>
  );
}
