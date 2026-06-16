"use client";

import { useRef, useState } from "react";
import { Send, MessagesSquare, ShieldCheck, ShieldAlert, Bot, User } from "lucide-react";
import { api } from "@/lib/api";
import type { ChatResponse } from "@/types";
import CitationCard from "@/components/CitationCard";
import DemoBadge, { DemoWriteNotice } from "@/components/DemoBadge";
import { ErrorState } from "@/components/States";

interface Turn {
  id: number;
  question: string;
  answer: ChatResponse | null;
  loading: boolean;
  error: string | null;
  demo: boolean;
}

const SAMPLES = [
  "How do wikilinks work?",
  "What is semantic search?",
  "Why local-first?",
];

let TURN_ID = 0;

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  async function ask(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    const id = ++TURN_ID;
    setTurns((t) => [
      ...t,
      { id, question: q, answer: null, loading: true, error: null, demo: false },
    ]);
    requestAnimationFrame(() =>
      endRef.current?.scrollIntoView({ behavior: "smooth" })
    );

    try {
      const { data, source } = await api.chat({ query: q, limit: 3 });
      setTurns((t) =>
        t.map((turn) =>
          turn.id === id
            ? { ...turn, answer: data, loading: false, demo: source === "demo" }
            : turn
        )
      );
    } catch (err) {
      setTurns((t) =>
        t.map((turn) =>
          turn.id === id
            ? { ...turn, error: (err as Error).message, loading: false }
            : turn
        )
      );
    } finally {
      setBusy(false);
      requestAnimationFrame(() =>
        endRef.current?.scrollIntoView({ behavior: "smooth" })
      );
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col">
      <header className="mb-6">
        <h1 className="flex items-center gap-2 text-2xl font-bold tracking-tight text-ink-900">
          <MessagesSquare className="h-6 w-6 text-brand-600" />
          Chat with your notes
        </h1>
        <p className="mt-1 text-sm text-ink-500">
          Ask a question — answers are grounded in your notes with inline{" "}
          <code className="rounded bg-ink-100 px-1 text-brand-700">[n]</code> citations.
        </p>
      </header>

      {turns.length === 0 ? (
        <div className="rounded-xl border border-dashed border-ink-300 bg-white p-8 text-center">
          <Bot className="mx-auto mb-3 h-9 w-9 text-ink-300" />
          <p className="text-sm text-ink-500">
            No messages yet. Ask anything about your knowledge base.
          </p>
          <div className="mt-4 flex flex-wrap justify-center gap-2">
            {SAMPLES.map((s) => (
              <button
                key={s}
                onClick={() => ask(s)}
                className="chip-muted hover:border-brand-300 hover:text-brand-700"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-6" data-testid="chat-thread">
          {turns.map((turn) => (
            <TurnView key={turn.id} turn={turn} />
          ))}
          <div ref={endRef} />
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="sticky bottom-4 mt-6 flex items-center gap-2 rounded-xl border border-ink-200 bg-white p-2 shadow-md"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          aria-label="Chat message"
          disabled={busy}
          className="w-full bg-transparent px-3 py-2 text-sm text-ink-900 outline-none placeholder:text-ink-400 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={busy || !input.trim()}
          className="btn-primary shrink-0"
          aria-label="Send"
        >
          <Send className="h-4 w-4" />
          <span className="hidden sm:inline">Send</span>
        </button>
      </form>
    </div>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <div className="flex max-w-[85%] items-start gap-2">
          <div className="rounded-2xl rounded-tr-sm bg-brand-600 px-4 py-2.5 text-sm text-white">
            {turn.question}
          </div>
          <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-brand-100 text-brand-600">
            <User className="h-4 w-4" />
          </span>
        </div>
      </div>

      <div className="flex items-start gap-2">
        <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ink-100 text-ink-500">
          <Bot className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1">
          {turn.loading ? (
            <div className="inline-flex items-center gap-2 rounded-2xl rounded-tl-sm border border-ink-200 bg-white px-4 py-3 text-sm text-ink-400">
              <span className="flex gap-1">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-300 [animation-delay:-0.2s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-300 [animation-delay:-0.1s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-ink-300" />
              </span>
              Thinking…
            </div>
          ) : turn.error ? (
            <ErrorState message={turn.error} />
          ) : turn.answer ? (
            <AnswerView answer={turn.answer} demo={turn.demo} />
          ) : null}
        </div>
      </div>
    </div>
  );
}

function AnswerView({ answer, demo }: { answer: ChatResponse; demo: boolean }) {
  const refused = answer.mode === "refusal";
  return (
    <div className="rounded-2xl rounded-tl-sm border border-ink-200 bg-white p-4">
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-800">
        {answer.answer}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-ink-100 pt-3">
        {refused ? (
          <span className="inline-flex items-center gap-1 rounded-full border border-ink-200 bg-ink-50 px-2 py-0.5 text-xs font-medium text-ink-500">
            No grounded answer
          </span>
        ) : answer.grounded ? (
          <span className="inline-flex items-center gap-1 rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
            <ShieldCheck className="h-3 w-3" /> Grounded
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
            <ShieldAlert className="h-3 w-3" /> Low grounding
          </span>
        )}
        <span className="chip-muted">model: {answer.model}</span>
        {!refused ? (
          <span className="chip-muted">
            citation score: {Math.round(answer.citation_score * 100)}%
          </span>
        ) : null}
      </div>

      {answer.citations.length > 0 ? (
        <div className="mt-4">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-400">
            Sources
          </h4>
          <div className="space-y-2" data-testid="citations">
            {answer.citations.map((c) => (
              <CitationCard key={c.index} citation={c} />
            ))}
          </div>
        </div>
      ) : null}

      {demo ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <DemoBadge />
          <DemoWriteNotice />
        </div>
      ) : null}
    </div>
  );
}
