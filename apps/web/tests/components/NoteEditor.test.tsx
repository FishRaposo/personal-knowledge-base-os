import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NoteEditor from "@/components/NoteEditor";
import { api } from "@/lib/api";
import type { Note } from "@/types";

const NOTE: Note = { id: "n1", title: "Note", content: "# Before", links: [], tags: [], backlinks: [] };

describe("NoteEditor", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("makes the note editable only after an explicit action", async () => {
    render(<NoteEditor note={NOTE} vaultId="default" onSaved={vi.fn()} />);
    expect(screen.queryByLabelText("Markdown content")).not.toBeInTheDocument();
    await act(async () => { await userEvent.click(screen.getByRole("button", { name: /edit note/i })); });
    expect(screen.getByLabelText("Markdown content")).toHaveValue("# Before");
    expect(screen.getByRole("button", { name: /save safely/i })).toBeVisible();
  });

  it("cancels an open edit when the active vault changes and saves with the loaded vault", async () => {
    const user = userEvent.setup();
    const updateNote = vi.spyOn(api, "updateNote").mockResolvedValue({ data: NOTE, source: "live" });
    const { rerender } = render(<NoteEditor note={NOTE} vaultId="default" onSaved={vi.fn()} />);

    await act(async () => { await user.click(screen.getByRole("button", { name: /edit note/i })); });
    await act(async () => { await user.clear(screen.getByLabelText("Markdown content")); });
    await act(async () => { await user.type(screen.getByLabelText("Markdown content"), "# Unsaved default vault edit"); });

    rerender(<NoteEditor note={NOTE} vaultId="work" onSaved={vi.fn()} />);

    expect(screen.queryByLabelText("Markdown content")).not.toBeInTheDocument();

    await act(async () => { await user.click(screen.getByRole("button", { name: /edit note/i })); });
    await act(async () => { await user.clear(screen.getByLabelText("Markdown content")); });
    await act(async () => { await user.type(screen.getByLabelText("Markdown content"), "# Work vault edit"); });
    await act(async () => { await user.click(screen.getByRole("button", { name: /save safely/i })); });

    expect(updateNote).toHaveBeenCalledWith("n1", { content: "# Work vault edit", vaultId: "work" });
  });
});
