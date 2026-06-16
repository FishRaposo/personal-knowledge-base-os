import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TagPill from "@/components/TagPill";

describe("TagPill", () => {
  it("renders the tag name", () => {
    render(<TagPill tag="architecture" />);
    expect(screen.getByText("architecture")).toBeInTheDocument();
  });

  it("renders a count when provided", () => {
    render(<TagPill tag="graph" count={3} />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("wraps in a link when href is provided", () => {
    render(<TagPill tag="meta" href="/tags?tag=meta" />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/tags?tag=meta");
  });
});
