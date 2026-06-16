---
title: Chat With Citations
tags: [ai, rag, retrieval]
---

# Chat With Citations

Chat answers a question using only your notes, with inline `[n]` citation markers
so every claim is traceable. This is retrieval-augmented generation (RAG) scoped
to a personal vault.

## Flow
1. The question is embedded and the most relevant chunks are retrieved via
   [[semantic_search]].
2. The retrieved chunks become numbered context `[1] [2] [3]`.
3. Offline, a deterministic answer stitches the snippets with their markers; when
   an API key is present, a real LLM answers from the same grounded prompt.
4. The answer's citation grounding is *scored* with a citation judge, so we can
   assert the response actually cites its sources.

If no notes are relevant, chat refuses rather than hallucinating.

Related: [[semantic_search]] | [[search_tips]] | [[embeddings]] #rag
