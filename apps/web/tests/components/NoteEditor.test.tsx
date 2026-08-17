import { describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NoteEditor from "@/components/NoteEditor";
import type { Note } from "@/types";

const NOTE: Note = { id: "n1", title: "Note", content: "# Before", links: [], tags: [], backlinks: [] };

describe("NoteEditor", () => {
  it("makes the note editable only after an explicit action", async () => {
    render(<NoteEditor note={NOTE} onSaved={vi.fn()} />);
    expect(screen.queryByLabelText("Markdown content")).not.toBeInTheDocument();
    await act(async () => { await userEvent.click(screen.getByRole("button", { name: /edit note/i })); });
    expect(screen.getByLabelText("Markdown content")).toHaveValue("# Before");
    expect(screen.getByRole("button", { name: /save safely/i })).toBeVisible();
  });
});
