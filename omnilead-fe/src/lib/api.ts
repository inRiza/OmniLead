// Klien REST ke omnilead-be. Tipe "Be*" = bentuk JSON dari backend apa adanya;
// adapt.ts mengubahnya ke tipe FE.

const BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);
// Hanya untuk dev: nilai NEXT_PUBLIC_* terkirim ke browser. Untuk produksi,
// lewatkan lewat proxy server-side.
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        "content-type": "application/json",
        ...(API_KEY ? { "x-api-key": API_KEY } : {}),
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(0, `Backend tidak terjangkau di ${BASE}`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* body bukan JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });

export interface BeGuardNote {
  check: string;
  status: "pass" | "warn" | "block";
  note: string;
}

export interface BeSender {
  handle: string;
  name: string | null;
  phone: string | null;
  email: string | null;
}

export interface BeTrace {
  goal?: string;
  plan?: string[];
  steps?: { n: number; tool: string; input: Record<string, unknown>; result: string }[];
  guard_summary?: string;
  status?: string;
  revisions?: number;
}

export interface BeEvent {
  id: string;
  channel: string;
  kind: "comment" | "dm" | "email" | "message";
  external_id: string;
  sender: BeSender;
  text: string;
  ts: string | null;
  post_ref: string | null;
  comment_ref: string | null;
  lead_id: string | null;
  status: "new" | "analyzed" | "review" | "held" | "agent_error";
  triage: {
    urgency?: "tinggi" | "sedang" | "rendah";
    urgency_reason?: string;
    intents?: string[];
  } | null;
  review_reason: string;
  trace: BeTrace | null;
}

export interface BeAction {
  id: string;
  channel: string;
  kind:
    | "comment_post"
    | "reply_comment"
    | "send_message"
    | "crm_update"
    | "followup"
    | "merge";
  post_ref: string;
  comment_ref: string | null;
  text: string;
  reason: string;
  recipient: string | null;
  due_at: string | null;
  payload: Record<string, unknown>;
  guard: BeGuardNote[];
  public: boolean;
  lead_id: string | null;
  event_id: string | null;
  trace: BeTrace | null;
  status: string;
  created_at: string;
  edited: boolean;
  error: string | null;
  reject_reason: string | null;
  result_ref: string | null;
}

export interface BeLead {
  id: string;
  name: string | null;
  company: string | null;
  phones: string[];
  emails: string[];
  handles: string[];
  stage: string;
  summary: string;
  score: number | null;
  label: string | null;
  score_reason: string;
  created_at: string;
  updated_at: string;
}

export interface BeCapability {
  action: string;
  available: boolean;
  path: "official_api" | "handoff" | null;
  note: string;
}

export interface BeChannel {
  channel: string;
  connected: boolean;
  detail: string;
  capabilities: BeCapability[];
}

export interface BeAudit {
  id: number;
  ts: string;
  action_id: string | null;
  event: string;
  detail: string;
  actor: string;
  channel: string | null;
  lead_id: string | null;
}

export interface BeSettings {
  paused: boolean;
  disabled_channels: string[];
  dry_run: boolean;
  preferences: string[];
  rate_limit_per_hour: number;
}

export interface BeAgentHealth {
  reachable: boolean;
  engine?: string;
  error?: string;
}

export interface BeLeadDetail {
  lead: BeLead;
  timeline: {
    ts: string | null;
    direction: "in" | "out";
    channel: string;
    text: string;
  }[];
  merge_evidence: BeAudit[];
  undoable_merges: { action_id: string; source_name: string | null; evidence: string[] }[];
}

export interface BeSummaryItem {
  priority: number;
  kind: string;
  title: string;
  detail: string;
  lead_id?: string | null;
}

export interface BeContentIdeas {
  analyzed: number;
  ideas: {
    title: string;
    why: string;
    format: string;
    caption: string;
    mentions: number;
  }[];
}

export interface HandoffPackage {
  copy_text: string;
  open_url: string;
  hint: string;
}

export const api = {
  base: BASE,
  events: () => request<BeEvent[]>("/events?limit=200"),
  actions: () => request<BeAction[]>("/actions"),
  leads: () => request<BeLead[]>("/leads"),
  channels: () => request<BeChannel[]>("/channels"),
  audit: () => request<BeAudit[]>("/audit?limit=200"),
  settings: () => request<BeSettings>("/settings"),
  agentHealth: () => request<BeAgentHealth>("/agent/health"),
  leadDetail: (id: string) => request<BeLeadDetail>(`/leads/${id}`),
  summary: () => request<BeSummaryItem[]>("/summary/today"),
  contentIdeas: () => request<BeContentIdeas>("/content-ideas"),
  pasteText: (body: { channel: string; text: string; handle?: string; name?: string }) =>
    post<BeEvent>("/events/paste", body),
  pasteImage: (body: { channel: string; image_base64: string; mime_type: string }) =>
    post<BeEvent>("/events/paste-image", body),

  approve: (id: string, editedText?: string) =>
    post<BeAction>(`/actions/${id}/approve`, { edited_text: editedText ?? null }),
  reject: (id: string, reason: string) =>
    post<BeAction>(`/actions/${id}/reject`, { reason }),
  retry: (id: string) => post<BeAction>(`/actions/${id}/retry`),
  undoMerge: (id: string) => post<BeAction>(`/actions/${id}/undo-merge`),
  markSent: (id: string) => post<BeAction>(`/actions/${id}/sent`),
  handoff: (id: string) => request<HandoffPackage>(`/actions/${id}/handoff`),
  reanalyze: (eventId: string) => post<BeEvent>(`/events/${eventId}/analyze`),

  setPause: (paused: boolean) =>
    post<{ paused: boolean; reprocessed_events: number }>("/settings/pause", {
      paused,
    }),
  setChannelEnabled: (channel: string, enabled: boolean) =>
    request<BeSettings>(`/settings/channels/${channel}`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  patchSettings: (patch: Partial<Pick<BeSettings, "dry_run" | "rate_limit_per_hour">>) =>
    request<BeSettings>("/settings", {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),
};
