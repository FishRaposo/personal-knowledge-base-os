# Project Roadmap - Personal Knowledge Base OS

This document outlines the milestones and developmental timeline for the Personal Knowledge Base OS.

---

## Milestone 1: Local Ingestion & Graph Core (Completed)
- **Monorepo API Directory**: Establish code boundaries under `apps/api/src/`.
- **Obsidian wikilinks parser**: Support extraction of double-bracketed `[[Wikilink]]` connections.
- **Backlink Solver**: Dynamic generation of bidirectional relationship graphs.
- **Directory Ingestion**: System utilities to parse folder trees.

---

## Milestone 2: 3D Force-Directed Graph UI & YAML Metadata (Planned)
- **Interactive Web Interface**: Initialize `apps/web/` using Next.js and TailwindCSS to render note networks as a responsive, force-directed graph.
- **Node Markdown Editor**: Build a side-panel editor allowing users to select nodes, read note content, and modify files.
- **Frontmatter Meta Parser**: Integrate parsing of YAML metadata blocks (tags, dates, categories) at the top of markdown notes.
- **Dangling Link Highlighting**: Visual indicators on the graph identifying links to non-existent notes.

---

## Milestone 3: Semantic Vector RAG & Real-Time Sync (Future)
- **Semantic Vector Similarity Ingestion**: Use `shared-core` pgvector bindings to store note embeddings. This lets users query similar notes based on topic similarity rather than explicit wiki linkages.
- **Automated Directory Watcher**: Integrate filesystem event hooks (`watchdog` in Python) to trigger graph recompilations automatically when notes are updated, added, or deleted.
- **Episodic Flashcard Generation**: Implement a space-repetition review builder (e.g. Leitner system card generator) leveraging LLMs to generate questions from notes.
- **Multi-Vault Workspace Settings**: Allow switching between multiple isolated workspace note directories.
