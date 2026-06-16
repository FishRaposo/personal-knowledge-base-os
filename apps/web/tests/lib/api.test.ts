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
});
