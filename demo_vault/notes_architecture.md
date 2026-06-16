---
title: Note Architecture
tags: [architecture, design]
---

# Note Architecture

Your knowledge base uses plain-text markdown files with `[[wikilinks]]` to connect
notes into a graph. Each file is one note; the filename (minus the extension) is
its stable id.

## Structure
- Each `.md` file becomes a note with an `id`, `title`, `content`, and `tags`.
- `[[note_title]]` creates a directed link that the [[backlinks_graph]] reverses
  into a backlink, so every note knows what points at it.
- YAML frontmatter (`tags`, `title`, `aliases`) is parsed for metadata.

## Chunking and embeddings
Notes are split into overlapping chunks and embedded so [[semantic_search]] can
find related ideas even when the words differ. See [[embeddings]] for the offline
hash-fallback vs. real OpenAI embedding paths.

Related: [[getting_started]] | [[search_tips]] | [[backlinks_graph]] #architecture
