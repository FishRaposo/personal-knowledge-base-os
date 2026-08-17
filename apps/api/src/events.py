"""Bounded, replayable knowledge-base events and SSE serialization."""

from __future__ import annotations

import json
import threading
from collections import deque
from typing import Any, Dict, Iterator, Optional


class EventBus:
    """Process-local event sink with monotonic reconnect-safe identifiers."""

    def __init__(self, max_events: int = 256) -> None:
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self._events: deque[Dict[str, Any]] = deque(maxlen=max_events)
        self._next_id = 1
        self._condition = threading.Condition()

    def publish(
        self, event_type: str, *, vault_id: str = "default", data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        with self._condition:
            event = {
                "id": str(self._next_id),
                "type": event_type,
                "vault_id": vault_id,
                "data": dict(data or {}),
            }
            self._next_id += 1
            self._events.append(event)
            self._condition.notify_all()
            return dict(event)

    def replay(
        self, *, vault_id: str = "default", after_id: str | int | None = None
    ) -> list[Dict[str, Any]]:
        boundary = int(after_id or 0)
        with self._condition:
            return [
                dict(event)
                for event in self._events
                if event["vault_id"] == vault_id and int(event["id"]) > boundary
            ]

    @staticmethod
    def to_sse(event: Dict[str, Any]) -> str:
        payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
        return f"id: {event['id']}\nevent: {event['type']}\ndata: {payload}\n\n"

    def stream(
        self,
        *,
        vault_id: str = "default",
        after_id: str | int | None = None,
        heartbeat_seconds: float = 15.0,
    ) -> Iterator[str]:
        """Yield replayed/new events, with comment heartbeats while idle."""
        cursor = int(after_id or 0)
        while True:
            pending = self.replay(vault_id=vault_id, after_id=cursor)
            if pending:
                for event in pending:
                    cursor = int(event["id"])
                    yield self.to_sse(event)
                continue
            with self._condition:
                self._condition.wait(timeout=heartbeat_seconds)
            if not self.replay(vault_id=vault_id, after_id=cursor):
                yield ": heartbeat\n\n"
