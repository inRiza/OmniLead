import { ApiError, getActiveWorkspace } from "./api";
import type { Channel } from "./types";

// Chat pemilik dengan agen. BE men-stream NDJSON: satu peristiwa per baris.
// step = agen memanggil tool, tool_result = hasil tool, message = jawaban akhir.

export type ChatEvent =
  | { type: "thoughts" | "say"; text: string }
  | { type: "step"; tool: string; args: Record<string, string>; label: string; say: string; thoughts?: string }
  | { type: "tool_result"; tool: string; ok: boolean; summary: string; data: Record<string, unknown>; refresh: boolean }
  | { type: "tool_progress"; tool: string; label: string; elapsed_s: number }
  | { type: "message"; text: string; thoughts?: string }
  | { type: "error"; message: string };

export type ToolStep = {
  tool: string;
  label: string;
  args: Record<string, string>;
  say: string;
  thoughts?: string;
  status: "running" | "done" | "failed" | "stopped";
  summary: string;
  data: Record<string, unknown>;
  progress?: string;
  elapsed?: number;
};

export type ChatTurn = {
  id: string;
  role: "user" | "agent";
  text: string;
  steps: ToolStep[];
  error: string;
  done: boolean;
  thoughts?: string;
  thinking?: string;
  narration?: string;
};

export type ChatHistoryItem = { role: "user" | "agent"; text: string };
export interface ConversationSummary { id: string; title: string; created_at: string; updated_at: string }
export interface Conversation extends ConversationSummary { turns: ChatTurn[]; lease_until: string | null; channel?: Channel | null }

export function parseLine(line: string): ChatEvent | null {
  const trimmed = line.trim();
  if (!trimmed) return null;
  try {
    const event = JSON.parse(trimmed);
    if (!event || typeof event !== "object") return null;
    if (["message", "thoughts", "say"].includes(event.type) && typeof event.text === "string") return event as ChatEvent;
    if (event.type === "step" && typeof event.tool === "string" && typeof event.label === "string") return event as ChatEvent;
    if (event.type === "tool_result" && typeof event.tool === "string" && typeof event.ok === "boolean" && typeof event.summary === "string") return event as ChatEvent;
    if (event.type === "error" && typeof event.message === "string") return event as ChatEvent;
    if (event.type === "tool_progress" && typeof event.tool === "string" && typeof event.label === "string" && typeof event.elapsed_s === "number") return event as ChatEvent;
    return null;
  } catch {
    return null;
  }
}

/** Terapkan satu peristiwa ke giliran agen; tidak mengubah objek asal. */
export function applyEvent(turn: ChatTurn, event: ChatEvent): ChatTurn {
  if (event.type === "thoughts") return { ...turn, thinking: (turn.thinking ?? "") + event.text };
  if (event.type === "say") return { ...turn, narration: (turn.narration ?? "") + event.text };
  if (event.type === "step") {
    const step: ToolStep = {
      tool: event.tool, label: event.label, args: event.args ?? {}, say: event.say ?? "",
      thoughts: event.thoughts || turn.thinking || "", status: "running", summary: "", data: {},
    };
    return { ...turn, thinking: "", narration: "", steps: [...turn.steps, step] };
  }
  if (event.type === "tool_result") {
    const steps = [...turn.steps];
    const i = steps.findLastIndex((s) => s.status === "running" && s.tool === event.tool);
    if (i >= 0) {
      steps[i] = { ...steps[i], status: event.ok ? "done" : "failed", summary: event.summary, data: event.data ?? {} };
    }
    return { ...turn, steps };
  }
  if (event.type === "tool_progress") {
    return { ...turn, steps: turn.steps.map((s) => s.tool === event.tool && s.status === "running"
      ? { ...s, progress: event.label === "Menunggu operasi yang sedang berjalan" && s.progress ? s.progress : event.label, elapsed: event.elapsed_s } : s) };
  }
  if (event.type === "message") return { ...finishTurn(turn), text: event.text, thoughts: event.thoughts || turn.thinking || "", thinking: "", narration: "" };
  if (event.type === "error") return finishTurn(turn, event.message);
  return turn;
}

/** Every terminal path must settle tool indicators, including cancellation and broken streams. */
export function finishTurn(turn: ChatTurn, error = ""): ChatTurn {
  return { ...turn, done: true, error, thoughts: turn.thoughts || turn.thinking,
    steps: turn.steps.map((s) => s.status === "running" ? { ...s, status: "stopped" } : s) };
}

/** Baca stream NDJSON dan panggil `onEvent` untuk tiap baris utuh. */
export async function readNdjson(body: ReadableStream<Uint8Array>, onEvent: (e: ChatEvent) => void) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        const event = parseLine(line);
        if (event) onEvent(event);
      }
    }
    buffer += decoder.decode();
    const tail = parseLine(buffer);
    if (tail) onEvent(tail);
  } finally { reader.releaseLock(); }
}

export async function streamChat(
  message: string,
  history: ChatHistoryItem[],
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
  conversationId?: string,
  channel?: Channel | null,
) {
  const res = await fetchChat({ message, history, conversation_id: conversationId, channel }, signal);
  if (!res.body) throw new ApiError(0, "Respons chat kosong");
  await readNdjson(res.body, onEvent);
}

async function fetchChat(payload: unknown, signal?: AbortSignal): Promise<Response> {
  // request() membaca seluruh body sebagai JSON; stream butuh fetch langsung dengan cookie dan header yang sama.
  let res: Response;
  try {
    res = await fetch("/api/backend/agent/chat", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "content-type": "application/json",
        ...(getActiveWorkspace() ? { "x-omnilead-workspace": getActiveWorkspace()! } : {}),
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, "Backend tidak terjangkau");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* bukan JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res;
}
