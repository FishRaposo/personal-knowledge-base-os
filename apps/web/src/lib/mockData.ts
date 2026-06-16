// Bundled demo fixtures that mirror the FastAPI backend's responses for the
// default demo vault (apps/api demo_vault). These let every view render fully
// with NO backend running. The search/chat/graph helpers below derive their
// output from this single source of truth so demo mode stays self-consistent.

import type {
  ChatResponse,
  GraphResponse,
  Note,
  SearchMode,
  SearchResult,
  StatsResponse,
  TagRollup,
} from "@/types";

interface RawNote {
  id: string;
  title: string;
  tags: string[];
  content: string;
  links: string[];
}

export const MOCK_NOTES: RawNote[] = [
  {
    id: "getting_started",
    title: "Getting Started",
    tags: ["meta", "onboarding", "start"],
    links: ["notes_architecture", "search_tips", "writing_style", "wikilinks", "local_first"],
    content: `# Getting Started

This is the entry point to your personal knowledge base. A vault is just a folder
of plain markdown files connected by \`[[wikilinks]]\`.

## Core concepts
- [[notes_architecture]] — how notes are organized and stored
- [[search_tips]] — keyword vs. semantic search
- [[writing_style]] — guidelines for writing durable notes
- [[wikilinks]] — how links create a bidirectional graph

## Why local-first?
Your notes live as files on your disk, not locked inside a database. See
[[local_first]] for the philosophy and trade-offs.

Start anywhere and follow the links. The graph will fill in as you write. #start`,
  },
  {
    id: "notes_architecture",
    title: "Note Architecture",
    tags: ["architecture", "design"],
    links: ["wikilinks", "backlinks_graph", "semantic_search", "embeddings", "getting_started", "search_tips"],
    content: `# Note Architecture

Your knowledge base uses plain-text markdown files with \`[[wikilinks]]\` to connect
notes into a graph. Each file is one note; the filename (minus the extension) is
its stable id.

## Structure
- Each \`.md\` file becomes a note with an \`id\`, \`title\`, \`content\`, and \`tags\`.
- \`[[note_title]]\` creates a directed link that the [[backlinks_graph]] reverses
  into a backlink, so every note knows what points at it.
- YAML frontmatter (\`tags\`, \`title\`, \`aliases\`) is parsed for metadata.

## Chunking and embeddings
Notes are split into overlapping chunks and embedded so [[semantic_search]] can
find related ideas even when the words differ. See [[embeddings]] for the offline
hash-fallback vs. real OpenAI embedding paths.

Related: [[getting_started]] | [[search_tips]] | [[backlinks_graph]] #architecture`,
  },
  {
    id: "wikilinks",
    title: "Wikilinks",
    tags: ["meta", "graph", "links"],
    links: ["backlinks_graph", "notes_architecture", "getting_started"],
    content: `# Wikilinks

A wikilink connects one note to another using double brackets: \`[[target]]\`. They
are the edges of your [[backlinks_graph]].

## Syntax
- \`[[notes_architecture]]\` — link by note id or title.
- \`[[notes_architecture|how notes work]]\` — link with display alias; the target
  before the \`|\` is what the graph records.
- Links resolve case- and space-insensitively via slugs.

Type \`[[\` in an editor to get auto-complete suggestions for existing notes.

Related: [[getting_started]] | [[backlinks_graph]] | [[notes_architecture]] #links`,
  },
  {
    id: "backlinks_graph",
    title: "Backlinks Graph",
    tags: ["architecture", "graph"],
    links: ["notes_architecture", "wikilinks", "getting_started"],
    content: `# Backlinks Graph

When note A links to note B with \`[[B]]\`, the graph records a directed edge
A → B. The *backlink* is the reverse view: B should know that A points at it.

## How it works
1. Indexing parses every \`[[wikilink]]\` into an outbound adjacency list.
2. \`get_backlinks(B)\` scans the adjacency list for every source that targets B.
3. \`get_graph()\` exports \`{nodes, edges}\` for a force-directed visualization,
   with in/out degree per node so hubs are easy to spot.

Links are resolved by slug, so \`[[Note Architecture]]\` matches the note whose id
is \`notes_architecture\`.

Related: [[notes_architecture]] | [[wikilinks]] | [[getting_started]] #graph`,
  },
  {
    id: "semantic_search",
    title: "Semantic Search",
    tags: ["search", "retrieval", "ai"],
    links: ["embeddings", "search_tips", "chat_with_citations"],
    content: `# Semantic Search

Semantic search retrieves notes by meaning rather than exact keywords. It embeds
the query into a vector and ranks note chunks by cosine similarity.

## Pipeline
1. During indexing, each note is split into chunks and embedded (see [[embeddings]]).
2. Vectors are stored in an in-memory store offline, or pgvector when a database
   is configured.
3. At query time the query is embedded and the nearest chunks are returned, then
   rolled up to their parent notes with the best-matching snippet.

Because the offline embeddings are a deterministic hash fallback, results are
reproducible in tests without a model or API key — the same query always returns
the same ranking.

Related: [[search_tips]] | [[embeddings]] | [[chat_with_citations]] #retrieval`,
  },
  {
    id: "search_tips",
    title: "Search Tips",
    tags: ["search", "meta", "retrieval"],
    links: ["semantic_search", "embeddings", "getting_started"],
    content: `# Search Tips

There are two complementary ways to find notes: lexical keyword search and
[[semantic_search]]. Hybrid search merges both.

## When to use which
- **Keyword** is transparent and exact — great for jargon, names, and codes.
- **Semantic** finds notes by meaning, even when the wording differs.
- **Hybrid** runs both and de-duplicates, ranking by the stronger signal.

Tip: start broad with semantic, then narrow with a keyword phrase you spotted in
the results. See [[embeddings]] for how the vectors are produced.

Related: [[getting_started]] | [[semantic_search]] #search`,
  },
  {
    id: "embeddings",
    title: "Embeddings",
    tags: ["ai", "retrieval", "infrastructure"],
    links: ["semantic_search", "local_first", "notes_architecture"],
    content: `# Embeddings

An embedding turns a chunk of text into a vector of numbers so similar ideas land
near each other in space. They power [[semantic_search]].

## Two paths
- **Offline (default)** — a deterministic hash-based embedder runs with no API key
  and no network, so the whole stack works fully offline. See [[local_first]].
- **Real** — when an OpenAI key is configured, the indexer calls the embedding
  model and stores the resulting vectors instead.

Either way the [[notes_architecture]] is unchanged: chunks carry an embedding that
the vector store indexes for nearest-neighbour retrieval.

Related: [[semantic_search]] | [[local_first]] #embeddings`,
  },
  {
    id: "local_first",
    title: "Local First",
    tags: ["philosophy", "design", "infrastructure"],
    links: ["getting_started", "notes_architecture"],
    content: `# Local First

Local-first software keeps the source of truth on your own device: plain files you
own, that work offline, and that outlive any single app or vendor.

## Trade-offs
- **Ownership & longevity** — markdown files are readable in 20 years.
- **Offline by default** — the whole system runs with no network or database.
- **Optional persistence** — when a database is configured, notes also persist to
  PostgreSQL so they survive across machines, but the files remain canonical.

This is why ingestion is file-driven and the database is an *additive* cache, not
the primary store. See [[notes_architecture]] for how that shapes the schema.

Related: [[getting_started]] | [[notes_architecture]] #philosophy`,
  },
  {
    id: "writing_style",
    title: "Writing Style",
    tags: ["meta", "onboarding"],
    links: ["getting_started", "wikilinks"],
    content: `# Writing Style

Durable notes are short, atomic, and densely linked. Write one idea per note and
connect it with [[wikilinks]] rather than burying it in a long document.

## Guidelines
- Lead with the idea, not the context.
- Prefer linking to an existing note over repeating yourself.
- Title notes as nouns you would search for later.
- Add a couple of #tags so the [[getting_started]] hubs stay navigable.

Good notes are findable months later — both by keyword and by following links.

Related: [[getting_started]] | [[wikilinks]] #writing`,
  },
  {
    id: "chat_with_citations",
    title: "Chat with Citations",
    tags: ["ai", "retrieval", "chat"],
    links: ["semantic_search", "embeddings"],
    content: `# Chat with Citations

Chat answers a question over your notes and grounds every claim with an inline
\`[n]\` citation that points back at the source note.

## How it works
1. The question is embedded and the top notes are retrieved via [[semantic_search]].
2. Those notes become the only context the model is allowed to use.
3. The answer carries \`[1]\`, \`[2]\` markers and a citation grounding score, so you
   can verify each statement against its source.

Offline, a deterministic simulated answer stitches the retrieved snippets together;
with an API key configured, a real model composes the response instead.

Related: [[semantic_search]] | [[embeddings]] #chat`,
  },
];

const NOTE_INDEX: Record<string, RawNote> = Object.fromEntries(
  MOCK_NOTES.map((n) => [n.id, n])
);

const TITLE_OF = (id: string): string => NOTE_INDEX[id]?.title ?? id;

function snippetOf(note: RawNote): string {
  const body = note.content.replace(/^#.*\n/, "").trim();
  return body.slice(0, 280);
}

// ---- Backlinks ----
export function mockBacklinks(id: string): string[] {
  return MOCK_NOTES.filter((n) => n.links.includes(id))
    .map((n) => n.id)
    .sort();
}

// ---- Single note (GET /notes/{id}) ----
export function mockNote(id: string): Note | null {
  const raw = NOTE_INDEX[id];
  if (!raw) return null;
  return {
    id: raw.id,
    title: raw.title,
    content: raw.content,
    source: `${raw.id}.md`,
    links: raw.links,
    tags: raw.tags,
    metadata: { title: raw.title, tags: raw.tags },
    word_count: raw.content.split(/\s+/).length,
    backlinks: mockBacklinks(raw.id),
  };
}

export function mockNoteIds(): string[] {
  return MOCK_NOTES.map((n) => n.id);
}

// ---- Graph (GET /graph) ----
export function mockGraph(): GraphResponse {
  const inDegree: Record<string, number> = Object.fromEntries(
    MOCK_NOTES.map((n) => [n.id, 0])
  );
  const edges: { source: string; target: string }[] = [];
  for (const n of MOCK_NOTES) {
    for (const target of n.links) {
      edges.push({ source: n.id, target });
      if (target in inDegree) inDegree[target] += 1;
    }
  }
  const nodes = MOCK_NOTES.map((n) => ({
    id: n.id,
    title: n.title,
    tags: n.tags,
    out_degree: n.links.length,
    in_degree: inDegree[n.id] ?? 0,
  })).sort((a, b) => a.id.localeCompare(b.id));
  edges.sort((a, b) =>
    a.source === b.source ? a.target.localeCompare(b.target) : a.source.localeCompare(b.source)
  );
  return { nodes, edges };
}

// ---- Tags (GET /tags) ----
export function mockTags(): TagRollup[] {
  const counts: Record<string, number> = {};
  const notesByTag: Record<string, string[]> = {};
  for (const n of MOCK_NOTES) {
    for (const tag of n.tags) {
      counts[tag] = (counts[tag] ?? 0) + 1;
      (notesByTag[tag] ??= []).push(n.id);
    }
  }
  return Object.keys(counts)
    .sort()
    .map((tag) => ({ tag, count: counts[tag], notes: notesByTag[tag] }));
}

// ---- Stats (GET /stats) ----
export function mockStats(): StatsResponse {
  return {
    total_notes: MOCK_NOTES.length,
    total_chunks: MOCK_NOTES.length, // one chunk per short demo note
    total_tags: mockTags().length,
  };
}

// ---- Search (GET /notes/search) ----
function keywordScore(note: RawNote, query: string): number {
  const q = query.toLowerCase().trim();
  if (!q) return 0;
  const words = q.split(/\s+/).filter(Boolean);
  const title = note.title.toLowerCase();
  const content = note.content.toLowerCase();
  const tags = note.tags.map((t) => t.toLowerCase());
  let score = 0;
  if (q === title) score += 100;
  else if (title.includes(q)) score += 50;
  score += occurrences(content, q) * 2;
  for (const w of words) {
    if (title.includes(w)) score += 5;
    if (tags.includes(w)) score += 8;
    score += occurrences(content, w);
  }
  return score;
}

function occurrences(haystack: string, needle: string): number {
  if (!needle) return 0;
  let count = 0;
  let idx = haystack.indexOf(needle);
  while (idx !== -1) {
    count += 1;
    idx = haystack.indexOf(needle, idx + needle.length);
  }
  return count;
}

// Deterministic "semantic" proxy for demo mode: token-overlap similarity with a
// tag boost, normalized to 0..1 so it reads like a cosine score.
function semanticScore(note: RawNote, query: string): number {
  const q = new Set(
    query
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((w) => w.length > 2)
  );
  if (q.size === 0) return 0;
  const text = `${note.title} ${note.content} ${note.tags.join(" ")}`.toLowerCase();
  const tokens = new Set(text.split(/[^a-z0-9]+/).filter((w) => w.length > 2));
  let overlap = 0;
  q.forEach((w) => {
    if (tokens.has(w)) overlap += 1;
  });
  let tagBoost = 0;
  q.forEach((w) => {
    if (note.tags.some((t) => t.toLowerCase().includes(w))) tagBoost += 0.15;
  });
  const base = overlap / q.size;
  return Math.min(1, base * 0.7 + tagBoost + (base > 0 ? 0.12 : 0));
}

function toResult(note: RawNote, score: number, match: "keyword" | "semantic"): SearchResult {
  return {
    id: note.id,
    title: note.title,
    snippet: snippetOf(note),
    content: note.content,
    tags: note.tags,
    links: note.links,
    score: match === "semantic" ? Number(score.toFixed(4)) : score,
    match_type: match,
  };
}

export function mockSearch(
  query: string,
  limit: number,
  mode: SearchMode
): SearchResult[] {
  if (!query.trim()) return [];
  if (mode === "keyword") {
    return MOCK_NOTES.map((n) => ({ n, s: keywordScore(n, query) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, limit)
      .map((x) => toResult(x.n, x.s, "keyword"));
  }
  if (mode === "semantic") {
    return MOCK_NOTES.map((n) => ({ n, s: semanticScore(n, query) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, limit)
      .map((x) => toResult(x.n, x.s, "semantic"));
  }
  // hybrid: keyword first, then fill from semantic, de-duplicated by id.
  const merged = new Map<string, SearchResult>();
  for (const r of mockSearch(query, limit, "keyword")) merged.set(r.id, r);
  for (const r of mockSearch(query, limit, "semantic")) {
    if (!merged.has(r.id)) merged.set(r.id, r);
  }
  return Array.from(merged.values())
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

// ---- Chat (POST /notes/chat) ----
export function mockChat(query: string, limit = 3): ChatResponse {
  const retrieved = mockSearch(query, limit, "semantic").length
    ? mockSearch(query, limit, "semantic")
    : mockSearch(query, limit, "keyword");

  if (retrieved.length === 0) {
    return {
      answer: "I don't have any notes that address that question.",
      citations: [],
      grounded: false,
      citation_score: 0,
      model: "none",
      mode: "refusal",
    };
  }

  const citations = retrieved.map((r, i) => ({
    index: i + 1,
    id: r.id,
    title: r.title,
    snippet: r.snippet,
    score: r.score,
  }));

  const parts = [`Based on your notes, here is what relates to '${query}':`];
  for (const c of citations) {
    let s = c.snippet.trim().replace(/\n/g, " ");
    if (s.length > 160) s = `${s.slice(0, 160).trimEnd()}…`;
    parts.push(`${s} [${c.index}]`);
  }

  return {
    answer: parts.join(" "),
    citations,
    grounded: true,
    citation_score: 1,
    model: "simulated",
    mode: "simulated",
  };
}

export { TITLE_OF as titleOf };
