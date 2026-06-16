---
title: Backlinks Graph
tags: [architecture, graph]
---

# Backlinks Graph

When note A links to note B with `[[B]]`, the graph records a directed edge
A → B. The *backlink* is the reverse view: B should know that A points at it.

## How it works
1. Indexing parses every `[[wikilink]]` into an outbound adjacency list.
2. `get_backlinks(B)` scans the adjacency list for every source that targets B.
3. `get_graph()` exports `{nodes, edges}` for a force-directed visualization,
   with in/out degree per node so hubs are easy to spot.

Links are resolved by slug, so `[[Note Architecture]]` matches the note whose id
is `notes_architecture`.

Related: [[notes_architecture]] | [[wikilinks]] | [[getting_started]] #graph
