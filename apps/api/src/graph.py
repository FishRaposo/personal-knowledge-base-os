"""Bidirectional wikilink graph: adjacency, backlinks, and UI node/edge export.

``build_graph`` accepts the note dicts produced by the indexer and computes the
outbound adjacency list. Links are resolved by slug so ``[[Note Architecture]]``
matches the note whose id is ``note_architecture`` (and titles still work for the
legacy test surface). ``get_graph`` returns the nodes+edges shape a force-directed
graph UI consumes directly.
"""

import re
from typing import Dict, List, Set


def _key(note: Dict) -> str:
    """The canonical node key for a note: its ``id`` if present, else its title."""
    return note.get("id") or note.get("title", "")


def _slug(value: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", value.strip().lower())
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug.strip("_")


class BacklinksGraph:
    """Tracks outbound links and reverses them into backlinks for any note."""

    def __init__(self) -> None:
        self.adj_list: Dict[str, Set[str]] = {}
        self._titles: Dict[str, str] = {}
        self._tags: Dict[str, List[str]] = {}

    def build_graph(self, notes: List[Dict]) -> None:
        """Build the adjacency list from notes, resolving links to node keys."""
        self.adj_list = {}
        self._titles = {}
        self._tags = {}
        # First pass: register every known node and an alias -> key index.
        alias_to_key: Dict[str, str] = {}
        for note in notes:
            key = _key(note)
            self.adj_list.setdefault(key, set())
            self._titles[key] = note.get("title", key)
            self._tags[key] = list(note.get("tags", []))
            alias_to_key[key] = key
            alias_to_key[_slug(key)] = key
            title = note.get("title")
            if title:
                alias_to_key[_slug(title)] = key
        # Second pass: resolve outbound links.
        for note in notes:
            key = _key(note)
            for link in note.get("links", []):
                target = alias_to_key.get(_slug(link), link)
                self.adj_list[key].add(target)

    def get_backlinks(self, target: str) -> List[str]:
        """Return every node that links *to* ``target`` (resolved by slug)."""
        resolved = self._resolve(target)
        backlinks = [
            src
            for src, dests in self.adj_list.items()
            if resolved in dests or target in dests
        ]
        return sorted(set(backlinks))

    def get_outbound(self, source: str) -> List[str]:
        """Return the outbound links from ``source``."""
        resolved = self._resolve(source)
        return sorted(self.adj_list.get(resolved, set()))

    def get_graph(self) -> Dict[str, List[Dict]]:
        """Return a ``{nodes, edges}`` payload for a graph-visualization UI."""
        backlink_counts: Dict[str, int] = dict.fromkeys(self.adj_list, 0)
        edges: List[Dict] = []
        for src, dests in self.adj_list.items():
            for dest in dests:
                edges.append({"source": src, "target": dest})
                backlink_counts[dest] = backlink_counts.get(dest, 0) + 1
        nodes = [
            {
                "id": key,
                "title": self._titles.get(key, key),
                "tags": self._tags.get(key, []),
                "out_degree": len(dests),
                "in_degree": backlink_counts.get(key, 0),
            }
            for key, dests in self.adj_list.items()
        ]
        nodes.sort(key=lambda node: node["id"])
        edges.sort(key=lambda edge: (edge["source"], edge["target"]))
        return {"nodes": nodes, "edges": edges}

    def _resolve(self, value: str) -> str:
        if value in self.adj_list:
            return value
        slug = _slug(value)
        if slug in self.adj_list:
            return slug
        return value
