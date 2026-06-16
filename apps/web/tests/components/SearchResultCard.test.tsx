import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SearchResultCard from "@/components/SearchResultCard";
import type { SearchResult } from "@/types";

const result: SearchResult = {
  id: "semantic_search",
  title: "Semantic Search",
  snippet: "Semantic search retrieves notes by meaning rather than exact keywords.",
  content: "full content here",
  tags: ["search", "retrieval", "ai"],
  links: ["embeddings", "search_tips"],
  score: 0.81,
  match_type: "semantic",
};

describe("SearchResultCard", () => {
  it("renders title, rank, and snippet", () => {
    render(<SearchResultCard result={result} rank={1} />);
    expect(screen.getByText("Semantic Search")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(
      screen.getByText(/retrieves notes by meaning/i)
    ).toBeInTheDocument();
  });

  it("renders the semantic score as a percentage", () => {
    render(<SearchResultCard result={result} rank={1} />);
    expect(screen.getByText("81%")).toBeInTheDocument();
  });

  it("links to the note viewer", () => {
    render(<SearchResultCard result={result} rank={2} />);
    expect(screen.getByTestId("search-result")).toHaveAttribute(
      "href",
      "/notes/semantic_search"
    );
  });

  it("shows the number of outbound links", () => {
    render(<SearchResultCard result={result} rank={1} />);
    expect(screen.getByText("2 links")).toBeInTheDocument();
  });
});
