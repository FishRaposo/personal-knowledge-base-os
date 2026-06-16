# Security — Personal Knowledge Base OS

Trust boundaries, input validation, and secret handling for the service.

---

## 1. Filesystem access (`/notes/index`)

The most sensitive surface: `/notes/index` takes a directory `path` and reads
files from it.

- **Current safeguards**:
  - Only `.md` / `.markdown` files are opened; other files are skipped.
  - Files are decoded with `errors="replace"`, so malformed content cannot crash
    the process.
  - A missing or empty vault returns a `400 VALIDATION_ERROR`, not a 500.
- **Recommended hardening (before exposing to untrusted callers)**:
  - Resolve the input to an absolute path (`os.path.abspath`) and verify it is
    inside an allow-listed vault root.
  - Reject any path containing `..` traversal sequences.
  - Enforce a max file size (e.g. 5 MB) and a recursion-depth cap to bound memory.
- **Deployment note**: Run the API process under a least-privilege user whose
  filesystem permissions are limited to the vault directory.

---

## 2. No code execution from content

- The indexer performs read-only file operations. It never executes shell
  commands, evaluates note content, or spawns subprocesses based on file names or
  bodies.
- Frontmatter is parsed with a minimal, dependency-free key/value reader — no
  arbitrary YAML object construction.

---

## 3. Secrets

- API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) and the database/Redis URLs are
  read from the environment / `.env` via `shared_core.config` (`SecretStr` for
  keys). They are never hard-coded.
- Secrets are unwrapped only at the call site that needs them (embeddings, LLM) and
  are not logged. The default configuration uses no keys at all.

---

## 4. Database & storage

- The relational store holds note content and JSON embeddings. If a vault contains
  private material, configure encryption-at-rest on the PostgreSQL volume.
- The DB connection uses `pool_pre_ping` and bounded pool sizes from
  `shared_core`; credentials come from `DATABASE_URL`.

---

## 5. Transport & API surface

- The service emits structured logs with a per-request correlation id
  (`RequestLoggingMiddleware`) for auditability.
- Errors are returned as structured JSON via the shared error handler (no stack
  traces leak to clients).
- CORS and authentication are intentionally **not** configured for the local-first
  default. Before any networked deployment, add an auth layer (the API is designed
  to sit behind a gateway) and restrict CORS origins via `CORS_ALLOWED_ORIGINS`.

---

## 6. Denial of service

- Indexing is bounded by the `.md`-only filter today. For multi-tenant or public
  exposure, move indexing to the Celery worker (job id returned immediately) and
  add rate limiting (`shared_core.ratelimit`) and the file-size/depth caps above.
