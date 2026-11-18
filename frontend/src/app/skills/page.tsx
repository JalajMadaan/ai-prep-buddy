"use client";

import { useEffect, useState } from "react";

import { getSkills, type SkillTopic } from "@/lib/api";

export default function SkillsPage() {
  const [topics, setTopics] = useState<SkillTopic[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getSkills()
      .then((r) => setTopics(r.topics))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoaded(true));
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 p-6">
      <h1 className="text-2xl font-semibold">Skill map</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {loaded && topics.length === 0 && !error && (
        <p className="text-sm text-neutral-500">No skills yet — answer a few quiz questions.</p>
      )}
      <div className="flex flex-col gap-3">
        {topics.map((t) => (
          <div key={t.topic_id}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="font-mono">{t.topic_id}</span>
              <span className="text-neutral-500">
                {Math.round(t.mastery * 100)}% · conf {Math.round(t.confidence * 100)}% · {t.attempts}×
              </span>
            </div>
            <div className="h-2 w-full rounded bg-neutral-200 dark:bg-neutral-800">
              <div
                className="h-2 rounded bg-neutral-900 dark:bg-white"
                style={{ width: `${Math.round(t.mastery * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
