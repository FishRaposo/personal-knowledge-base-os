# Failure Modes & Mitigations — Personal Knowledge Base OS

Anticipated failure modes, how they are detected, and how the service handles
them today (vs. future hardening).

---

## 1. Database unavailable

- **Cause**: No PostgreSQL is running (the default offline case), or it goes down
  mid-operation.
- **Impact (mitigated)**: None to availability. `db.py` does a fast ~0.25s TCP
  pre-check plus `SELECT 1`; on failure the service uses `InMemoryNoteStore` and an
  in-memory vector store. The API, worker, demo, and tests all run with no DB.
- **Detection**: A logged "Database unreachable — using in-memory note store"
  line; `/health` reports `database: offline`.
- **Cost**: Notes are not persisted across restarts in the offline path. This is
  by design for the local-first default.

---

## 2. No API key (embeddings / LLM)

- **Cause**: `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` are unset.
- **Impact (mitigated)**: None. Embeddings fall back to the deterministic hash
  provider; chat composes a simulated, citation-bearing answer. Both are
  reproducible.
- **Detection**: Chat responses report `mode: simulated` and `model: simulated`.
- **Future**: Surface a capability flag in `/stats` so a dashboard can show
  whether real providers are active.

---

## 3. LLM call fails or SDK missing (keyed path)

- **Cause**: A key is configured but the `openai`/`anthropic` SDK is not installed,
  or the API call errors/times out.
- **Impact (mitigated)**: The request never crashes. `chat.py` catches
  `ImportError` and generic exceptions, logs them, and falls back to the simulated
  answer — mirroring the `llm-cost-latency-monitor` SDK pattern.
- **Detection**: A warning/error log line; the response still returns `grounded`
  with a simulated answer.

---

## 4. Directory traversal / arbitrary path reads

- **Cause**: `/notes/index` accepts a `path`. An attacker could point it at system
  directories.
- **Impact**: Potential read of files outside an intended vault root.
- **Current**: The indexer only opens `.md`/`.markdown` files and tolerates decode
  errors, limiting blast radius; an empty/missing path yields a 400.
- **Future fix**: Resolve to an absolute path and enforce an allow-listed vault
  root, rejecting `..` sequences. See `security.md`.

---

## 5. Non-UTF-8 or binary files in the vault

- **Cause**: UTF-16/Latin-1 files or binaries (`.png` renamed to `.md`).
- **Impact (mitigated)**: No crash. The markdown parser decodes with
  `errors="replace"`, so a bad file degrades to replacement characters rather than
  raising `UnicodeDecodeError`.
- **Future fix**: MIME sniffing + a max-file-size guard to skip binaries entirely.

---

## 6. Large vault blocks the request thread

- **Cause**: Indexing a very large directory synchronously in the request handler.
- **Impact**: Latency spikes / timeouts on concurrent requests.
- **Current**: Only `.md`/`.markdown` files are read; the Celery worker
  (`kb.index_vault`) exists to offload indexing off the request path.
- **Future fix**: Make `/notes/index` dispatch to the worker and return a job id;
  add async file reads.

---

## 7. Broken / dangling wikilinks

- **Cause**: `[[Missing Note]]` points at a note that does not exist.
- **Impact (mitigated)**: No key errors. The graph records the edge to the
  (unresolved) target; `get_backlinks` still works, and the target simply has no
  node payload.
- **Future fix**: Flag dangling targets in the `/graph` response so a UI can render
  them distinctly.

---

## 8. Embedding / scorer drift

- **Cause**: A future change swaps the embedding provider or citation scorer and
  silently changes rankings or grounding.
- **Impact**: Search results or chat grounding regress without an obvious failure.
- **Mitigation**: Golden tests (`tests/test_golden.py`) pin the offline embedding
  prefix, the `CitationJudge` scores, and the deterministic semantic ranking over
  the demo vault, so drift breaks the build.
