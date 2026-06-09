# Security Boundaries & Rules - Personal Knowledge Base OS

This document outlines the security parameters, directory trust boundaries, and input validation rules for the Personal Knowledge Base OS.

---

## 1. Directory Traversal Safeguards

- **Strict Sandbox Validation**: The indexer must validate the requested path string before attempting any directory listing or file read operation:
  - Resolve the input path to its canonical, absolute representation (`os.path.abspath`).
  - Verify that the resolved path is located within an explicitly approved workspace root directory.
- **Traversal String Rejection**: Any path parameters containing path traversal sequences (such as `..` or `\..`) must immediately fail validation.

---

## 2. Ingest Verification & Sandbox Execution

- **Text-Only Ingestion**: The indexer must restrict file opening to plain-text `.md` extensions.
- **No Command Spawning**: Ingest routines must perform only basic file system read operations. The system must not execute shell commands, parse scripts, or spawn sub-processes based on file names or contents.
- **Resource Exhaustion Limits**: Enforce maximum file size limits (e.g., 5MB per note) and recursion depth limits when indexing folders, to protect memory against zip-bomb style nested directory trees.

---

## 3. Storage and Database Security

- **Database Credentials**: PostgreSQL connection configurations must be stored securely in the local environment and not hardcoded.
- **Data Encryption**: If local user vaults contain sensitive credentials or private diaries, vector index databases must be configured to encrypt table volumes on disk.
