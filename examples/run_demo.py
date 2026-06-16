"""End-to-end demo for Personal Knowledge Base OS.

Runs fully offline — NO database, NO API key, NO network. It indexes the bundled
``demo_vault/``, then exercises keyword + semantic search, the backlinks graph,
tag rollup, and citation-grounded chat, printing each result. Exits 0 on success.
"""

import os
import sys

# Make the apps/api/src modules importable both as the ``apps.api.src`` package
# (how the tests import them) and as top-level modules. We add the project root so
# ``apps.api.src`` resolves as a package, keeping relative imports working.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from apps.api.src.engine import KnowledgeBase  # noqa: E402

VAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "demo_vault"))


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def main() -> int:
    kb = KnowledgeBase()

    section("1. Index the demo vault")
    summary = kb.index_vault(VAULT)
    print(f"Indexed {summary['total_notes']} notes from {VAULT}")
    print(
        f"  chunks={summary['total_chunks']}  "
        f"links={summary['total_links']}  tags={summary['total_tags']}"
    )
    assert summary["total_notes"] >= 8, "expected a richer demo vault"

    section("2. Keyword search: 'wikilinks'")
    for hit in kb.search("wikilinks", limit=3, mode="keyword"):
        print(f"  [{hit['score']:.1f}] {hit['title']}  tags={hit['tags']}")

    section("3. Semantic search: 'how do I find related ideas by meaning?'")
    sem = kb.search("how do I find related ideas by meaning?", limit=3, mode="semantic")
    for hit in sem:
        print(f"  [{hit['score']:.4f}] {hit['title']}")
    assert sem, "semantic search returned no results"

    section("4. Backlinks for 'notes_architecture'")
    backlinks = kb.get_backlinks("notes_architecture")
    print(f"  Notes linking to notes_architecture: {backlinks}")
    assert backlinks, "expected backlinks for notes_architecture"

    section("5. Graph (nodes + edges)")
    graph = kb.get_graph()
    print(f"  nodes={len(graph['nodes'])}  edges={len(graph['edges'])}")
    hub = max(graph["nodes"], key=lambda n: n["in_degree"])
    print(f"  most-linked note: {hub['id']} (in_degree={hub['in_degree']})")

    section("6. Tags")
    for tag in kb.list_tags()[:6]:
        print(f"  #{tag['tag']}: {tag['count']} note(s)")

    section("7. Chat with citations: 'How does the backlinks graph work?'")
    answer = kb.chat("How does the backlinks graph work?", limit=3)
    print(f"  mode={answer['mode']}  model={answer['model']}")
    print(
        f"  grounded={answer['grounded']} (citation_score={answer['citation_score']})"
    )
    print(f"  answer: {answer['answer'][:240]}...")
    print("  citations:")
    for citation in answer["citations"]:
        print(f"    [{citation['index']}] {citation['title']}")
    assert answer["grounded"], "chat answer was not grounded with citations"

    section("Demo complete — all assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
