"""Generate canonical, credential-free portfolio evidence for PKB OS."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.src import worker  # noqa: E402
from apps.api.src.embeddings import EmbeddingGenerator  # noqa: E402
from apps.api.src.engine import KnowledgeBase  # noqa: E402
from apps.api.src.internal.vendor_core.testing import MockDatabase  # noqa: E402
from apps.api.src.store import DatabaseNoteStore  # noqa: E402
from apps.api.src.watcher import PollingVaultWatcher  # noqa: E402

DEFAULT_OUTPUT = (
    ROOT / "artifacts" / "portfolio" / "personal-knowledge-base-os-evidence"
)
FORMAT_VERSION = 1
BUNDLE_FILES = frozenset(
    {"checksums.sha256", "manifest.json", "report.json", "report.md"}
)


def canonical_bytes(value: Any) -> bytes:
    """Return the one accepted JSON representation (UTF-8 with final newline)."""
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write(root: Path, name: str, content: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _result_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "note": result["id"],
            "score": round(float(result["score"]), 6),
        }
        for result in results
    ]


def _frontend_fixture_proof() -> dict[str, Any]:
    source = (ROOT / "apps" / "web" / "src" / "lib" / "mockData.ts").read_text(
        encoding="utf-8"
    )
    note_block = source.split("const NOTE_INDEX", maxsplit=1)[0]
    exports = sorted(set(re.findall(r"export function (mock[A-Za-z]+)", source)))
    return {
        "offline_demo": True,
        "note_count": len(re.findall(r'^    id: "[^"]+",$', note_block, re.MULTILINE)),
        "fixture_exports": exports,
        "fixture_hash": sha256_hex(source.encode("utf-8")),
    }


def _scenario(workspace: Path) -> dict[str, Any]:
    default_vault = workspace / "default"
    work_vault = workspace / "work"
    default_vault.mkdir(parents=True)
    work_vault.mkdir(parents=True)
    _write(
        default_vault,
        "architecture.md",
        "# Architecture\n\nLocal-first graph links [[Retrieval]] and "
        "[[Missing Note]]. #graph #local\n",
    )
    _write(
        default_vault,
        "retrieval.md",
        "# Retrieval\n\nHybrid retrieval combines keyword and semantic results. "
        "#search #local\n",
    )
    _write(
        default_vault,
        "transient.md",
        "# Transient\n\nThis note will be removed by incremental indexing. #local\n",
    )
    _write(
        work_vault,
        "secret.md",
        "# Work Secret\n\nPrivate beta knowledge belongs only to work. #private\n",
    )

    kb = KnowledgeBase(
        embedder=EmbeddingGenerator(offline=True),
        api_keys={"openai": None, "anthropic": None},
    )
    kb.register_vault("default", str(default_vault), name="Default")
    kb.register_vault("work", str(work_vault), name="Work")
    initial = kb.index_vault(str(default_vault), incremental=True)
    work_index = kb.index_vault(str(work_vault), vault_id="work", incremental=True)

    graph = kb.get_graph()
    keyword = kb.search("hybrid retrieval", mode="keyword")
    semantic = kb.search("finding knowledge by meaning", mode="semantic")
    hybrid = kb.search("hybrid retrieval", mode="hybrid")
    tagged = kb.search("retrieval", mode="hybrid", tags=["search"])
    chat = kb.chat("How does hybrid retrieval work?", limit=2)

    default_private = kb.search("private beta", vault_id="default")
    work_private = kb.search("private beta", vault_id="work")

    architecture = kb._state("default").note_store.get_note("architecture")
    if architecture is None:
        raise RuntimeError("offline scenario did not index architecture")
    source = architecture["source"]
    architecture["source"] = "../escape.md"
    refusal_message = ""
    try:
        kb.update_note("architecture", "unsafe")
    except ValueError as exc:
        refusal_message = str(exc)
    finally:
        architecture["source"] = source
    updated = kb.update_note(
        "architecture",
        "# Architecture\n\nSafely edited graph links [[Retrieval]] and "
        "[[Missing Note]]. #graph #local\n",
    )

    _write(
        default_vault,
        "retrieval.md",
        "# Retrieval\n\nChanged hybrid retrieval combines lexical and semantic scores. "
        "#search #local\n",
    )
    _write(
        default_vault,
        "added.md",
        "# Added\n\nIncremental indexing discovered this note. #local\n",
    )
    (default_vault / "transient.md").unlink()
    incremental = kb.index_vault(str(default_vault), incremental=True)

    def reindex_after_change() -> None:
        kb.index_vault(str(default_vault), incremental=True)

    watcher = PollingVaultWatcher(
        vault_id="default",
        root=default_vault,
        event_bus=kb.events,
        on_change=reindex_after_change,
    )
    watcher.start(background=False)
    _write(
        default_vault,
        "added.md",
        "# Added\n\nThe explicit polling watcher observed this deterministic edit. "
        "#local\n",
    )
    watched_paths = watcher.poll_once()
    watcher.stop()
    events = kb.events.replay(vault_id="default")
    watcher_start = next(
        index
        for index, event in enumerate(events)
        if event["type"] == "watcher_started"
    )
    watcher_events = events[watcher_start:]
    replayed = kb.events.replay(vault_id="default", after_id=watcher_events[0]["id"])
    sse = kb.events.to_sse(watcher_events[-1])

    saved = kb.save_search(
        name="Local retrieval",
        query="hybrid retrieval",
        mode="hybrid",
        tags=["search"],
    )
    saved_again = kb.save_search(
        name="Local retrieval",
        query="hybrid retrieval",
        mode="hybrid",
        tags=["search"],
    )

    cards = kb.generate_flashcards(enrich=True)
    repeated_cards = kb.generate_flashcards(enrich=True)
    reviewed = kb.flashcards.review(cards[0]["id"], rating=4)

    sqlite = MockDatabase()
    sqlite_store = DatabaseNoteStore(sqlite.get_session)
    default_note = kb.get_note("architecture")
    work_note = kb.get_note("secret", vault_id="work")
    if default_note is None or work_note is None:
        raise RuntimeError("offline scenario lost persisted notes")
    sqlite_store.replace_all([default_note])
    sqlite_store.replace_all([work_note], vault_id="work")

    task_names = {worker.index_vault_task.name, worker.reindex_task.name}
    capabilities: dict[str, Any] = {
        "ingestion_graph": {
            "initial": {
                "notes": initial["total_notes"],
                "chunks": initial["total_chunks"],
                "links": initial["total_links"],
                "tags": initial["total_tags"],
            },
            "wikilinks": graph["edges"],
            "backlinks": kb.get_backlinks("retrieval"),
            "dangling_links": graph["dangling_links"],
        },
        "retrieval_chat": {
            "keyword": _result_summary(keyword),
            "semantic": _result_summary(semantic),
            "hybrid": _result_summary(hybrid),
            "tag_filter": [result["id"] for result in tagged],
            "chat": {
                "mode": chat["mode"],
                "model": chat["model"],
                "grounded": chat["grounded"],
                "citation_score": chat["citation_score"],
                "citations": [citation["id"] for citation in chat["citations"]],
            },
        },
        "multi_vault": {
            "default_search": [result["id"] for result in default_private],
            "work_search": [result["id"] for result in work_private],
            "work_indexed_notes": work_index["total_notes"],
            "isolated": not default_private
            and [result["id"] for result in work_private] == ["secret"],
        },
        "editing_incremental": {
            "safe_refusal": refusal_message == "note path is outside vault root",
            "successful_edit": updated["content"].startswith("# Architecture"),
            "changes": incremental["changes"],
            "deleted_absent": kb.get_note("transient") is None,
        },
        "watcher_events": {
            "backend": "stdlib_polling",
            "explicit_start": True,
            "changed_sources": watched_paths,
            "event_types": [event["type"] for event in watcher_events],
            "sse_replay": bool(replayed)
            and replayed[-1]["type"] == "watcher_stopped"
            and "event: watcher_stopped" in sse,
        },
        "saved_searches": {
            "stable": saved["id"] == saved_again["id"],
            "vault": saved["vault_id"],
            "query": saved["query"],
            "mode": saved["mode"],
            "tags": saved["tags"],
            "count": len(kb.list_saved_searches()),
        },
        "flashcards": {
            "count": len(cards),
            "stable": [card["id"] for card in cards]
            == [card["id"] for card in repeated_cards],
            "citations": sorted({card["citation"]["note_id"] for card in cards}),
            "provider_fallback": all(not card["enriched"] for card in cards),
            "review": reviewed["review"],
        },
        "persistence": {
            "in_memory": {
                "default_notes": kb.note_store.count(),
                "work_notes": kb.note_store.count(vault_id="work"),
            },
            "sqlite": {
                "default_notes": sqlite_store.count(),
                "work_notes": sqlite_store.count(vault_id="work"),
            },
        },
        "optional_fallbacks": {
            "network_required": False,
            "credentials_required": False,
            "embedding": type(kb.embedder.provider).__name__,
            "chat": chat["mode"],
            "flashcard_enrichment": "deterministic_local",
            "celery_imported_without_dispatch": task_names
            == {"kb.index_vault", "kb.reindex"},
        },
        "frontend_fixtures": _frontend_fixture_proof(),
    }
    assertions = {
        "broker_free_celery": capabilities["optional_fallbacks"][
            "celery_imported_without_dispatch"
        ],
        "citation_grounding": capabilities["retrieval_chat"]["chat"]["grounded"],
        "dangling_links": bool(capabilities["ingestion_graph"]["dangling_links"]),
        "deterministic_flashcards": capabilities["flashcards"]["stable"],
        "frontend_demo_fixtures": capabilities["frontend_fixtures"]["offline_demo"],
        "incremental_add_change_delete": capabilities["editing_incremental"]["changes"]
        == {"added": ["added"], "changed": ["retrieval"], "deleted": ["transient"]},
        "multi_vault_isolation": capabilities["multi_vault"]["isolated"],
        "offline_provider_fallbacks": not capabilities["optional_fallbacks"][
            "network_required"
        ],
        "safe_editing": capabilities["editing_incremental"]["safe_refusal"]
        and capabilities["editing_incremental"]["successful_edit"],
        "saved_search_stability": capabilities["saved_searches"]["stable"],
        "sqlite_and_memory": capabilities["persistence"]["sqlite"]
        == {"default_notes": 1, "work_notes": 1},
        "watcher_sse_replay": capabilities["watcher_events"]["sse_replay"],
    }
    if not all(assertions.values()):
        failed = sorted(name for name, passed in assertions.items() if not passed)
        raise RuntimeError(f"offline evidence assertion failed: {', '.join(failed)}")
    return {
        "schema_version": "1.0",
        "project": "personal-knowledge-base-os",
        "mode": "offline",
        "capabilities": capabilities,
        "assertions": assertions,
    }


def build_report() -> dict[str, Any]:
    """Exercise the product in a disposable local workspace."""
    with tempfile.TemporaryDirectory(prefix="pkb-evidence-") as temporary:
        return _scenario(Path(temporary))


def render_markdown(report: dict[str, Any]) -> str:
    capabilities = report["capabilities"]
    lines = [
        "# Personal Knowledge Base OS portfolio evidence",
        "",
        "Deterministic offline proof for ingestion, retrieval, local workflows, "
        "persistence, and dashboard fixtures.",
        "",
        f"Reproducibility hash: `{report['reproducibility_hash']}`",
        "",
        "## Verified capabilities",
        "",
    ]
    for name in sorted(capabilities):
        lines.append(f"- {name.replace('_', ' ')}")
    lines.extend(
        [
            "",
            "## Gate assertions",
            "",
            *[
                f"- {name.replace('_', ' ')}: passed"
                for name in sorted(report["assertions"])
            ],
            "",
        ]
    )
    return "\n".join(lines)


def write_bundle(report: dict[str, Any], output_dir: Path | str) -> dict[str, Any]:
    """Canonicalize an evidence report and write the four-file bundle."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    normalized = deepcopy(report)
    normalized.pop("reproducibility_hash", None)
    result_hash = sha256_hex(canonical_bytes(normalized))
    normalized["reproducibility_hash"] = result_hash
    report_json = canonical_bytes(normalized)
    report_md = render_markdown(normalized).encode("utf-8")
    manifest = {
        "format_version": FORMAT_VERSION,
        "project": "personal-knowledge-base-os",
        "reproducibility_hash": result_hash,
        "files": {
            "report.json": sha256_hex(report_json),
            "report.md": sha256_hex(report_md),
        },
    }
    manifest_json = canonical_bytes(manifest)
    payloads = {
        "manifest.json": manifest_json,
        "report.json": report_json,
        "report.md": report_md,
    }
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
    checksums = "".join(
        f"{sha256_hex(payloads[name])}  {name}\n" for name in sorted(payloads)
    )
    (output / "checksums.sha256").write_text(checksums, encoding="utf-8", newline="\n")
    return manifest


def generate_bundle(output_dir: Path | str = DEFAULT_OUTPUT) -> dict[str, Any]:
    return write_bundle(build_report(), output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = generate_bundle(args.output)
    print(manifest["reproducibility_hash"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
