---
title: Local First
tags: [philosophy, design, infrastructure]
---

# Local First

Local-first software keeps the source of truth on your own device: plain files you
own, that work offline, and that outlive any single app or vendor.

## Trade-offs
- **Ownership & longevity** — markdown files are readable in 20 years.
- **Offline by default** — the whole system runs with no network or database.
- **Optional persistence** — when a database is configured, notes also persist to
  PostgreSQL so they survive across machines, but the files remain canonical.

This is why ingestion is file-driven and the database is an *additive* cache, not
the primary store. See [[notes_architecture]] for how that shapes the schema.

Related: [[getting_started]] | [[notes_architecture]] #philosophy
