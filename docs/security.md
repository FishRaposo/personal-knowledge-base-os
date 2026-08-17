# Security — Personal Knowledge Base OS

## Filesystem trust boundary

The index and edit surfaces operate only in configured vault roots. A non-default vault must be registered first; an explicit indexing path must equal that vault root. The service rejects path escapes and every existing symlink component before indexing or writing. It parses `.md` and `.markdown` files, keeps decoding failures controlled, and rejects null-containing or over-2 MiB note edits.

These are enforced local containment controls. They do not establish user identity, authorization, or a hosted multi-tenant boundary. Do not expose this API to untrusted networks without an authentication layer, least-privilege filesystem permissions, and appropriately restricted CORS/gateway policy.

## Content handling

Markdown and frontmatter are data only. The indexer does not evaluate note content, execute shell commands, or load arbitrary code. Watchers use a standard-library polling loop; starting one is an explicit API action, never an application-start side effect.

## Events and metadata

SSE data is vault-scoped and bounded in memory. Event payloads use normalized metadata appropriate for dashboard state, not secrets or provider responses. A reconnect cursor may replay retained events; stale cursors must reload current state. Do not treat replay as an audit ledger.

## Secrets and optional integrations

Provider keys and service URLs are read through `apps.api.src.internal.vendor_core.config`; no key is committed or logged by default. OpenAI/Anthropic, PostgreSQL/pgvector, Redis, Celery, watchdog, and heavy parsing/model dependencies are optional extras. A missing provider must not turn the default demo into a network-backed flow.

## Persistence and operations

For private vaults, secure the host filesystem and configure encryption/backups appropriate to the selected database. The local in-memory fallback intentionally does not persist across restarts. Production deployment must independently verify database backup/recovery, provider credentials, transport security, rate limits, access control, and tenant isolation; none are claimed by the offline evidence bundle.
