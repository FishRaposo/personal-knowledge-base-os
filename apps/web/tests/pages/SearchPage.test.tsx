import { describe, it, expect, vi, afterEach } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SearchPage from "@/app/search/page";

// next/navigation is not available in jsdom; SearchPage does not use it, but the
// graph/tags pages do. Keep this file focused on Search.

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("SearchPage (demo mode, no backend)", () => {
  it("renders results and a demo badge when the backend is offline", async () => {
    // Force the api client into its demo fallback path.
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      })
    );

    render(<SearchPage />);

    const input = screen.getByLabelText("Search query");
    await act(async () => {
      await userEvent.type(input, "wikilinks");
      await userEvent.click(screen.getByRole("button", { name: "Search" }));
    });

    await waitFor(() =>
      expect(screen.getByTestId("results-list")).toBeInTheDocument()
    );

    expect(screen.getByTestId("demo-badge")).toBeInTheDocument();
    expect(screen.getAllByTestId("search-result").length).toBeGreaterThan(0);
    expect(screen.getByText("Wikilinks")).toBeInTheDocument();
  });

  it("shows suggestion chips before any search", () => {
    render(<SearchPage />);
    expect(screen.getByText("Try searching for:")).toBeInTheDocument();
  });
});
