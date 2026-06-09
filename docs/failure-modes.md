# Failure Modes & Mitigation - Personal Knowledge Base OS

This document details anticipated failure modes, detection strategies, and mitigation pathways for the Personal Knowledge Base OS.

---

## 1. Directory Traversal / Arbitrary Path Reads

- **Cause**: The API `/notes/index?path=...` accepts a query string specifying a folder. If unvalidated, a client can input root system directories (e.g., `C:\` or `/etc`) to read system files.
- **Impact**: Exposure of sensitive host configuration files, environment variables, or private directories.
- **Detection**:
  - API receives request paths containing parent traversal sequences or system folders.
  - Logs show unauthorized directory access attempts.
- **Mitigation**: Resolve target path to an absolute path and verify it lies within a designated root user sandbox directory (e.g., a designated `vaults/` directory). Reject any path parameters containing double dots `..`.
- **Future Fix**: Enforce sandbox boundaries at the operating system or container layer, restricting file access permissions of the FastAPI process.

---

## 2. Text Encoding & Binary File Crashes

- **Cause**: A markdown directory contains non-UTF-8 files (e.g., encoded in UTF-16, ISO-8859-1) or binary attachments (like `.png` or `.pdf` files renamed or placed in the folder).
- **Impact**: The indexer throws `UnicodeDecodeError` when executing `f.read()`, crashing the ingestion routine and returning HTTP 500.
- **Detection**:
  - Ingestion halts with `UnicodeDecodeError` in trace logs.
  - API responses return 500 status codes on specific folders.
- **Mitigation**: The indexer file-open call utilizes `errors="ignore"` or `errors="replace"` parameter on `open()` to prevent decoding exceptions from halting execution.
- **Future Fix**: Add mime-type checkers that filter out non-text files and implement encoding detection (using libraries like `chardet`) before reading file bytes.

---

## 3. Worker Starvation via Large Directory Ingestion

- **Cause**: A user requests indexing on a massive directory containing tens of thousands of files (e.g., the user's home folder or `node_modules`).
- **Impact**: The single-threaded synchronous file read operation blocks the FastAPI worker thread, causing the server to hang and leading to gateway timeouts on all other API requests.
- **Detection**:
  - Response latency spikes.
  - Uvicorn server logs timeouts.
- **Mitigation**: Filter folder listing to include only files ending with `.md`, avoiding parsing non-markdown files.
- **Future Fix**: Implement asynchronous file reads utilizing `aiofiles` or offload directory parsing to Celery background workers (`worker.py`), returning an execution job ID immediately.

---

## 4. Broken/Dangling Wikilinks

- **Cause**: Notes contain wikilinks to notes that do not exist (e.g., `[[Missing Note]]`).
- **Impact**: The backlinks graph registers outgoing edges to nodes that have no matching content or source files.
- **Detection**: Adjacency lists contain target nodes that are missing from the primary notes index list.
- **Mitigation**: The graph builder creates blank nodes for missing link targets in the adjacency list, preventing key errors when querying backlinks.
- **Future Fix**: Flag dangling links in the API response so frontend applications can render them as dashed or colored red nodes to alert users of broken links.
