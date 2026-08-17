"""Markdown vault ingestion: parse, chunk, and extract links/tags/metadata.

Built on internal ``vendor_core.docparse`` for parsing (``MarkdownParser``) and semantic
chunking (``chunk_text``). On top of the shared pipeline this module adds the
knowledge-base-specific signals: ``[[wikilink]]`` extraction, ``#hashtag`` and
YAML-frontmatter ``tags``, and a stable content hash per note. The output is a
list of plain dicts so it serializes straight to JSON and persists to either the
in-memory or the database store without an ORM dependency here.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .internal.vendor_core.docparse import (
    ChunkStrategy,
    MarkdownParser,
    chunk_text,
    compute_hash,
)

_WIKILINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")
_HASHTAG_RE = re.compile(r"(?:^|\s)#([a-zA-Z][\w/-]*)")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def slugify(title: str) -> str:
    """Normalize a note title/link to a stable id (lowercase, underscores)."""
    slug = title.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug.strip("_")


def extract_wikilinks(content: str) -> List[str]:
    """Return the target titles of ``[[wikilink]]`` references (alias-aware).

    Supports ``[[target|alias]]`` (keeps ``target``) and de-duplicates while
    preserving first-seen order.
    """
    links: List[str] = []
    for raw in _WIKILINK_RE.findall(content):
        target = raw.split("|", 1)[0].split("#", 1)[0].strip()
        if target and target not in links:
            links.append(target)
    return links


def _parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """Split YAML frontmatter from the body. Returns ``(metadata, body)``.

    A tiny, dependency-free YAML subset is parsed (``key: value`` and inline/list
    ``tags``) so the offline path needs no PyYAML; richer YAML is tolerated by
    ignoring lines that don't match.
    """
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return {}, content
    block = match.group(1)
    body = content[match.end() :]
    metadata: Dict[str, Any] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key:
            continue
        if key == "tags":
            metadata["tags"] = _parse_tag_value(value)
        elif value:
            metadata[key] = value
    return metadata, body


def _parse_tag_value(value: str) -> List[str]:
    """Parse a frontmatter ``tags`` value: ``[a, b]`` or ``a, b`` or ``a b``."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    parts = re.split(r"[,\s]+", value)
    return [p.strip().strip("\"'#") for p in parts if p.strip().strip("\"'#")]


def extract_tags(
    content: str, frontmatter: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Collect tags from frontmatter ``tags`` and inline ``#hashtags``."""
    tags: List[str] = []
    if frontmatter and frontmatter.get("tags"):
        for tag in frontmatter["tags"]:
            norm = tag.lstrip("#").strip().lower()
            if norm and norm not in tags:
                tags.append(norm)
    for raw in _HASHTAG_RE.findall(content):
        norm = raw.strip().lower()
        if norm and norm not in tags:
            tags.append(norm)
    return tags


class NotesIndexer:
    """Parses a markdown vault into structured, chunked notes."""

    def __init__(
        self,
        *,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        chunk_strategy: ChunkStrategy = ChunkStrategy.SEMANTIC,
        max_file_size: int = 2 * 1024 * 1024,
    ) -> None:
        self.parser = MarkdownParser()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_strategy = chunk_strategy
        self.max_file_size = max_file_size

    def parse_directory(
        self, folder_path: str, *, recursive: bool = True
    ) -> List[Dict]:
        """Parse every ``.md``/``.markdown`` file in ``folder_path`` into notes.

        Recurses into subdirectories by default (Obsidian vaults nest). Returns a
        list of note dicts sorted by id for deterministic output.
        """
        notes: List[Dict] = []
        if not os.path.isdir(folder_path):
            return notes
        for path in self._iter_markdown_files(folder_path, recursive):
            if os.path.islink(path):
                raise ValueError(f"Symlinked note is not allowed: {path}")
            size = os.path.getsize(path)
            if size > self.max_file_size:
                raise ValueError(
                    f"Note exceeds {self.max_file_size} byte limit: {path}"
                )
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    raw = handle.read()
            except UnicodeDecodeError as exc:
                raise ValueError(f"Note is not valid UTF-8 text: {path}") from exc
            if "\x00" in raw:
                raise ValueError(f"Binary note content is not allowed: {path}")
            rel = Path(os.path.relpath(path, folder_path)).as_posix()
            notes.append(self.parse_note(raw, source=rel))
        notes.sort(key=lambda note: note["id"])
        return notes

    def _iter_markdown_files(self, folder_path: str, recursive: bool):
        if recursive:
            for root, dirs, files in os.walk(folder_path, followlinks=False):
                symlinks = [
                    name for name in dirs if os.path.islink(os.path.join(root, name))
                ]
                if symlinks:
                    raise ValueError(
                        f"Symlinked directory is not allowed: "
                        f"{os.path.join(root, sorted(symlinks)[0])}"
                    )
                dirs[:] = sorted(dirs)
                for name in sorted(files):
                    if name.lower().endswith((".md", ".markdown")):
                        yield os.path.join(root, name)
        else:
            for name in sorted(os.listdir(folder_path)):
                full = os.path.join(folder_path, name)
                if os.path.isfile(full) and name.lower().endswith((".md", ".markdown")):
                    yield full

    def parse_note(self, raw: str, *, source: str = "note.md") -> Dict:
        """Parse a single markdown string into a structured note dict."""
        frontmatter, body = _parse_frontmatter(raw)
        parsed = self.parser.parse(body.encode("utf-8"), filename=source)

        base = os.path.basename(source)
        stem = re.sub(r"\.(md|markdown)$", "", base, flags=re.IGNORECASE)
        title = frontmatter.get("title") or parsed.title or stem
        note_id = slugify(stem)

        links = extract_wikilinks(body)
        tags = extract_tags(body, frontmatter)
        chunks = self._chunk(note_id, body)

        return {
            "id": note_id,
            "title": title,
            "content": body,
            "source": source,
            "links": links,
            "tags": tags,
            "metadata": frontmatter,
            # Hash the canonical source payload, including frontmatter. Metadata-only
            # edits must invalidate incremental snapshots even though ``content``
            # remains the legacy body-only response field.
            "content_hash": compute_hash(raw),
            "word_count": len(body.split()),
            "chunks": chunks,
        }

    def _chunk(self, note_id: str, body: str) -> List[Dict[str, Any]]:
        """Split a note body into embeddable chunk dicts."""
        pieces = chunk_text(
            body,
            strategy=self.chunk_strategy,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
        )
        return [
            {
                "id": f"{note_id}::{index}",
                "note_id": note_id,
                "index": index,
                "content": piece,
                "content_hash": compute_hash(piece),
            }
            for index, piece in enumerate(pieces)
        ]

    # Backwards-compatible alias retained for the original test surface.
    def _extract_links(self, content: str) -> List[str]:
        return extract_wikilinks(content)
