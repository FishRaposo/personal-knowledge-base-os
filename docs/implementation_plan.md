# Implementation Plan - Personal Knowledge Base OS

This document details the step-by-step technical implementation plan and development milestones for **Personal Knowledge Base OS**.

---

## 1. Project Goal
A local-first note vault indexing engine that compiles backlinks graphs, performs semantic search, and provides query interfaces for personal knowledge maps.

---

## 2. Architecture & Component Map

The repository is structured as a standalone project conforming to operator workspace standards. The core module responsibilities are mapped below:

### 2.1 File Map & Responsibilities
* **`apps/api/src/indexer.py`**: Scans directory vaults, extracts wikilinks, and indexes metadata tags.
* **`apps/api/src/graph.py`**: Constructs note adjacency maps and resolves backlinks list dynamically.
* **`apps/api/src/search.py`**: Exposes semantic vector queries using pgvector against note contents.
* **`apps/api/src/main.py`**: FastAPI server exposing endpoints to Next.js notes interfaces.

### 2.2 Shared Core Dependencies
This service imports standard layers from `shared-core` (sibling dependency library):
* `shared_core.config.BaseAppConfig`: Settings parsing, reading configs from `.env`.
* `shared_core.database.DatabaseManager`: SQL database engine instantiation and session factories.
* `shared_core.redis.RedisManager`: Caching connections and health checks.
* `shared_core.logging.setup_logging`: Structured log formats and correlation ID tracing.
* `shared_core.errors.BaseApplicationError`: Exception mapping and global handlers.

---

## 3. Database Schema & Data Models

### 3.1 Data Schema
PostgreSQL (pgvector): `notes` (id, title, content, path_hash, updated_at, embedding_vector: vector(1536)), `links` (id, source_note_id, target_note_id).
Redis: Cache index mappings and active directory watch mappings.

### 3.2 Redis Storage & Caching Patterns
* Caching: Utilizing `@cache` decorator with prefix keys.
* Concurrency: Lock critical tasks using `RedisLock` context managers.

---

## 4. Step-by-Step Implementation Sequence

The project development checklist is ordered into six milestones:

- `[ ]` **Milestone 1 (Design): Design directory file indexer, wikilink regex extraction, and backlink calculations.**
- `[ ]` **Milestone 2 (Skeleton): Scaffold apps/api folder structures, setup FastAPI routes, and create pgvector connection.**
- `[ ]` **Milestone 3 (Core Loop): Build notes directory file indexer and backlinks compiler.**
- `[ ]` **Milestone 4 (Reliability): Handle deleted files, broken wikilink pathways, and filesystem permission locks.**
- `[ ]` **Milestone 5 (Showcase): Ingest a sample markdown notes vault, generate graph models, and chat with notes.**
- `[ ]` **Milestone 6 (Publish): Document wiki syntax compatibility, graph scaling bounds, and Next.js visual configurations.**

---

## 5. Standard Makefile & Developer Commands

```bash
make install          # Set up virtual environment and local editable package
make dev              # Boot the microservice API server locally
make test             # Run local pytest / jest test suites
make lint             # Execute Ruff checks / ESLint verifications
make format           # Standardize style formatting
make typecheck        # Verify static types (Pyright / TypeScript)
make docker-up        # Spawn isolated local PostgreSQL and Redis service containers
make docker-down      # Teardown the isolated local containers stack
make demo             # Execute the runnable demo workflow
make clean            # Remove caches and temporary files
```

---

## 6. Verification & Testing Plan

### 6.1 Automated Tests
* **Core Logic Verification**: Tests for regex link matching, backlinks reversal mapping, directory index caching, and missing file exception handlers.
* **Type Safety & Style**: Run `make typecheck` and `make lint` as a pipeline validation hook.
* **Mock Environments**: Utilize `MockDatabase` and `MockRedisClient` inside `tests/conftest.py` to assert correct lifecycle transactions without depending on live network services.

### 6.2 Manual Verification
* Deploy local PostgreSQL and Redis containers with `make docker-up`.
* Execute the runnable script demo `make demo` and review Loguru stdout records.
