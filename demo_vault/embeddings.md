---
title: Embeddings
tags: [ai, retrieval, infrastructure]
---

# Embeddings

An embedding turns text into a vector so similar meanings sit close together in
vector space. This vault uses two interchangeable providers from `shared_core`.

## Offline (default)
A deterministic SHA-256 hash fallback produces stable 384-dimensional vectors with
no API key, no network, and no heavy ML dependency. This keeps the demo and the
test suite fully reproducible.

## Real (when keyed)
When `OPENAI_API_KEY` is set, the same interface calls OpenAI's
`text-embedding-3-small` endpoint instead — no code changes at the call sites.

The vectors feed [[semantic_search]] and [[chat_with_citations]].

Related: [[semantic_search]] | [[notes_architecture]] #ai
