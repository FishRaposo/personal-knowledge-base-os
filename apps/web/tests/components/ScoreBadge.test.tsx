import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ScoreBadge from "@/components/ScoreBadge";

describe("ScoreBadge", () => {
  it("renders a semantic score as a percentage", () => {
    render(<ScoreBadge score={0.92} matchType="semantic" />);
    expect(screen.getByText("92%")).toBeInTheDocument();
  });

  it("uses a green tone for high semantic scores", () => {
    const { container } = render(<ScoreBadge score={0.85} matchType="semantic" />);
    expect(container.querySelector(".text-green-600")).toBeInTheDocument();
  });

  it("uses a red tone for low semantic scores", () => {
    const { container } = render(<ScoreBadge score={0.2} matchType="semantic" />);
    expect(container.querySelector(".text-red-600")).toBeInTheDocument();
  });

  it("renders keyword scores with a kw prefix", () => {
    render(<ScoreBadge score={42} matchType="keyword" />);
    expect(screen.getByText("kw 42")).toBeInTheDocument();
  });
});
