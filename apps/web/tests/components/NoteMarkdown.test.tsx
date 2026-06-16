import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import NoteMarkdown from "@/components/NoteMarkdown";

describe("NoteMarkdown", () => {
  it("renders markdown headings and text", () => {
    render(<NoteMarkdown content={"# Title\n\nSome **bold** body."} />);
    expect(screen.getByRole("heading", { name: "Title" })).toBeInTheDocument();
    expect(screen.getByText("bold")).toBeInTheDocument();
  });

  it("converts [[wikilinks]] into note links", () => {
    render(<NoteMarkdown content={"See [[Note Architecture]] for details."} />);
    const link = screen.getByRole("link", { name: "Note Architecture" });
    expect(link).toHaveAttribute("href", "/notes/note_architecture");
  });

  it("respects wikilink aliases and keeps the target slug", () => {
    render(<NoteMarkdown content={"Read [[notes_architecture|how notes work]]."} />);
    const link = screen.getByRole("link", { name: "how notes work" });
    expect(link).toHaveAttribute("href", "/notes/notes_architecture");
  });
});
