"""Milestones 3 and 4 backend contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.api.src.engine import KnowledgeBase
from apps.api.src.events import EventBus
from apps.api.src.flashcards import FlashcardService
from apps.api.src.graph import BacklinksGraph
from apps.api.src.watcher import PollingVaultWatcher


def _write(root: Path, name: str, content: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_graph_reports_dangling_links_additively():
    graph = BacklinksGraph()
    graph.build_graph(
        [{"id": "alpha", "title": "Alpha", "links": ["Missing Note"], "tags": []}]
    )

    payload = graph.get_graph()

    assert set(payload) >= {"nodes", "edges", "dangling_links"}
    assert payload["edges"] == [
        {"source": "alpha", "target": "Missing Note", "dangling": True}
    ]
    assert payload["dangling_links"] == [{"source": "alpha", "target": "Missing Note"}]


def test_multi_vault_state_is_isolated(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    _write(first, "same.md", "# First\nonly alpha")
    _write(second, "same.md", "# Second\nonly beta")
    kb = KnowledgeBase()
    kb.register_vault("alpha", str(first), name="Alpha")
    kb.register_vault("beta", str(second), name="Beta")

    kb.index_vault(str(first), vault_id="alpha")
    kb.index_vault(str(second), vault_id="beta")

    assert kb.get_note("same", vault_id="alpha")["title"] == "First"
    assert kb.get_note("same", vault_id="beta")["title"] == "Second"
    assert kb.search("beta", vault_id="alpha") == []
    assert kb.search("beta", vault_id="beta")[0]["id"] == "same"


def test_incremental_index_detects_add_change_and_delete(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    _write(vault, "a.md", "# A\none")
    kb = KnowledgeBase()
    kb.register_vault("v", str(vault))
    embedded: list[list[str]] = []
    real_embed = kb.embedder.embed_chunks

    def observe(chunks):
        embedded.append([chunk["note_id"] for chunk in chunks])
        return real_embed(chunks)

    kb.embedder.embed_chunks = observe
    first = kb.index_vault(str(vault), vault_id="v", incremental=True)
    assert first["changes"] == {"added": ["a"], "changed": [], "deleted": []}

    _write(vault, "a.md", "# A\ntwo with a different size")
    _write(vault, "b.md", "# B\nnew")
    second = kb.index_vault(str(vault), vault_id="v", incremental=True)
    assert second["changes"] == {
        "added": ["b"],
        "changed": ["a"],
        "deleted": [],
    }
    assert embedded[-1] == ["a", "b"]

    embedded.clear()
    unchanged = kb.index_vault(str(vault), vault_id="v", incremental=True)
    assert unchanged["changes"] == {"added": [], "changed": [], "deleted": []}
    assert embedded == []

    (vault / "a.md").unlink()
    third = kb.index_vault(str(vault), vault_id="v", incremental=True)
    assert third["changes"] == {"added": [], "changed": [], "deleted": ["a"]}
    assert kb.get_note("a", vault_id="v") is None


def test_safe_edit_stays_within_vault_and_emits_event(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    _write(vault, "safe.md", "# Safe\nold")
    kb = KnowledgeBase()
    kb.register_vault("v", str(vault))
    kb.index_vault(str(vault), vault_id="v")

    updated = kb.update_note("safe", "# Safe\nnew", vault_id="v")

    assert updated["content"].strip().endswith("new")
    assert (vault / "safe.md").read_text(encoding="utf-8") == "# Safe\nnew"
    assert kb.events.replay(vault_id="v")[-1]["type"] == "note_changed"

    stored = kb._state("v").note_store.get_note("safe", vault_id="v")
    assert stored is not None
    stored["source"] = "../escape.md"
    with pytest.raises(ValueError, match="outside vault"):
        kb.update_note("safe", "nope", vault_id="v")


def test_tag_filter_and_saved_search_are_vault_scoped(tmp_path):
    kb = KnowledgeBase()
    kb.register_vault("work", str(tmp_path))
    kb.index_notes(
        [
            {
                "id": "a",
                "title": "Alpha",
                "content": "common",
                "tags": ["keep"],
                "links": [],
                "chunks": [],
            },
            {
                "id": "b",
                "title": "Beta",
                "content": "common",
                "tags": ["drop"],
                "links": [],
                "chunks": [],
            },
        ],
        vault_id="work",
    )

    results = kb.search("common", vault_id="work", tags=["keep"])
    assert [result["id"] for result in results] == ["a"]
    saved = kb.save_search(
        name="Kept", query="common", mode="keyword", tags=["keep"], vault_id="work"
    )
    assert kb.list_saved_searches(vault_id="work") == [saved]
    assert kb.list_saved_searches(vault_id="default") == []


def test_unknown_vaults_are_rejected_until_explicitly_registered(tmp_path):
    kb = KnowledgeBase()

    with pytest.raises(KeyError, match="unknown"):
        kb.index_vault(str(tmp_path), vault_id="unknown")
    with pytest.raises(KeyError, match="unknown"):
        kb.search("anything", vault_id="unknown")

    assert [vault["id"] for vault in kb.list_vaults()] == ["default"]


def test_api_rejects_unregistered_vault_index_path(tmp_path):
    from fastapi.testclient import TestClient

    from apps.api.src import main

    outside = tmp_path / "outside"
    outside.mkdir()
    _write(outside, "secret.md", "# Secret\nprivate")
    main.kb = KnowledgeBase(config=main.config)
    client = TestClient(main.app)

    response = client.post(
        "/notes/index", json={"vault_id": "unknown", "path": str(outside)}
    )

    assert response.status_code == 404
    assert "unknown" not in {vault["id"] for vault in main.kb.list_vaults()}


def test_unknown_vault_api_paths_return_controlled_not_found_envelopes():
    from fastapi.testclient import TestClient

    from apps.api.src import main

    main.kb = KnowledgeBase(config=main.config)
    client = TestClient(main.app)
    requests = [
        client.get("/notes/search", params={"q": "x", "vault_id": "missing"}),
        client.post("/notes/chat", json={"query": "x", "vault_id": "missing"}),
        client.get("/notes/nope", params={"vault_id": "missing"}),
        client.get("/notes/nope/backlinks", params={"vault_id": "missing"}),
        client.get("/graph", params={"vault_id": "missing"}),
        client.get("/tags", params={"vault_id": "missing"}),
        client.get("/stats", params={"vault_id": "missing"}),
        client.post("/watchers/missing/start"),
        client.post("/watchers/missing/stop"),
        client.get("/saved-searches", params={"vault_id": "missing"}),
        client.post(
            "/saved-searches",
            json={"vault_id": "missing", "name": "X", "query": "x"},
        ),
        client.get("/flashcards", params={"vault_id": "missing"}),
        client.post("/flashcards/generate", json={"vault_id": "missing"}),
        client.get("/events/replay", params={"vault_id": "missing"}),
    ]

    assert [response.status_code for response in requests] == [404] * len(requests)
    assert all(response.json()["error"] == "NOT_FOUND" for response in requests)
    assert [vault["id"] for vault in main.kb.list_vaults()] == ["default"]


def test_lifespan_reindexes_every_restored_vault(monkeypatch, tmp_path):
    import asyncio

    from apps.api.src import main
    from apps.api.src.internal.vendor_core.vectorstore import InMemoryVectorStore
    from apps.api.src.store import InMemoryNoteStore

    main.kb = KnowledgeBase(config=main.config)
    main.kb.register_vault("work", str(tmp_path))
    restored = InMemoryNoteStore()
    calls: list[str] = []
    monkeypatch.setattr(main.db_module, "check_db", lambda: None)
    monkeypatch.setattr(main.db_module, "db_available", True)
    monkeypatch.setattr(main.db_module, "build_store", lambda: restored)
    monkeypatch.setattr(
        main, "get_vector_store", lambda **_kwargs: InMemoryVectorStore()
    )
    monkeypatch.setattr(
        main.kb,
        "reindex_from_store",
        lambda *, vault_id="default": calls.append(vault_id),
    )

    async def run_lifespan() -> None:
        async with main.lifespan(main.app):
            pass

    asyncio.run(run_lifespan())

    assert calls == ["default", "work"]
    assert main.kb.note_store is restored


def test_incremental_index_detects_frontmatter_only_change_and_source_move(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    _write(vault, "folder/a.md", "---\ntitle: Before\ntags: [old]\n---\nbody")
    kb = KnowledgeBase()
    kb.register_vault("v", str(vault))
    kb.index_vault(str(vault), vault_id="v", incremental=True)

    _write(vault, "folder/a.md", "---\ntitle: After\ntags: [new]\n---\nbody")
    changed = kb.index_vault(str(vault), vault_id="v", incremental=True)

    assert changed["changes"] == {"added": [], "changed": ["a"], "deleted": []}
    assert kb.get_note("a", vault_id="v")["title"] == "After"
    assert kb.get_note("a", vault_id="v")["tags"] == ["new"]

    (vault / "moved").mkdir()
    (vault / "folder" / "a.md").replace(vault / "moved" / "a.md")
    moved = kb.index_vault(str(vault), vault_id="v", incremental=True)

    assert moved["changes"] == {"added": [], "changed": ["a"], "deleted": []}
    assert kb.get_note("a", vault_id="v")["source"] == "moved/a.md"


@pytest.mark.parametrize("mode", ["semantic", "hybrid"])
def test_tag_filtered_vector_search_applies_limit_after_filtering(tmp_path, mode):
    kb = KnowledgeBase()
    kb.register_vault("work", str(tmp_path))
    notes = [
        {
            "id": f"untagged-{index}",
            "title": "Same",
            "content": "identical semantic content",
            "tags": ["drop"],
            "links": [],
            "chunks": [],
        }
        for index in range(25)
    ]
    notes.append(
        {
            "id": "tagged",
            "title": "Same",
            "content": "identical semantic content",
            "tags": ["keep"],
            "links": [],
            "chunks": [],
        }
    )
    kb.index_notes(notes, vault_id="work")

    results = kb.search(
        "identical semantic content",
        limit=1,
        mode=mode,
        vault_id="work",
        tags=["keep"],
    )

    assert [result["id"] for result in results] == ["tagged"]


def test_invalid_event_replay_cursor_has_a_validation_envelope():
    from fastapi.testclient import TestClient

    from apps.api.src import main

    main.kb = KnowledgeBase(config=main.config)
    client = TestClient(main.app)

    response = client.get("/events/replay", params={"last_event_id": "not-an-id"})

    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_flashcards_are_stable_cited_and_reviewable():
    service = FlashcardService()
    note = {
        "id": "architecture",
        "title": "Architecture",
        "source": "architecture.md",
        "content": (
            "# Storage\nThe local store keeps knowledge durable.\n\n"
            "## Search\nHybrid retrieval merges lexical and vector scores."
        ),
    }

    first = service.generate([note], vault_id="default")
    second = service.generate([note], vault_id="default")

    assert first == second
    assert first[0]["citation"]["note_id"] == "architecture"
    reviewed = service.review(first[0]["id"], rating=4, vault_id="default")
    assert reviewed["review"]["interval_days"] == 3
    assert reviewed["review"]["repetitions"] == 1


def test_event_bus_is_bounded_and_replayable():
    bus = EventBus(max_events=2)
    one = bus.publish("index_started", vault_id="v", data={"n": 1})
    two = bus.publish("note_changed", vault_id="v", data={"n": 2})
    three = bus.publish("index_completed", vault_id="v", data={"n": 3})

    assert int(one["id"]) < int(two["id"]) < int(three["id"])
    assert [event["type"] for event in bus.replay(vault_id="v")] == [
        "note_changed",
        "index_completed",
    ]
    assert bus.replay(vault_id="v", after_id=two["id"]) == [three]
    assert "event: index_completed" in bus.to_sse(three)


def test_polling_watcher_is_explicit_and_reports_changes(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    _write(vault, "a.md", "# A\none")
    bus = EventBus()
    watcher = PollingVaultWatcher(
        vault_id="v", root=vault, event_bus=bus, on_change=lambda: None
    )

    assert watcher.running is False
    watcher.start(background=False)
    assert watcher.running is True
    _write(vault, "a.md", "# A\ntwo")
    changed = watcher.poll_once()
    watcher.stop()

    assert changed == ["a.md"]
    assert [event["type"] for event in bus.replay(vault_id="v")] == [
        "watcher_started",
        "note_changed",
        "watcher_stopped",
    ]


def test_watcher_factory_falls_back_to_polling_when_watchdog_is_absent(
    tmp_path, monkeypatch
):
    from apps.api.src import watcher as watcher_module

    monkeypatch.setattr(watcher_module, "optional_watchdog_available", lambda: False)

    watcher = watcher_module.create_vault_watcher(
        vault_id="v",
        root=tmp_path,
        event_bus=EventBus(),
        on_change=lambda: None,
    )

    assert isinstance(watcher, PollingVaultWatcher)
    assert watcher.backend == "polling"


def test_watcher_factory_uses_watchdog_adapter_when_available(tmp_path, monkeypatch):
    from apps.api.src import watcher as watcher_module

    class FakeWatchdog(watcher_module.PollingVaultWatcher):
        backend = "watchdog"

    monkeypatch.setattr(watcher_module, "optional_watchdog_available", lambda: True)
    monkeypatch.setattr(watcher_module, "WatchdogVaultWatcher", FakeWatchdog)

    watcher = watcher_module.create_vault_watcher(
        vault_id="v",
        root=tmp_path,
        event_bus=EventBus(),
        on_change=lambda: None,
    )

    assert isinstance(watcher, FakeWatchdog)
    assert watcher.backend == "watchdog"


def test_additive_api_routes_preserve_legacy_shapes(tmp_path):
    from fastapi.testclient import TestClient

    from apps.api.src import main

    main.kb = KnowledgeBase(config=main.config)
    main.indexer = main.kb.indexer
    main.graph = main.kb.graph
    client = TestClient(main.app)
    vault = tmp_path / "vault"
    vault.mkdir()
    _write(vault, "a.md", "# Alpha\nTagged knowledge. #keep")

    created = client.post(
        "/vaults", json={"vault_id": "work", "name": "Work", "path": str(vault)}
    )
    assert created.status_code == 200
    indexed = client.post(
        "/notes/index", json={"vault_id": "work", "incremental": True}
    )
    assert indexed.status_code == 200
    assert indexed.json()["changes"]["added"] == ["a"]
    searched = client.get(
        "/notes/search", params={"q": "knowledge", "vault_id": "work", "tags": "keep"}
    )
    assert set(searched.json()) == {"query", "mode", "results", "total"}

    edited = client.patch(
        "/notes/a", json={"vault_id": "work", "content": "# Alpha\nUpdated. #keep"}
    )
    assert edited.status_code == 200
    assert edited.json()["id"] == "a"

    saved = client.post(
        "/saved-searches",
        json={"vault_id": "work", "name": "Keep", "query": "Updated", "tags": ["keep"]},
    )
    assert saved.status_code == 200
    assert client.get("/saved-searches", params={"vault_id": "work"}).json()[
        "saved_searches"
    ] == [saved.json()]

    cards = client.post(
        "/flashcards/generate", json={"vault_id": "work", "note_id": "a"}
    ).json()
    assert cards["total"] >= 1
    review = client.post(
        f"/flashcards/{cards['cards'][0]['id']}/review",
        json={"vault_id": "work", "rating": 4},
    )
    assert review.status_code == 200
    assert review.json()["review"]["repetitions"] == 1

    replay = client.get("/events/replay", params={"vault_id": "work"})
    assert replay.status_code == 200
    assert replay.json()["events"]


def test_indexer_rejects_binary_and_oversized_notes(tmp_path):
    from apps.api.src.indexer import NotesIndexer

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "binary.md").write_bytes(b"\xff\xfe\x00")
    with pytest.raises(ValueError, match="UTF-8"):
        NotesIndexer().parse_directory(str(vault))

    (vault / "binary.md").unlink()
    (vault / "large.md").write_text("x" * 11, encoding="utf-8")
    with pytest.raises(ValueError, match="byte limit"):
        NotesIndexer(max_file_size=10).parse_directory(str(vault))


def test_register_vault_rejects_terminal_and_parent_symlinks(tmp_path, monkeypatch):
    target = tmp_path / "target"
    target.mkdir()
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: (
            path.name in {"terminal", "parent-link"} or original_is_symlink(path)
        ),
    )
    kb = KnowledgeBase()

    with pytest.raises(ValueError, match="symlink"):
        kb.register_vault("terminal", str(tmp_path / "terminal"))

    with pytest.raises(ValueError, match="symlink"):
        kb.register_vault("parent", str(tmp_path / "parent-link" / "child"))


def test_edit_rejects_terminal_and_parent_symlink_components(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    nested = vault / "nested"
    nested.mkdir(parents=True)
    _write(vault, "nested/note.md", "# Note\noriginal")
    kb = KnowledgeBase()
    kb.register_vault("v", str(vault))
    kb.index_vault(str(vault), vault_id="v")
    stored = kb._state("v").note_store.get_note("note", vault_id="v")
    assert stored is not None

    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: (
            path.name in {"terminal.md", "parent-link"} or original_is_symlink(path)
        ),
    )
    stored["source"] = "terminal.md"
    with pytest.raises(ValueError, match="symlink"):
        kb.update_note("note", "unsafe", vault_id="v")

    stored["source"] = "parent-link/note.md"
    with pytest.raises(ValueError, match="symlink"):
        kb.update_note("note", "unsafe", vault_id="v")


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
def test_watcher_failure_stops_background_state(tmp_path, failure_type):
    vault = tmp_path / "vault"
    vault.mkdir()
    bus = EventBus()
    watcher = PollingVaultWatcher(
        vault_id="v", root=vault, event_bus=bus, on_change=lambda: None
    )
    watcher.running = True
    calls = 0

    def wait_once(_timeout):
        nonlocal calls
        calls += 1
        return calls > 1

    def invalid_poll():
        raise failure_type("invalid note")

    watcher._stop.wait = wait_once
    watcher.poll_once = invalid_poll
    watcher._run()

    assert watcher.running is False
    assert [event["type"] for event in bus.replay(vault_id="v")] == [
        "index_failed",
        "watcher_stopped",
    ]


def test_watcher_does_not_duplicate_engine_index_failure(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    _write(vault, "note.md", "# Note\nvalid")
    kb = KnowledgeBase()
    kb.register_vault("v", str(vault))
    kb.index_vault(str(vault), vault_id="v")
    kb.events = EventBus()
    watcher = PollingVaultWatcher(
        vault_id="v",
        root=vault,
        event_bus=kb.events,
        on_change=lambda: kb.index_vault(str(vault), vault_id="v", incremental=True),
    )
    watcher.start(background=False)
    (vault / "note.md").write_bytes(b"\xff\xfe")
    calls = 0

    def wait_once(_timeout):
        nonlocal calls
        calls += 1
        return calls > 1

    watcher._stop.wait = wait_once
    watcher._run()
    event_types = [event["type"] for event in kb.events.replay(vault_id="v")]

    assert event_types.count("index_failed") == 1
    assert event_types[-1] == "watcher_stopped"


def test_watcher_does_not_treat_stale_failure_as_current_attempt(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    bus = EventBus()
    bus.publish("index_failed", vault_id="v", data={"error": "OldFailure"})
    watcher = PollingVaultWatcher(
        vault_id="v", root=vault, event_bus=bus, on_change=lambda: None
    )
    watcher.running = True
    calls = 0

    def wait_once(_timeout):
        nonlocal calls
        calls += 1
        return calls > 1

    watcher._stop.wait = wait_once
    watcher.poll_once = lambda: (_ for _ in ()).throw(RuntimeError("current"))
    watcher._run()

    failures = [
        event for event in bus.replay(vault_id="v") if event["type"] == "index_failed"
    ]
    assert [event["data"]["error"] for event in failures] == [
        "OldFailure",
        "RuntimeError",
    ]


def test_watcher_does_not_claim_concurrent_failure_for_current_attempt(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    bus = EventBus()
    watcher = PollingVaultWatcher(
        vault_id="v", root=vault, event_bus=bus, on_change=lambda: None
    )
    watcher.running = True
    calls = 0

    def wait_once(_timeout):
        nonlocal calls
        calls += 1
        return calls > 1

    def concurrent_then_fail():
        bus.publish("index_failed", vault_id="v", data={"error": "Concurrent"})
        raise RuntimeError("current")

    watcher._stop.wait = wait_once
    watcher.poll_once = concurrent_then_fail
    watcher._run()

    failures = [
        event for event in bus.replay(vault_id="v") if event["type"] == "index_failed"
    ]
    assert [event["data"]["error"] for event in failures] == [
        "Concurrent",
        "RuntimeError",
    ]


def test_get_index_maps_validation_errors_like_post(tmp_path):
    from fastapi.testclient import TestClient

    from apps.api.src import main

    main.kb = KnowledgeBase(config=main.config)
    client = TestClient(main.app)
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "bad.md").write_bytes(b"\xff\xfe")
    assert (
        client.post("/vaults", json={"vault_id": "bad", "path": str(vault)}).status_code
        == 200
    )

    response = client.get("/notes/index", params={"vault_id": "bad"})

    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_vault_selection_is_explicit_and_default_compatible(tmp_path):
    from fastapi.testclient import TestClient

    from apps.api.src import main

    main.kb = KnowledgeBase(config=main.config)
    client = TestClient(main.app)
    vault = tmp_path / "work"
    vault.mkdir()
    client.post("/vaults", json={"vault_id": "work", "path": str(vault)})

    assert client.get("/vaults").json()["selected"] == "default"
    selected = client.post("/vaults/work/select")
    assert selected.status_code == 200
    assert selected.json()["selected"] == "work"
    assert client.get("/vaults").json()["selected"] == "work"
    assert client.post("/vaults/missing/select").status_code == 404


def test_edit_rejects_root_replaced_by_symlink_after_registration(
    tmp_path, monkeypatch
):
    vault = tmp_path / "vault"
    outside = tmp_path / "outside"
    vault.mkdir()
    outside.mkdir()
    _write(vault, "note.md", "# Note\ninside")
    _write(outside, "note.md", "# Note\noutside")
    kb = KnowledgeBase()
    kb.register_vault("v", str(vault))
    kb.index_vault(str(vault), vault_id="v")
    original_resolve = Path.resolve
    original_is_symlink = Path.is_symlink

    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path == vault or original_is_symlink(path),
    )
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda path, strict=False: (
            outside if path == vault else original_resolve(path, strict=strict)
        ),
    )

    with pytest.raises(ValueError, match="symlink"):
        kb.update_note("note", "unsafe", vault_id="v")
    assert (outside / "note.md").read_text(encoding="utf-8").endswith("outside")


def test_index_route_preserves_requested_symlink_for_engine_validation(
    tmp_path, monkeypatch
):
    from fastapi.testclient import TestClient

    from apps.api.src import main

    main.kb = KnowledgeBase(config=main.config)
    client = TestClient(main.app)
    configured = Path(main.kb.vault_metadata("default")["path"])
    alias = tmp_path / "alias"
    original_resolve = Path.resolve
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path == alias or original_is_symlink(path),
    )
    monkeypatch.setattr(
        Path,
        "resolve",
        lambda path, strict=False: (
            configured if path == alias else original_resolve(path, strict=strict)
        ),
    )

    response = client.get("/notes/index", params={"path": str(alias)})

    assert response.status_code == 400
    assert "symlink" in response.json()["message"].lower()


def test_default_config_symlink_is_not_resolved_before_route_validation(
    tmp_path, monkeypatch
):
    from fastapi.testclient import TestClient

    from apps.api.src import main
    from apps.api.src.config import AppConfig

    default_link = tmp_path / "default-link"
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda path: path.name == "default-link" or original_is_symlink(path),
    )
    main.kb = KnowledgeBase(config=AppConfig(DEFAULT_VAULT_PATH=str(default_link)))
    client = TestClient(main.app)

    response = client.get("/notes/index")

    assert response.status_code == 400
    assert "symlink" in response.json()["message"].lower()
