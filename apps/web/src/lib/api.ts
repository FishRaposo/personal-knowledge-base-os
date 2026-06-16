import type {
  BacklinksResponse,
  ChatRequest,
  ChatResponse,
  GraphResponse,
  Note,
  SearchMode,
  SearchResponse,
  SourcedResult,
  StatsResponse,
  TagsResponse,
} from "@/types";
import {
  mockChat,
  mockGraph,
  mockNote,
  mockSearch,
  mockStats,
  mockTags,
  mockBacklinks,
} from "@/lib/mockData";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Raised for real HTTP 4xx/5xx responses. These are surfaced to the UI as error
 * states (e.g. a missing note → 404) and are NOT masked by demo fallback — only
 * network/connection failures fall back to bundled demo fixtures.
 */
export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function rawRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...options.headers },
      ...options,
    });
  } catch (err) {
    // Network/connection error (backend down, CORS, DNS). Signal fallback.
    throw new NetworkError((err as Error)?.message || "Network request failed");
  }

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    const detail =
      (body && (body.detail || body.message)) || `API error: ${response.status}`;
    throw new ApiError(String(detail), response.status);
  }

  return response.json() as Promise<T>;
}

/** Thrown when the backend is unreachable; triggers demo-mode fallback. */
export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}

/**
 * Live-first helper: try the real API; on a *network* failure fall back to the
 * provided demo fixture and tag the result as "demo". Real 4xx/5xx (ApiError)
 * propagate so the UI can show a true error state.
 */
async function liveOrDemo<T>(
  live: () => Promise<T>,
  demo: () => T
): Promise<SourcedResult<T>> {
  try {
    const data = await live();
    return { data, source: "live" };
  } catch (err) {
    if (err instanceof NetworkError) {
      return { data: demo(), source: "demo" };
    }
    throw err;
  }
}

export const api = {
  async search(
    q: string,
    mode: SearchMode = "keyword",
    limit = 10
  ): Promise<SourcedResult<SearchResponse>> {
    const params = new URLSearchParams({
      q,
      mode,
      limit: String(limit),
    });
    return liveOrDemo(
      () => rawRequest<SearchResponse>(`/notes/search?${params}`),
      () => {
        const results = mockSearch(q, limit, mode);
        return { query: q, mode, results, total: results.length };
      }
    );
  },

  async getNote(id: string): Promise<SourcedResult<Note>> {
    return liveOrDemo(
      () => rawRequest<Note>(`/notes/${encodeURIComponent(id)}`),
      () => {
        const note = mockNote(id);
        if (!note) throw new ApiError(`Note '${id}' not found`, 404);
        return note;
      }
    );
  },

  async getBacklinks(id: string): Promise<SourcedResult<BacklinksResponse>> {
    return liveOrDemo(
      () =>
        rawRequest<BacklinksResponse>(
          `/notes/${encodeURIComponent(id)}/backlinks`
        ),
      () => ({ note_id: id, backlinks: mockBacklinks(id) })
    );
  },

  async getGraph(): Promise<SourcedResult<GraphResponse>> {
    return liveOrDemo(
      () => rawRequest<GraphResponse>(`/graph`),
      () => mockGraph()
    );
  },

  async getTags(): Promise<SourcedResult<TagsResponse>> {
    return liveOrDemo(
      () => rawRequest<TagsResponse>(`/tags`),
      () => ({ tags: mockTags() })
    );
  },

  async getStats(): Promise<SourcedResult<StatsResponse>> {
    return liveOrDemo(
      () => rawRequest<StatsResponse>(`/stats`),
      () => mockStats()
    );
  },

  async chat(req: ChatRequest): Promise<SourcedResult<ChatResponse>> {
    return liveOrDemo(
      () =>
        rawRequest<ChatResponse>(`/notes/chat`, {
          method: "POST",
          body: JSON.stringify({ query: req.query, limit: req.limit ?? 3 }),
        }),
      () => mockChat(req.query, req.limit ?? 3)
    );
  },
};
