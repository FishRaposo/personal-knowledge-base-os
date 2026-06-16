---
title: Search Tips
tags: [search, usage]
---

# Search Tips

The knowledge base supports keyword, semantic, and hybrid search.

## Keyword search
Matches exact terms in note titles, content, and tags. Title matches and tag hits
are weighted higher than body-frequency matches, so the most on-topic note rises
to the top.

## Semantic search
Finds related content by *meaning*, even when the exact words don't appear. It
embeds your query and compares it against the chunk vectors built during indexing.
See [[semantic_search]] and [[embeddings]] for how the vectors are produced.

## Hybrid search
Runs both and merges the results, de-duplicated by note. Good default when you are
not sure whether you remember the exact wording.

## Chat
[[chat_with_citations]] retrieves the most relevant chunks and answers with inline
`[n]` citations so every claim is traceable back to a note.

Links: [[getting_started]] | [[notes_architecture]] #search
