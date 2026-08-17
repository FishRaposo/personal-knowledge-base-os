"""Explicit stdlib polling watcher with an optional background loop."""

# watchdog is an optional extra imported only after availability detection.
# pyright: reportMissingImports=false

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Dict

from .events import EventBus


class PollingVaultWatcher:
    """Detect markdown file changes without requiring watchdog."""

    backend = "polling"

    def __init__(
        self,
        *,
        vault_id: str,
        root: Path | str,
        event_bus: EventBus,
        on_change: Callable[[], None],
        interval_seconds: float = 1.0,
    ) -> None:
        self.vault_id = vault_id
        self.root = Path(root).resolve()
        self.event_bus = event_bus
        self.on_change = on_change
        self.interval_seconds = interval_seconds
        self.running = False
        self._snapshot: Dict[str, tuple[int, int]] = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def _scan(self) -> Dict[str, tuple[int, int]]:
        result: Dict[str, tuple[int, int]] = {}
        if not self.root.is_dir():
            return result
        for path in sorted(self.root.rglob("*")):
            if path.is_symlink() or not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".markdown"}:
                continue
            stat = path.stat()
            result[path.relative_to(self.root).as_posix()] = (
                stat.st_mtime_ns,
                stat.st_size,
            )
        return result

    def start(self, *, background: bool = True) -> None:
        if self.running:
            return
        self._snapshot = self._scan()
        self.running = True
        self._stop.clear()
        self.event_bus.publish("watcher_started", vault_id=self.vault_id)
        if background:
            self._thread = threading.Thread(
                target=self._run, name=f"pkb-watcher-{self.vault_id}", daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        if not self.running:
            return
        self.running = False
        self._stop.set()
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=max(self.interval_seconds * 2, 0.2))
        self._thread = None
        self.event_bus.publish("watcher_stopped", vault_id=self.vault_id)

    def poll_once(self) -> list[str]:
        current = self._scan()
        changed = sorted(
            path
            for path in set(current) | set(self._snapshot)
            if current.get(path) != self._snapshot.get(path)
        )
        self._snapshot = current
        if changed:
            for path in changed:
                self.event_bus.publish(
                    "note_changed", vault_id=self.vault_id, data={"source": path}
                )
            self.on_change()
        return changed

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            existing = self.event_bus.replay(vault_id=self.vault_id)
            cursor = existing[-1]["id"] if existing else None
            try:
                self.poll_once()
            except Exception as exc:  # noqa: BLE001 - terminate truthfully on failure
                emitted_id = getattr(exc, "_pkb_index_failed_event_id", None)
                attempt_events = self.event_bus.replay(
                    vault_id=self.vault_id, after_id=cursor
                )
                engine_emitted = bool(emitted_id) and any(
                    event["id"] == str(emitted_id) and event["type"] == "index_failed"
                    for event in attempt_events
                )
                if not engine_emitted:
                    self.event_bus.publish(
                        "index_failed",
                        vault_id=self.vault_id,
                        data={"error": type(exc).__name__},
                    )
                self.running = False
                self._stop.set()
                self.event_bus.publish(
                    "watcher_stopped",
                    vault_id=self.vault_id,
                    data={"error": type(exc).__name__},
                )
                break


def optional_watchdog_available() -> bool:
    """Report acceleration availability without importing it by default."""
    try:
        import importlib.util

        return importlib.util.find_spec("watchdog") is not None
    except (ImportError, ValueError):
        return False


class WatchdogVaultWatcher(PollingVaultWatcher):
    """Use watchdog notifications to accelerate the same deterministic scan."""

    backend = "watchdog"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        watcher = self

        class MarkdownHandler(FileSystemEventHandler):
            def on_any_event(self, event) -> None:
                if event.is_directory:
                    return
                paths = [
                    getattr(event, "src_path", ""),
                    getattr(event, "dest_path", ""),
                ]
                if not any(
                    str(path).lower().endswith((".md", ".markdown")) for path in paths
                ):
                    return
                watcher.poll_once()

        self._observer = Observer()
        self._handler = MarkdownHandler()

    def start(self, *, background: bool = True) -> None:
        del background  # watchdog owns its background observer thread
        if self.running:
            return
        super().start(background=False)
        self._observer.schedule(self._handler, str(self.root), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        if not self.running:
            return
        self._observer.stop()
        self._observer.join(timeout=max(self.interval_seconds * 2, 0.2))
        super().stop()


def create_vault_watcher(**kwargs) -> PollingVaultWatcher:
    """Select watchdog acceleration when installed, otherwise stdlib polling."""
    if optional_watchdog_available():
        try:
            return WatchdogVaultWatcher(**kwargs)
        except (ImportError, RuntimeError):
            pass
    return PollingVaultWatcher(**kwargs)
