import type {
  BacklinksResponse,
  ChatRequest,
  ChatResponse,
  GraphResponse,
  Note,
  Flashcard,
  FlashcardsResponse,
  SavedSearch,
  SavedSearchesResponse,
  SearchMode,
  SearchResponse,
  SourcedResult,
  StatsResponse,
  TagsResponse,
  VaultsResponse,
  WatcherStatus,
} from "@/types";
import {
  mockChat,
  mockGraph,
  mockNote,
  mockSearch,
  mockStats,
  mockTags,
  mockBacklinks,
  mockFlashcards,
  mockSavedSearches,
  mockVaults,
  mockWatcherStatus,
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

type BackendFlashcard = Partial<Flashcard> & {
  question?: string;
  answer?: string;
  citation?: { note_id?: string; source?: string };
  review?: { interval_days?: number; due_in_days?: number };
};

function normalizeFlashcard(card: BackendFlashcard): Flashcard {
  return {
    id: String(card.id ?? ""),
    vault_id: String(card.vault_id ?? "default"),
    front: String(card.front ?? card.question ?? ""),
    back: String(card.back ?? card.answer ?? ""),
    note_id: String(card.note_id ?? card.citation?.note_id ?? ""),
    citations:
      card.citations ?? (card.citation?.source ? [card.citation.source] : []),
    interval_days: card.interval_days ?? card.review?.interval_days,
    due_at: card.due_at,
  };
}

export const api = {
  async search(
    q: string,
    mode: SearchMode = "keyword",
    limit = 10,
    options: { vaultId?: string; tag?: string } = {}
  ): Promise<SourcedResult<SearchResponse>> {
    const params = new URLSearchParams({
      q,
      mode,
      limit: String(limit),
    });
    if (options.vaultId) params.set("vault_id", options.vaultId);
    if (options.tag) params.set("tags", options.tag);
    return liveOrDemo(
      () => rawRequest<SearchResponse>(`/notes/search?${params}`),
      () => {
        const results = mockSearch(q, limit, mode);
        return { query: q, mode, results, total: results.length };
      }
    );
  },

  async getNote(id: string, vaultId = "default"): Promise<SourcedResult<Note>> {
    return liveOrDemo(
      () => rawRequest<Note>(`/notes/${encodeURIComponent(id)}?vault_id=${encodeURIComponent(vaultId)}`),
      () => {
        const note = mockNote(id);
        if (!note) throw new ApiError(`Note '${id}' not found`, 404);
        return note;
      }
    );
  },

  async getVaults(): Promise<SourcedResult<VaultsResponse>> {
    return liveOrDemo(() => rawRequest<VaultsResponse>("/vaults"), mockVaults);
  },

  async updateNote(
    id: string,
    input: { content: string; vaultId?: string }
  ): Promise<SourcedResult<Note>> {
    return liveOrDemo(
      () =>
        rawRequest<Note>(`/notes/${encodeURIComponent(id)}`, {
          method: "PATCH",
          body: JSON.stringify({ content: input.content, vault_id: input.vaultId ?? "default" }),
        }),
      () => {
        const note = mockNote(id);
        if (!note) throw new ApiError(`Note '${id}' not found`, 404);
        return { ...note, content: input.content };
      }
    );
  },

  async getSavedSearches(vaultId = "default"): Promise<SourcedResult<SavedSearchesResponse>> {
    return liveOrDemo(
      async () => {
        const raw = await rawRequest<{ saved_searches: SavedSearch[] }>(`/saved-searches?vault_id=${encodeURIComponent(vaultId)}`);
        return { searches: raw.saved_searches };
      },
      mockSavedSearches
    );
  },

  async saveSearch(input: Omit<SavedSearch, "id">): Promise<SourcedResult<SavedSearch>> {
    return liveOrDemo(
      () => rawRequest<SavedSearch>("/saved-searches", { method: "POST", body: JSON.stringify(input) }),
      () => ({ ...input, id: `demo-${input.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}` })
    );
  },

  async getFlashcards(vaultId = "default"): Promise<SourcedResult<FlashcardsResponse>> {
    return liveOrDemo(
      async () => {
        const raw = await rawRequest<{ cards: BackendFlashcard[] }>(`/flashcards?vault_id=${encodeURIComponent(vaultId)}`);
        return { flashcards: raw.cards.map(normalizeFlashcard) };
      },
      mockFlashcards
    );
  },

  async generateFlashcards(vaultId = "default", noteId?: string): Promise<SourcedResult<FlashcardsResponse>> {
    return liveOrDemo(
      async () => {
        const raw = await rawRequest<{ cards: BackendFlashcard[] }>("/flashcards/generate", { method: "POST", body: JSON.stringify({ vault_id: vaultId, note_id: noteId }) });
        return { flashcards: raw.cards.map(normalizeFlashcard) };
      },
      mockFlashcards
    );
  },

  async reviewFlashcard(id: string, vaultId = "default", rating = 3): Promise<SourcedResult<unknown>> {
    return liveOrDemo(
      () => rawRequest<unknown>(`/flashcards/${encodeURIComponent(id)}/review`, { method: "POST", body: JSON.stringify({ vault_id: vaultId, rating }) }),
      () => ({ id, vault_id: vaultId, rating })
    );
  },

  async getWatcher(vaultId = "default"): Promise<SourcedResult<WatcherStatus>> {
    return liveOrDemo(
      () => rawRequest<WatcherStatus>(`/watchers/${encodeURIComponent(vaultId)}`),
      () => mockWatcherStatus(vaultId)
    );
  },

  async setWatcher(vaultId = "default", running: boolean): Promise<SourcedResult<WatcherStatus>> {
    const action = running ? "start" : "stop";
    return liveOrDemo(
      () => rawRequest<WatcherStatus>(`/watchers/${encodeURIComponent(vaultId)}/${action}`, { method: "POST" }),
      () => ({ ...mockWatcherStatus(vaultId), running })
    );
  },

  async getBacklinks(id: string, vaultId = "default"): Promise<SourcedResult<BacklinksResponse>> {
    return liveOrDemo(
      () =>
        rawRequest<BacklinksResponse>(
          `/notes/${encodeURIComponent(id)}/backlinks?vault_id=${encodeURIComponent(vaultId)}`
        ),
      () => ({ note_id: id, backlinks: mockBacklinks(id) })
    );
  },

  async getGraph(vaultId = "default"): Promise<SourcedResult<GraphResponse>> {
    return liveOrDemo(
      () => rawRequest<GraphResponse>(`/graph?vault_id=${encodeURIComponent(vaultId)}`),
      () => mockGraph()
    );
  },

  async getTags(vaultId = "default"): Promise<SourcedResult<TagsResponse>> {
    return liveOrDemo(
      () => rawRequest<TagsResponse>(`/tags?vault_id=${encodeURIComponent(vaultId)}`),
      () => ({ tags: mockTags() })
    );
  },

  async getStats(vaultId = "default"): Promise<SourcedResult<StatsResponse>> {
    return liveOrDemo(
      () => rawRequest<StatsResponse>(`/stats?vault_id=${encodeURIComponent(vaultId)}`),
      () => mockStats()
    );
  },

  async chat(req: ChatRequest & { vaultId?: string }): Promise<SourcedResult<ChatResponse>> {
    return liveOrDemo(
      () =>
        rawRequest<ChatResponse>(`/notes/chat`, {
          method: "POST",
          body: JSON.stringify({ query: req.query, limit: req.limit ?? 3, vault_id: req.vaultId ?? "default" }),
        }),
      () => mockChat(req.query, req.limit ?? 3)
    );
  },
};
