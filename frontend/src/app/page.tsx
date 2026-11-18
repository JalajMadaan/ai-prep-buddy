"use client";

import { type FormEvent, useState } from "react";

import { askStudy, createConversation } from "@/lib/api";

type Citation = { n: number; source_key: string; title: string; url: string | null };
type Turn = { question: string; answer: string; citations: Citation[]; abstained: boolean };

const STYLES = ["concise", "interview", "deep"] as const;
type Style = (typeof STYLES)[number];

export default function Home() {
  const [question, setQuestion] = useState("");
  const [style, setStyle] = useState<Style>("interview");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [current, setCurrent] = useState<Turn | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);

  async function onAsk(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const q = question.trim();
    if (!q || loading) return;

    setLoading(true);
    setError(null);
    setQuestion("");
    const turn: Turn = { question: q, answer: "", citations: [], abstained: false };
    setCurrent({ ...turn });

    try {
      let convId = conversationId;
      if (!convId) {
        convId = await createConversation();
        setConversationId(convId);
      }
      for await (const { event, data } of askStudy({
        question: q,
        style,
        conversation_id: convId,
      })) {
        if (event === "meta") turn.abstained = Boolean(data.abstained);
        else if (event === "token") turn.answer += String(data.text ?? "");
        else if (event === "citation") turn.citations.push(data as unknown as Citation);
        setCurrent({ ...turn, citations: [...turn.citations] });
      }
      setTurns((prev) => [...prev, turn]);
      setCurrent(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setCurrent(null);
    } finally {
      setLoading(false);
    }
  }

  const transcript = current ? [...turns, current] : turns;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold">AI Prep Buddy — Study</h1>
        <p className="text-sm text-neutral-500">
          Ask an AI question; answers cite the knowledge base.
        </p>
      </header>

      <div className="flex flex-1 flex-col gap-4">
        {transcript.length === 0 && (
          <p className="text-sm text-neutral-400">
            Try: “Why does QLoRA use 4-bit quantization?”
          </p>
        )}
        {transcript.map((t, i) => (
          <article
            key={i}
            className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800"
          >
            <p className="mb-2 font-medium">{t.question}</p>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {t.answer || <span className="text-neutral-400">…</span>}
            </p>
            {t.abstained && (
              <p className="mt-2 text-xs font-medium text-amber-600">
                Not covered in the knowledge base
              </p>
            )}
            {t.citations.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {t.citations.map((c) => (
                  <Chip key={c.n} citation={c} />
                ))}
              </div>
            )}
          </article>
        ))}
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <form onSubmit={onAsk} className="sticky bottom-4 flex flex-col gap-2">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask an AI question…"
          rows={2}
          className="w-full resize-none rounded-lg border border-neutral-300 bg-white p-3 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700 dark:bg-neutral-900"
        />
        <div className="flex items-center gap-2">
          <select
            value={style}
            onChange={(e) => setStyle(e.target.value as Style)}
            className="rounded-lg border border-neutral-300 bg-white p-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            {STYLES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
          >
            {loading ? "Thinking…" : "Ask"}
          </button>
        </div>
      </form>
    </main>
  );
}

function Chip({ citation }: { citation: Citation }) {
  const label = `[${citation.n}] ${citation.title || citation.source_key}`;
  const className =
    "rounded-full border border-neutral-300 px-2 py-0.5 text-xs text-neutral-600 hover:border-neutral-500 dark:border-neutral-700 dark:text-neutral-300";
  return citation.url ? (
    <a href={citation.url} target="_blank" rel="noreferrer" className={className}>
      {label}
    </a>
  ) : (
    <span className={className}>{label}</span>
  );
}
