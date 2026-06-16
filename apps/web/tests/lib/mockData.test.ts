import { describe, it, expect } from "vitest";
import {
  mockSearch,
  mockChat,
  mockGraph,
  mockTags,
  mockNote,
  mockBacklinks,
  mockStats,
} from "@/lib/mockData";

describe("mockData", () => {
  it("keyword search ranks an exact title match first", () => {
    const results = mockSearch("wikilinks", 10, "keyword");
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].id).toBe("wikilinks");
    expect(results[0].match_type).toBe("keyword");
  });

  it("semantic search returns scored results in 0..1", () => {
    const results = mockSearch("search by meaning", 5, "semantic");
    expect(results.length).toBeGreaterThan(0);
    for (const r of results) {
      expect(r.match_type).toBe("semantic");
      expect(r.score).toBeGreaterThanOrEqual(0);
      expect(r.score).toBeLessThanOrEqual(1);
    }
  });

  it("hybrid search de-duplicates by note id", () => {
    const results = mockSearch("semantic search", 10, "hybrid");
    const ids = results.map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("empty query yields no results", () => {
    expect(mockSearch("   ", 5, "keyword")).toHaveLength(0);
  });

  it("graph nodes and edges are internally consistent", () => {
    const graph = mockGraph();
    expect(graph.nodes.length).toBeGreaterThan(0);
    const ids = new Set(graph.nodes.map((n) => n.id));
    for (const e of graph.edges) {
      expect(ids.has(e.source)).toBe(true);
    }
    // in_degree on a node should equal edges targeting it
    const node = graph.nodes.find((n) => n.id === "getting_started")!;
    const incoming = graph.edges.filter((e) => e.target === "getting_started").length;
    expect(node.in_degree).toBe(incoming);
  });

  it("tags rollup counts notes per tag", () => {
    const tags = mockTags();
    const arch = tags.find((t) => t.tag === "architecture");
    expect(arch).toBeTruthy();
    expect(arch!.count).toBe(arch!.notes.length);
  });

  it("note includes backlinks derived from other notes", () => {
    const note = mockNote("backlinks_graph");
    expect(note).not.toBeNull();
    expect(note!.title).toBe("Backlinks Graph");
    expect(note!.backlinks).toContain("wikilinks");
  });

  it("backlinks are symmetric with outbound links", () => {
    // wikilinks links to backlinks_graph, so backlinks_graph's backlinks include wikilinks
    expect(mockBacklinks("backlinks_graph")).toContain("wikilinks");
  });

  it("unknown note id returns null", () => {
    expect(mockNote("does_not_exist")).toBeNull();
  });

  it("chat returns a grounded answer with citations", () => {
    const res = mockChat("how do wikilinks work?", 3);
    expect(res.citations.length).toBeGreaterThan(0);
    expect(res.answer).toMatch(/\[1\]/);
    expect(res.grounded).toBe(true);
    expect(res.mode).toBe("simulated");
  });

  it("stats reflect the number of notes and tags", () => {
    const stats = mockStats();
    expect(stats.total_notes).toBeGreaterThan(0);
    expect(stats.total_tags).toBe(mockTags().length);
  });
});
