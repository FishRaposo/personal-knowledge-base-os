"use client";

import { useState } from "react";
import { Pencil, Save, X } from "lucide-react";
import { api } from "@/lib/api";
import { selectedVault } from "@/components/VaultPicker";
import type { Note } from "@/types";

export default function NoteEditor({ note, onSaved }: { note: Note; onSaved: (note: Note) => void }) {
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(note.content);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!editing) return <button className="btn-secondary" onClick={() => setEditing(true)}><Pencil className="h-4 w-4" /> Edit note</button>;
  return <section className="mb-5 rounded-xl border border-brand-200 bg-brand-50 p-4" data-testid="note-editor">
    <label className="text-sm font-semibold text-ink-800" htmlFor="note-content">Markdown content</label>
    <textarea id="note-content" aria-label="Markdown content" value={content} onChange={(event) => setContent(event.target.value)} className="mt-2 min-h-56 w-full rounded-lg border border-ink-200 bg-white p-3 font-mono text-sm" />
    {error ? <p role="alert" className="mt-2 text-sm text-red-700">{error}</p> : null}
    <div className="mt-3 flex gap-2"><button className="btn-primary" disabled={saving} onClick={async () => { setSaving(true); setError(null); try { const { data } = await api.updateNote(note.id, { content, vaultId: selectedVault() }); onSaved(data); setEditing(false); } catch (err) { setError((err as Error).message); } finally { setSaving(false); } }}><Save className="h-4 w-4" /> Save safely</button><button className="btn-secondary" onClick={() => { setContent(note.content); setEditing(false); }}><X className="h-4 w-4" /> Cancel</button></div>
  </section>;
}
