import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EmptyState, ErrorState, Spinner } from "@/components/States";

describe("States", () => {
  it("Spinner shows its label", () => {
    render(<Spinner label="Loading notes…" />);
    expect(screen.getByText("Loading notes…")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("EmptyState renders title and description", () => {
    render(<EmptyState title="Nothing here" description="Try a search" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Try a search")).toBeInTheDocument();
  });

  it("ErrorState renders the message and calls onRetry", async () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Boom" onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Boom")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
