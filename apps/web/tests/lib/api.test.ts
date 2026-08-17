import { describe, it, expect, vi, afterEach } from "vitest";
import { api, ApiError } from "@/lib/api";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("returns live data when the backend responds", async () => {
    const payload = {
      query: "x",
      mode: "keyword",
      results: [
        {
          id: "n1",
          title: "Live Note",
          snippet: "s",
          content: "c",
          tags: [],
          links: [],
          score: 5,
          match_type: "keyword",
        },
      ],
      total: 1,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify(payload), { status: 200 }))
    );

    const { data, source } = await api.search("x", "keyword");
    expect(source).toBe("live");
    expect(data.results[0].title).toBe("Live Note");
  });

  it("falls back to demo data on a network error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      })
    );

    const { data, source } = await api.search("wikilinks", "keyword");
    expect(source).toBe("demo");
    expect(data.results.length).toBeGreaterThan(0);
    expect(data.results[0].id).toBe("wikilinks");
  });

  it("surfaces a real 4xx as an ApiError (not masked by demo)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: "Note 'x' not found" }), {
            status: 404,
          })
      )
    );

    await expect(api.getNote("x")).rejects.toBeInstanceOf(ApiError);
  });

  it("graph falls back to a demo graph offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      })
    );
    const { data, source } = await api.getGraph();
    expect(source).toBe("demo");
    expect(data.nodes.length).toBeGreaterThan(0);
    expect(data.edges.length).toBeGreaterThan(0);
  });

  it("chat falls back to a simulated demo answer offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      })
    );
    const { data, source } = await api.chat({ query: "what is local first?" });
    expect(source).toBe("demo");
    expect(data.citations.length).toBeGreaterThan(0);
  });

  it("scopes new retrieval calls to the selected vault and tag without changing legacy search", async () => {
    const response = {
      query: "offline",
      mode: "hybrid",
      results: [],
      total: 0,
    };
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify(response), { status: 200 })
    );
    vi.stubGlobal("fetch", fetchMock);

    await api.search("offline", "hybrid", 5, { vaultId: "work", tag: "ops" });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("vault_id=work"),
      expect.anything()
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("tags=ops"),
      expect.anything()
    );
  });

  it("keeps vault, note-edit, saved-search, and flashcard actions usable offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      })
    );

    await expect(api.getVaults()).resolves.toMatchObject({ source: "demo" });
    await expect(
      api.updateNote("wikilinks", { content: "# Wikilinks\nUpdated", vaultId: "default" })
    ).resolves.toMatchObject({ source: "demo" });
    await expect(api.getSavedSearches("default")).resolves.toMatchObject({ source: "demo" });
    await expect(api.getFlashcards("default")).resolves.toMatchObject({ source: "demo" });
  });

  it("normalizes additive backend response keys and exact paths", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.includes("saved-searches")) return new Response(JSON.stringify({ saved_searches: [] }), { status: 200 });
      if (url.includes("flashcards")) return new Response(JSON.stringify({ cards: [] }), { status: 200 });
      return new Response(JSON.stringify({ vault_id: "default", running: false }), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.getSavedSearches()).resolves.toMatchObject({ data: { searches: [] } });
    await expect(api.getFlashcards()).resolves.toMatchObject({ data: { flashcards: [] } });
    await api.getWatcher("default");
    expect(fetchMock.mock.calls.map(([url]) => String(url))).toContain("http://localhost:8000/watchers/default");
  });
});
