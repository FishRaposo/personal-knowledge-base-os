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

    _write(vault, "a.md", "# A\ntwo")
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
