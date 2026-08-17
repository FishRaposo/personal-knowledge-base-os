# Failure Modes & Mitigations — Personal Knowledge Base OS

## Offline dependency unavailable

**Database, Redis, broker, provider SDK, or network is unavailable.** The normal local path continues with in-memory/SQLite-compatible stores, deterministic hash embeddings, and simulated cited chat. Celery modules are importable without a broker. PostgreSQL/pgvector, Redis, Celery workers, OpenAI/Anthropic, watchdog, OCR, and heavy parsers are optional integrations, not offline pass criteria.

## Invalid vault path or unsafe edit

**A caller supplies a path outside the configured vault, a symlink, binary/null content, or an oversized edit.** Indexing and editing reject it as a validation error. The engine checks configured-root containment and every extant symlink component; note edits are UTF-8 text and limited to 2 MiB. The service opens Markdown files only and does not execute note content. A local filesystem boundary is not a replacement for authentication before a networked deployment.

## Incremental indexing or watcher failure

**A Markdown file is added, changed, removed, unreadable, or parsing fails.** Full indexing remains the legacy default. Incremental indexing compares deterministic content-hash snapshots and returns added/changed/deleted IDs. A failure publishes `index_failed` without masking the request error. The explicit polling watcher publishes `note_changed`, uses the same incremental service, and emits `watcher_stopped` when stopped or an unrecoverable loop failure occurs.

## Dangling links

**A wikilink points to no indexed note.** Graph export retains its legacy `{nodes, edges}` surface and attaches additive unresolved/dangling metadata. The source note, backlinks, search, and chat remain usable; the dashboard can distinguish the missing target rather than failing graph traversal.

## SSE client disconnect or missed event

**An SSE client reconnects after a transient failure.** Event IDs are monotonic, bounded, and vault-scoped. Clients can supply `Last-Event-ID`/`last_event_id` to `/events`, or use `/events/replay` as a polling fallback. Heartbeats keep an idle stream observable. The buffer is local and bounded, so a client that falls beyond its retained window must refresh state.

## Provider failure or poor semantic quality

**A keyed provider is missing, errors, or returns unusable output.** Embedding and chat paths fall back to deterministic local behavior where the existing response contract permits it. Offline embeddings are intentionally stable but less semantically capable than a real model; this is a product boundary, not hidden quality equivalence. Golden fixtures pin deterministic ranking and citation behavior.

## Persistence restart boundary

**The process restarts in default offline mode.** Process-local vault registrations, watchers, events, saved searches, cards, and reviews do not claim durable distributed persistence. The additive schema defines durable records for configured database adapters; SQLite/in-memory mode preserves service-level scoping during a running process. Users who require restart persistence should configure and verify their chosen database adapter.
