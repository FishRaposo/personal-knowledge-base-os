# Architectural Design - Personal Knowledge Base OS

This document details the architectural layout, component maps, and dataflow of the Personal Knowledge Base OS API service.

---

## 1. System Overview

The Personal Knowledge Base OS is structured around a decoupled processing model:
1. **Directory Ingestion Layer (`indexer.py`)**: Responsible for file system discovery, file filtering, reading file bytes, and parsing link patterns.
2. **Graph Compilation Layer (`graph.py`)**: Computes directional graph edges and backlinks (incoming nodes).
3. **HTTP Web Layer (`main.py`)**: Serves the REST API interfaces.

---

## 2. Component Diagram

```mermaid
graph TD
    subgraph Client/User
        Request[Request GET /notes/index?path=...]
    end

    subgraph API Service apps/api/src/
        APIServer[main.py] --> Indexer[NotesIndexer indexer.py]
        APIServer --> Graph[BacklinksGraph graph.py]
    end

    subgraph Local Filesystem
        Indexer -->|Read Directory| Files[Markdown Files .md]
    end

    subgraph Infrastructure
        APIServer --> DB[PostgreSQL]
        APIServer --> Redis[Redis]
    end
```

---

## 3. Data Processing Sequence

```mermaid
sequenceDiagram
    participant Client
    participant API as API Server (main.py)
    participant Indexer as NotesIndexer
    participant Graph as BacklinksGraph
    participant Disk as Local Filesystem

    Client->>API: GET /notes/index?path=/my/notes
    API->>Indexer: parse_directory(/my/notes)
    Indexer->>Disk: List Files & filter .md
    Disk-->>Indexer: List of note files
    loop Read Notes
        Indexer->>Disk: Read file content
        Indexer->>Indexer: Extract wikilinks [[Link]]
    end
    Indexer-->>API: List of notes with titles, content, links
    API->>Graph: build_graph(notes)
    loop Map Adjacencies
        Graph->>Graph: Map outgoing links to adjacency list
    end
    Graph-->>API: Adjacency list configuration
    API-->>Client: JSON response (note counts + graph layout)
```

---

## 4. Component Breakdown

### 4.1 Notes Indexer (`indexer.py`)
- **`NotesIndexer`**: Interacts with the filesystem. Reads file contents, strips extensions to resolve note titles, and applies standard regular expression matchers (`r'\[\[(.*?)\]\]'`) to capture wikilinks.

### 4.2 Backlinks Graph (`graph.py`)
- **`BacklinksGraph`**: In-memory graph model. It processes parsed notes, creates nodes for each note title, and inserts links into directed sets.
- **`get_backlinks`**: Reverses directed edges. Iterates through the graph adjacency list, checking which source nodes link to a target node, compiling an incoming links list dynamically.

### 4.3 API Entrypoint (`main.py`)
- **FastAPI**: Runs the web server, maps config schemas from `shared-core`, and registers application exception handlers.
- **Path Parameter Handler**: Calls the indexer and graph compiler, wrapping output into an API response schema.
