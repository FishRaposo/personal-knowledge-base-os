"""Vector store abstraction: in-memory (offline default) + pgvector (when a DB is set).

Built on ``shared_core.embeddings`` for the similarity math. The in-memory store makes
RAG-style retrieval fully testable with no database; ``PgVectorStore`` persists vectors
in PostgreSQL via the pgvector extension. Both implement the ``VectorStore`` interface,
so consumers (rag-evaluation-lab, document-intelligence-pipeline, personal-knowledge-
base-os, groundtruth, knowledgeops) swap offline/production without code changes.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence

from .embeddings import cosine_similarity

# A SQL identifier that is safe to interpolate into table-name positions.
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


@dataclass
class VectorRecord:
    """A stored vector with an id and arbitrary JSON-able payload."""

    id: str
    vector: list[float]
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class VectorHit:
    """A ranked search result."""

    id: str
    score: float
    payload: dict[str, Any]


class VectorStore(ABC):
    """Minimal vector-store interface."""

    @abstractmethod
    def setup(self) -> None:
        """Prepare the store before use."""

    @abstractmethod
    def add(self, record: VectorRecord) -> None: ...

    def add_many(self, records: Iterable[VectorRecord]) -> None:
        for record in records:
            self.add(record)

    @abstractmethod
    def query(self, vector: Sequence[float], top_k: int = 5) -> list[VectorHit]: ...

    @abstractmethod
    def count(self) -> int: ...

    @abstractmethod
    def clear(self) -> None: ...


class InMemoryVectorStore(VectorStore):
    """In-memory cosine-similarity store — the offline/testing default."""

    def __init__(self) -> None:
        self._records: dict[str, VectorRecord] = {}

    def setup(self) -> None:
        """No-op setup for the offline store."""

    def add(self, record: VectorRecord) -> None:
        self._records[record.id] = record

    def query(self, vector: Sequence[float], top_k: int = 5) -> list[VectorHit]:
        hits = [
            VectorHit(
                id=r.id,
                score=cosine_similarity(vector, r.vector),
                payload=r.payload,
            )
            for r in self._records.values()
        ]
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()


class PgVectorStore(VectorStore):
    """pgvector-backed store (synchronous SQLAlchemy ``DatabaseManager``).

    Creates the ``vector`` extension and a ``{table}`` table on :meth:`setup`. Vectors
    are stored per ``namespace`` so multiple collections can share one table. Cosine
    distance uses the pgvector ``<=>`` operator (score = ``1 - distance``).

    Security: ``table`` is interpolated directly into SQL (identifiers cannot be
    bound as parameters), so it MUST NOT come from untrusted input — it is validated
    against a strict SQL-identifier pattern in ``__init__``. ``namespace`` is always
    passed as a bound parameter, but as a matter of policy neither ``table`` nor
    ``namespace`` should be derived from untrusted user input.
    """

    def __init__(
        self,
        db_manager: Any,
        *,
        dimensions: int,
        table: str = "vectors",
        namespace: str = "default",
    ) -> None:
        if not _IDENTIFIER_RE.fullmatch(table):
            raise ValueError(
                f"Invalid table name {table!r}: must be a valid SQL identifier "
                r"matching [A-Za-z_][A-Za-z0-9_]* (it is interpolated into SQL "
                "and must not be untrusted input)."
            )
        self.db_manager = db_manager
        self.dimensions = dimensions
        self.table = table
        self.namespace = namespace

    def setup(self) -> None:
        """Create the pgvector extension and the storage table (idempotent)."""
        from sqlalchemy import text

        with self.db_manager.SessionLocal() as session:
            session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            session.execute(
                text(
                    f"CREATE TABLE IF NOT EXISTS {self.table} ("
                    "id TEXT, namespace TEXT, "
                    f"embedding vector({self.dimensions}), "
                    "payload JSONB, PRIMARY KEY (namespace, id))"
                )
            )
            session.commit()

    def add(self, record: VectorRecord) -> None:
        import json

        from sqlalchemy import text

        vec = "[" + ",".join(str(float(x)) for x in record.vector) + "]"
        with self.db_manager.SessionLocal() as session:
            session.execute(
                text(
                    f"INSERT INTO {self.table} (id, namespace, embedding, payload) "
                    "VALUES (:id, :ns, :emb, :payload) "
                    "ON CONFLICT (namespace, id) DO UPDATE SET "
                    "embedding = EXCLUDED.embedding, payload = EXCLUDED.payload"
                ),
                {
                    "id": record.id,
                    "ns": self.namespace,
                    "emb": vec,
                    "payload": json.dumps(record.payload),
                },
            )
            session.commit()

    def query(self, vector: Sequence[float], top_k: int = 5) -> list[VectorHit]:
        from sqlalchemy import text

        vec = "[" + ",".join(str(float(x)) for x in vector) + "]"
        with self.db_manager.SessionLocal() as session:
            rows = session.execute(
                text(
                    f"SELECT id, payload, 1 - (embedding <=> :q) AS score "
                    f"FROM {self.table} WHERE namespace = :ns "
                    "ORDER BY embedding <=> :q LIMIT :k"
                ),
                {"q": vec, "ns": self.namespace, "k": top_k},
            ).mappings()
            return [
                VectorHit(
                    id=row["id"],
                    score=float(row["score"]),
                    payload=row["payload"] or {},
                )
                for row in rows
            ]

    def count(self) -> int:
        from sqlalchemy import text

        with self.db_manager.SessionLocal() as session:
            result = session.execute(
                text(f"SELECT COUNT(*) FROM {self.table} WHERE namespace = :ns"),
                {"ns": self.namespace},
            )
            return int(result.scalar() or 0)

    def clear(self) -> None:
        from sqlalchemy import text

        with self.db_manager.SessionLocal() as session:
            session.execute(
                text(f"DELETE FROM {self.table} WHERE namespace = :ns"),
                {"ns": self.namespace},
            )
            session.commit()


def get_vector_store(
    *,
    offline: bool = True,
    db_manager: Optional[Any] = None,
    dimensions: int = 384,
    table: str = "vectors",
    namespace: str = "default",
) -> VectorStore:
    """Return an in-memory store when offline (or no DB), else a pgvector store."""
    if offline or db_manager is None:
        return InMemoryVectorStore()
    store = PgVectorStore(
        db_manager, dimensions=dimensions, table=table, namespace=namespace
    )
    return store
