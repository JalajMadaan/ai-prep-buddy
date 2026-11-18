// Minimal client for the study API. The /ask endpoint streams Server-Sent
// Events over a POST, so we read the response body manually (EventSource is
// GET-only).

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type SSE = { event: string; data: Record<string, unknown> };

export type AskBody = {
  question: string;
  style: string;
  conversation_id?: string | null;
  topic_filter?: string[] | null;
};

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${path} failed (${res.status})`);
  return (await res.json()) as T;
}

export type QuizQuestion = {
  id: string;
  kind: string;
  text: string;
  options: string[];
  topic_ids: string[];
};
export type QuizToday = { quiz_session_id: string; questions: QuizQuestion[] };
export type AnswerResult = {
  correct: boolean;
  score: number;
  explanation: string;
  next_due_at: string;
};
export type SkillTopic = {
  topic_id: string;
  mastery: number;
  confidence: number;
  attempts: number;
};

export function getQuizToday(): Promise<QuizToday> {
  return jsonFetch<QuizToday>("/v1/quiz/today");
}

export function submitAnswer(body: {
  quiz_session_id: string;
  question_id: string;
  answer?: string;
  self_rating?: string | null;
}): Promise<AnswerResult> {
  return jsonFetch<AnswerResult>("/v1/quiz/answer", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function finishQuiz(
  sessionId: string,
): Promise<{ summary: { total: number; correct: number } }> {
  return jsonFetch(`/v1/quiz/sessions/${sessionId}/finish`, { method: "POST" });
}

export function getSkills(): Promise<{ topics: SkillTopic[] }> {
  return jsonFetch<{ topics: SkillTopic[] }>("/v1/skills");
}

export async function createConversation(): Promise<string> {
  const res = await fetch(`${API_BASE}/v1/study/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Could not start a conversation (${res.status})`);
  const json = (await res.json()) as { id: string };
  return json.id;
}

function parseEvent(raw: string): SSE | null {
  let event = "message";
  let data = "";
  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return null;
  return { event, data: JSON.parse(data) as Record<string, unknown> };
}

export async function* askStudy(body: AskBody): AsyncGenerator<SSE> {
  const res = await fetch(`${API_BASE}/v1/study/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) throw new Error(`Ask failed (${res.status})`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let streamDone = false;

  while (!streamDone) {
    const chunk = await reader.read();
    streamDone = chunk.done;
    if (chunk.value) buffer += decoder.decode(chunk.value, { stream: true });

    let sep = buffer.indexOf("\n\n");
    while (sep !== -1) {
      const parsed = parseEvent(buffer.slice(0, sep));
      buffer = buffer.slice(sep + 2);
      if (parsed) yield parsed;
      sep = buffer.indexOf("\n\n");
    }
  }
}
