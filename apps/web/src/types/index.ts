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
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
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
