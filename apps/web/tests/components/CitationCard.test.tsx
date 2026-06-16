import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CitationCard from "@/components/CitationCard";
import type { Citation } from "@/types";

const citation: Citation = {
  index: 1,
  id: "wikilinks",
  title: "Wikilinks",
  snippet: "A wikilink connects one note to another using double brackets.",
  score: 0.74,
};

describe("CitationCard", () => {
  it("renders the citation index, title, and snippet", () => {
    render(<CitationCard citation={citation} />);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("Wikilinks")).toBeInTheDocument();
    expect(screen.getByText(/double brackets/i)).toBeInTheDocument();
  });

  it("links to the cited note", () => {
    render(<CitationCard citation={citation} />);
    expect(screen.getByTestId("citation-card")).toHaveAttribute(
      "href",
      "/notes/wikilinks"
    );
  });

  it("renders the score as a percentage", () => {
    render(<CitationCard citation={citation} />);
    expect(screen.getByText("74%")).toBeInTheDocument();
  });
});
