# Key Technical Decisions - Personal Knowledge Base OS

This document outlines the architectural and technical decisions made for the Personal Knowledge Base OS.

---

## 1. Monorepo Directory Layout (`apps/api/src/`)

- **Decision**: Organize the project structure using a monorepo pattern (`apps/api/` for the backend, leaving space for a future `apps/web/` frontend) rather than a single flat repository layout.
- **Rationale**: A personal knowledge base requires a high-fidelity visual interface (such as a 3D force-directed network graph). Placing the API within a sub-folder isolates Python environment configurations from node/React dependencies, keeping frontend and backend concerns modular.

---

## 2. In-Memory Graph Compilation (`graph.py`)

- **Decision**: Perform note parsing and adjacency mapping dynamically in memory on request rather than reading/writing link tables from PostgreSQL database entries during indexing.
- **Rationale**: Local markdown directories change frequently. Compiling the graph dynamically avoids synchronization issues between the file system and the database, ensuring that file edits on disk are immediately reflected in the API response.
- **Trade-offs**: Graph compilation scales linearly with directory size. For large note vaults (>10,000 notes), parsing files on every request becomes slow. Future designs will require caching indices in Redis or storing them in a graph-relational database.

---

## 3. Obsidian-Compatible Wikilink Regex Parsing (`indexer.py`)

- **Decision**: Parse connections using wikilink double-bracket regex syntax (`r'\[\[(.*?)\]\]'`) instead of standard Markdown links (`[text](url)`).
- **Rationale**: The wikilink syntax is the standard connection format used by modern personal knowledge base platforms (Obsidian, Logseq, Roam Research). Compatibility with this syntax allows users to point this service to their existing markdown vaults without modification.
- **Trade-offs**: Standard Markdown link syntaxes are ignored. Future updates will require a hybrid parsing pipeline supporting both standard markdown links and wikilink syntax.

---

## 4. File-Name Based Title Mapping (`indexer.py`)

- **Decision**: Resolve a note's primary key/title from its file name (e.g., `Ideas.md` -> Title: `"Ideas"`) rather than requiring a YAML frontmatter `title` attribute.
- **Rationale**: Simplifies note creation. Users don't need to write metadata blocks at the top of every file to participate in the backlinks network graph.
