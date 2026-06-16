import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import DemoBadge, { DemoWriteNotice } from "@/components/DemoBadge";

describe("DemoBadge", () => {
  it("renders the demo-mode indicator", () => {
    render(<DemoBadge />);
    expect(screen.getByTestId("demo-badge")).toBeInTheDocument();
    expect(screen.getByText(/demo mode/i)).toBeInTheDocument();
  });

  it("write notice explains the action was not persisted", () => {
    render(<DemoWriteNotice />);
    expect(screen.getByTestId("demo-write-notice")).toBeInTheDocument();
    expect(screen.getByText(/not persisted/i)).toBeInTheDocument();
  });
});
