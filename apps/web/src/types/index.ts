// Types mirror the FastAPI response shapes in apps/api/src.

export type SearchMode = "keyword" | "semantic" | "hybrid";

export interface SearchResult {
  id: string;
  title: string;
  snippet: string;
  content: string;
  tags: string[];
  links: string[];
  score: number;
  match_type: "keyword" | "semantic";
}

export interface SearchResponse {
  query: string;
  mode: SearchMode;
  results: SearchResult[];
  total: number;
}

export interface NoteChunk {
  id: string;
  note_id: string;
  index: number;
  content: string;
  content_hash?: string;
  embedding?: number[] | null;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  source?: string;
  links: string[];
  tags: string[];
  metadata?: Record<string, unknown>;
  content_hash?: string;
  word_count?: number;
  chunks?: NoteChunk[];
  backlinks: string[];
}

export interface BacklinksResponse {
  note_id: string;
  backlinks: string[];
}

export interface GraphNode {
  id: string;
  title: string;
  tags: string[];
  out_degree: number;
  in_degree: number;
  /** Additive metadata: unresolved wikilinks are never rendered as graph nodes. */
  dangling_links?: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Vault {
  id: string;
  name: string;
  path?: string;
}

export interface VaultsResponse {
  vaults: Vault[];
  selected?: string;
}

export interface SavedSearch {
  id: string;
  name: string;
  query: string;
  mode?: SearchMode;
  tags?: string[];
  vault_id: string;
}

export interface SavedSearchesResponse {
  searches: SavedSearch[];
}

export interface Flashcard {
  id: string;
  front: string;
  back: string;
  note_id: string;
  citations?: string[];
  due_at?: string;
  interval_days?: number;
  vault_id: string;
}

export interface FlashcardsResponse {
  flashcards: Flashcard[];
}

export interface WatcherStatus {
  vault_id: string;
  running: boolean;
  backend?: "polling" | "watchdog" | string;
}

export interface LiveEvent {
  id: string;
  event:
    | "index_started"
    | "note_changed"
    | "index_completed"
    | "index_failed"
    | "watcher_started"
    | "watcher_stopped";
  data: Record<string, unknown>;
}

export interface TagRollup {
  tag: string;
  count: number;
  notes: string[];
}

export interface TagsResponse {
  tags: TagRollup[];
}

export interface Citation {
  index: number;
  id: string;
  title: string;
  snippet: string;
  score: number | null;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  grounded: boolean;
  citation_score: number;
  model: string;
  mode: "simulated" | "llm" | "refusal";
}

export interface ChatRequest {
  query: string;
  limit?: number;
}

export interface StatsResponse {
  total_notes: number;
  total_chunks: number;
  total_tags: number;
}

// A response is wrapped so the UI knows whether it came from the live API or
// the bundled demo fixtures (and therefore should show a "Demo mode" banner).
export interface SourcedResult<T> {
  data: T;
  source: "live" | "demo";
}
