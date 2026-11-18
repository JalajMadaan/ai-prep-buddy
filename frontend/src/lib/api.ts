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
