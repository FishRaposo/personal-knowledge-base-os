"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpenCheck, Bookmark, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";
import { useActiveVault } from "@/components/VaultPicker";
import LiveVaultStatus from "@/components/LiveVaultStatus";
import type { Flashcard, SavedSearch } from "@/types";

export default function WorkspacePage() {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const vaultId = useActiveVault();
  const load = useCallback(async () => {
    const [saved, flashcards] = await Promise.all([api.getSavedSearches(vaultId), api.getFlashcards(vaultId)]);
    setSearches(saved.data.searches);
    setCards(flashcards.data.flashcards);
  }, [vaultId]);
  useEffect(() => { load().catch(() => undefined); }, [load]);

  return <div className="mx-auto max-w-4xl space-y-6">
    <header><h1 className="text-2xl font-bold tracking-tight text-ink-900">Vault workspace</h1><p className="mt-1 text-sm text-ink-500">Live indexing status, reusable retrieval, and local review cards for the active vault.</p></header>
    <LiveVaultStatus />
    <section className="card"><h2 className="flex items-center gap-2 text-lg font-semibold"><Bookmark className="h-5 w-5 text-brand-600" /> Saved searches</h2>
      <form className="mt-3 flex flex-wrap gap-2" onSubmit={async (event) => { event.preventDefault(); if (!name.trim() || !query.trim()) return; const { data } = await api.saveSearch({ name, query, vault_id: vaultId, mode: "hybrid" }); setSearches((current) => [...current, data]); setName(""); setQuery(""); }}>
        <input aria-label="Saved search name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" className="rounded border border-ink-200 px-3 py-2 text-sm" />
        <input aria-label="Saved search query" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Query" className="min-w-56 flex-1 rounded border border-ink-200 px-3 py-2 text-sm" />
        <button className="btn-primary">Save search</button>
      </form>
      <ul className="mt-4 space-y-2" data-testid="saved-searches">{searches.map((item) => <li key={item.id} className="rounded border border-ink-100 px-3 py-2 text-sm"><span className="font-medium">{item.name}</span><span className="ml-2 text-ink-500">{item.query}</span></li>)}</ul>
    </section>
    <section className="card"><div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="flex items-center gap-2 text-lg font-semibold"><BookOpenCheck className="h-5 w-5 text-brand-600" /> Flashcards</h2><p className="text-sm text-ink-500">Deterministic cards stay local. Provider enrichment remains optional.</p></div><button className="btn-secondary" onClick={async () => { const { data } = await api.generateFlashcards(vaultId); setCards(data.flashcards); }}><RefreshCw className="h-4 w-4" /> Generate cards</button></div>
      <div className="mt-4 space-y-3" data-testid="flashcards">{cards.map((card) => <article key={card.id} className="rounded-lg border border-ink-100 p-3"><p className="font-medium text-ink-800">{card.front}</p><p className="mt-2 text-sm text-ink-600">{card.back}</p><div className="mt-3 flex items-center gap-2"><span className="text-xs text-ink-400">Source: {card.note_id}</span><button className="rounded border border-ink-200 px-2 py-1 text-xs hover:bg-ink-50" onClick={() => api.reviewFlashcard(card.id, vaultId, 3)}>Reviewed</button></div></article>)}</div>
    </section>
  </div>;
}
