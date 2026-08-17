"""Deterministic local flashcard generation and review scheduling."""

from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from typing import Any, Callable, Dict, Iterable, Optional

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


class FlashcardService:
    """Process-local cards; provider enrichment is optional and fail-safe."""

    def __init__(self, enricher: Optional[Callable[[Dict], Dict]] = None) -> None:
        self._cards: Dict[tuple[str, str], Dict[str, Any]] = {}
        self._enricher = enricher

    def generate(
        self,
        notes: Iterable[Dict],
        *,
        vault_id: str = "default",
        enrich: bool = False,
    ) -> list[Dict[str, Any]]:
        generated: list[Dict[str, Any]] = []
        for note in sorted(notes, key=lambda item: item.get("id", "")):
            for index, (question, answer) in enumerate(self._pairs(note)):
                seed = (
                    f"{vault_id}\0{note.get('id', '')}\0{index}\0{question}\0{answer}"
                )
                card_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
                card: Dict[str, Any] = {
                    "id": card_id,
                    "vault_id": vault_id,
                    "question": question,
                    "answer": answer,
                    "citation": {
                        "note_id": note.get("id"),
                        "title": note.get("title", note.get("id", "")),
                        "source": note.get("source"),
                    },
                    "review": {
                        "repetitions": 0,
                        "interval_days": 0,
                        "due_in_days": 0,
                        "ease": 2.5,
                    },
                    "enriched": False,
                }
                if enrich and self._enricher:
                    try:
                        enriched = self._enricher(deepcopy(card))
                        if isinstance(enriched, dict):
                            card.update(enriched)
                            card["enriched"] = True
                    except Exception:  # noqa: BLE001 - deterministic fallback
                        pass
                existing = self._cards.get((vault_id, card_id))
                if existing:
                    card["review"] = existing["review"]
                self._cards[(vault_id, card_id)] = card
                generated.append(deepcopy(card))
        return generated

    def list(self, *, vault_id: str = "default") -> list[Dict[str, Any]]:
        return [
            deepcopy(card)
            for (scope, _), card in sorted(self._cards.items())
            if scope == vault_id
        ]

    def review(
        self, card_id: str, *, rating: int, vault_id: str = "default"
    ) -> Dict[str, Any]:
        if rating not in range(0, 6):
            raise ValueError("rating must be between 0 and 5")
        key = (vault_id, card_id)
        if key not in self._cards:
            raise KeyError(card_id)
        card = self._cards[key]
        state = card["review"]
        if rating < 3:
            state["repetitions"] = 0
            state["interval_days"] = 1
        else:
            state["repetitions"] += 1
            if state["repetitions"] == 1:
                state["interval_days"] = 3
            elif state["repetitions"] == 2:
                state["interval_days"] = 7
            else:
                state["interval_days"] = max(
                    1, round(state["interval_days"] * state["ease"])
                )
        state["ease"] = round(max(1.3, state["ease"] + 0.1 - (5 - rating) * 0.08), 2)
        state["due_in_days"] = state["interval_days"]
        return deepcopy(card)

    @staticmethod
    def _pairs(note: Dict) -> list[tuple[str, str]]:
        content = str(note.get("content", ""))
        headings = list(_HEADING.finditer(content))
        pairs: list[tuple[str, str]] = []
        for index, match in enumerate(headings):
            start = match.end()
            end = (
                headings[index + 1].start()
                if index + 1 < len(headings)
                else len(content)
            )
            body = " ".join(
                paragraph.strip()
                for paragraph in content[start:end].split("\n\n")
                if paragraph.strip()
            )
            if body:
                pairs.append((f"What does {match.group(2).strip()} explain?", body))
        if not pairs:
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            if paragraphs:
                title = note.get("title") or note.get("id") or "this note"
                pairs.append((f"What is the key point of {title}?", paragraphs[0]))
        return pairs
