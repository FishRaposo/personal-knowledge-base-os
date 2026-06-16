"""Shared pytest fixtures.

Tests import the API modules as the ``apps.api.src`` package (relative imports
inside the package then resolve), so we ensure the project root is importable.
Everything here runs offline: no database, no API key, no network.
"""

import os
import sys

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

VAULT_PATH = os.path.join(PROJECT_ROOT, "demo_vault")


@pytest.fixture
def vault_path() -> str:
    """Absolute path to the bundled demo vault."""
    return VAULT_PATH


@pytest.fixture
def sample_notes():
    """A small, fully-parsed set of notes for unit tests."""
    from apps.api.src.indexer import NotesIndexer

    indexer = NotesIndexer()
    return [
        indexer.parse_note(
            "---\ntitle: Alpha\ntags: [core, demo]\n---\n"
            "# Alpha\nAlpha links to [[Beta]] and explains pythons. #core",
            source="alpha.md",
        ),
        indexer.parse_note(
            "# Beta\nBeta is linked from Alpha and points to [[Gamma]]. #demo",
            source="beta.md",
        ),
        indexer.parse_note(
            "# Gamma\nGamma is a leaf note about retrieval and search.",
            source="gamma.md",
        ),
    ]


@pytest.fixture
def indexed_kb(vault_path):
    """A KnowledgeBase with the demo vault indexed (in-memory, offline)."""
    from apps.api.src.engine import KnowledgeBase

    kb = KnowledgeBase()
    kb.index_vault(vault_path)
    return kb
