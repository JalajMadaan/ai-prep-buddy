"use client";

import { useState } from "react";

import {
  finishQuiz,
  getQuizToday,
  submitAnswer,
  type AnswerResult,
  type QuizQuestion,
} from "@/lib/api";

const RATINGS = ["again", "hard", "good", "easy"] as const;

export default function QuizPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [shortAnswer, setShortAnswer] = useState("");
  const [feedback, setFeedback] = useState<AnswerResult | null>(null);
  const [summary, setSummary] = useState<{ total: number; correct: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const current: QuizQuestion | null = questions[index] ?? null;

  async function start() {
    setLoading(true);
    setError(null);
    setSummary(null);
    try {
      const today = await getQuizToday();
      setSessionId(today.quiz_session_id);
      setQuestions(today.questions);
      setIndex(0);
      setFeedback(null);
      setShortAnswer("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load drill");
    } finally {
      setLoading(false);
    }
  }

  async function answer(payload: { answer?: string; self_rating?: string }) {
    if (!sessionId || !current || loading) return;
    setLoading(true);
    setError(null);
    try {
      setFeedback(await submitAnswer({ quiz_session_id: sessionId, question_id: current.id, ...payload }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit");
    } finally {
      setLoading(false);
    }
  }

  async function next() {
    setFeedback(null);
    setShortAnswer("");
    if (index + 1 < questions.length) {
      setIndex(index + 1);
      return;
    }
    if (sessionId) {
      const result = await finishQuiz(sessionId);
      setSummary(result.summary);
      setQuestions([]);
      setSessionId(null);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold">Daily drill</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      {summary && (
        <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
          <p className="font-medium">
            Done — {summary.correct}/{summary.total} correct.
          </p>
          <button className="mt-3 rounded-lg bg-neutral-900 px-4 py-2 text-sm text-white dark:bg-white dark:text-neutral-900" onClick={start}>
            New drill
          </button>
        </div>
      )}

      {!summary && !current && (
        <button
          onClick={start}
          disabled={loading}
          className="w-fit rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          {loading ? "Loading…" : "Start today's drill"}
        </button>
      )}

      {!summary && current && (
        <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
          <p className="mb-1 text-xs text-neutral-500">
            {index + 1} / {questions.length} · {current.kind}
          </p>
          <p className="mb-4 font-medium">{current.text}</p>

          {!feedback && current.kind === "mcq" && (
            <div className="flex flex-col gap-2">
              {current.options.map((opt, i) => (
                <button
                  key={i}
                  onClick={() => answer({ answer: String(i) })}
                  disabled={loading}
                  className="rounded-lg border border-neutral-300 p-2 text-left text-sm hover:border-neutral-500 disabled:opacity-50 dark:border-neutral-700"
                >
                  {opt}
                </button>
              ))}
            </div>
          )}

          {!feedback && current.kind === "short" && (
            <div className="flex flex-col gap-2">
              <textarea
                value={shortAnswer}
                onChange={(e) => setShortAnswer(e.target.value)}
                rows={3}
                className="w-full rounded-lg border border-neutral-300 p-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
              />
              <button
                onClick={() => answer({ answer: shortAnswer })}
                disabled={loading || !shortAnswer.trim()}
                className="w-fit rounded-lg bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
              >
                Submit
              </button>
            </div>
          )}

          {!feedback && current.kind === "flashcard" && (
            <div className="flex flex-wrap gap-2">
              {RATINGS.map((r) => (
                <button
                  key={r}
                  onClick={() => answer({ self_rating: r })}
                  disabled={loading}
                  className="rounded-lg border border-neutral-300 px-3 py-1 text-sm hover:border-neutral-500 disabled:opacity-50 dark:border-neutral-700"
                >
                  {r}
                </button>
              ))}
            </div>
          )}

          {feedback && (
            <div className="mt-2 flex flex-col gap-2">
              <p className={`text-sm font-medium ${feedback.correct ? "text-green-600" : "text-amber-600"}`}>
                {feedback.correct ? "Correct" : "Not quite"} · score {feedback.score.toFixed(2)}
              </p>
              {feedback.explanation && <p className="text-sm">{feedback.explanation}</p>}
              <p className="text-xs text-neutral-500">Next review: {new Date(feedback.next_due_at).toLocaleString()}</p>
              <button
                onClick={next}
                className="w-fit rounded-lg bg-neutral-900 px-4 py-2 text-sm text-white dark:bg-white dark:text-neutral-900"
              >
                {index + 1 < questions.length ? "Next" : "Finish"}
              </button>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
