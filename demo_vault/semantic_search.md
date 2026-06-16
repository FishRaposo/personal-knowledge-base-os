---
title: Semantic Search
tags: [search, retrieval, ai]
---

# Semantic Search

Semantic search retrieves notes by meaning rather than exact keywords. It embeds
the query into a vector and ranks note chunks by cosine similarity.

## Pipeline
1. During indexing, each note is split into chunks and embedded (see [[embeddings]]).
2. Vectors are stored in an in-memory store offline, or pgvector when a database
   is configured.
3. At query time the query is embedded and the nearest chunks are returned, then
   rolled up to their parent notes with the best-matching snippet.

Because the offline embeddings are a deterministic hash fallback, results are
reproducible in tests without a model or API key — the same query always returns
the same ranking.

Related: [[search_tips]] | [[embeddings]] | [[chat_with_citations]] #retrieval
