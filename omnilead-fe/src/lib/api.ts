import type { AgentExecutionEvent } from "./types";

// Klien REST ke omnilead-be. Tipe "Be*" = bentuk JSON dari backend apa adanya;
// adapt.ts mengubahnya ke tipe FE.

const BASE = "/api/backend";
let activeWorkspace: string | null = null;
export function setActiveWorkspace(id: string | null) { activeWorkspace = id; }

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
      credentials: "same-origin",
      headers: {
        "content-type": "application/json",
        ...(activeWorkspace ? { "x-omnilead-workspace": activeWorkspace } : {}),
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
  activity?: AgentExecutionEvent[];
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
  status: "new" | "processing" | "analyzed" | "review" | "held" | "agent_error";
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

export interface BePost {
  id: string;
  channel: string;
  url: string | null;
  caption: string | null;
  created_at: string | null;
  comment_count: number | null;
}

export interface BeComment {
  id: string;
  channel: string;
  post_ref: string;
  author_handle: string;
  author_name: string | null;
  text: string;
  created_at: string | null;
  parent_id: string | null;
}

export interface ProposeBody {
  channel: string;
  kind: BeAction["kind"];
  post_ref?: string;
  comment_ref?: string | null;
  text: string;
  reason?: string;
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

export interface AccountUser {
  id: string;
  workspace_id: string;
  email: string;
  name: string;
  business: string;
  workspaces: { id: string; name: string }[];
}

export interface AccountSession {
  enabled: boolean;
  user: AccountUser | null;
  registration_enabled: boolean;
}

export interface Connection {
  provider: "instagram" | "facebook" | "gmail" | "whatsapp";
  channel: string;
  configured: boolean;
  status: "connected" | "disconnected" | "reconnect_required";
  label: string;
  expires_at: number | null;
  scopes: string[];
  error: string;
}

export interface KnowledgeProduct {
  name: string;
  unit_price: number;
  unit: string;
  min_order: number;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  content: string;
  products: KnowledgeProduct[];
  updated_at: string;
}

export interface ChannelAgentConfig {
  knowledge_base_ids: string[];
  tone: "friendly" | "professional" | "casual" | "concise" | "custom";
  custom_tone: string;
}

export type ConnectionStart =
  | { mode: "redirect"; url: string }
  | { mode: "embedded"; app_id: string; config_id: string; version: string; state: string };

export interface WhatsAppAccounts {
  selection: string;
  accounts: { id: string; waba_id: string; label: string; registered: boolean }[];
}

export interface FacebookPages {
  pages: { id: string; label: string }[];
}

export const api = {
  base: BASE,
  session: () => request<AccountSession>("/auth/session"),
  login: (email: string, password: string) => post<AccountUser>("/auth/login", { email, password }),
  register: (body: { email: string; password: string; name: string }) => post<AccountUser>("/auth/register", body),
  addWorkspace: (name: string) => post<{ id: string; name: string }>("/workspaces", { name }),
  selectWorkspace: (workspace_id: string) => post<{ ok: boolean }>("/workspaces/select", { workspace_id }),
  knowledgeBases: () => request<KnowledgeBase[]>("/knowledge-bases"),
  saveKnowledge: (body: Pick<KnowledgeBase, "name" | "content" | "products">, id?: string) => id
    ? request<KnowledgeBase>(`/knowledge-bases/${id}`, { method: "PUT", body: JSON.stringify(body) })
    : post<KnowledgeBase>("/knowledge-bases", body),
  deleteKnowledge: (id: string) => request<{ ok: boolean }>(`/knowledge-bases/${id}`, { method: "DELETE" }),
  agentChannelSettings: () => request<Record<string, ChannelAgentConfig>>("/agent/channel-settings"),
  saveAgentChannelSettings: (channel: string, body: ChannelAgentConfig) => request<ChannelAgentConfig>(`/agent/channel-settings/${channel}`, { method: "PATCH", body: JSON.stringify(body) }),
  logout: () => post<{ ok: boolean }>("/auth/logout"),
  updateProfile: (name: string, business: string) => request<AccountUser>("/auth/profile", { method: "PATCH", body: JSON.stringify({ name, business }) }),
  connections: () => request<Connection[]>("/connections"),
  connect: (provider: string) => post<ConnectionStart>(`/connections/${provider}/start`),
  disconnect: (provider: string) => request<{ ok: boolean }>(`/connections/${provider}`, { method: "DELETE" }),
  whatsappExchange: (state: string, code: string) => post<WhatsAppAccounts>("/connections/whatsapp/exchange", { state, code }),
  whatsappSelect: (selection: string, account_id: string, pin: string) => post<{ ok: boolean }>("/connections/whatsapp/select", { selection, account_id, pin }),
  facebookPages: () => request<FacebookPages>("/connections/facebook/pages"),
  facebookSelect: (page_id: string) => post<{ ok: boolean }>("/connections/facebook/select", { page_id }),
  events: () => request<BeEvent[]>("/events?limit=200"),
  actions: () => request<BeAction[]>("/actions"),
  leads: () => request<BeLead[]>("/leads"),
  channels: () => request<BeChannel[]>("/channels"),
  posts: (channel: string, limit = 12) =>
    request<BePost[]>(`/channels/${channel}/posts?limit=${limit}`),
  comments: (channel: string, postRef: string, limit = 50) =>
    request<BeComment[]>(
      `/channels/${channel}/comments?post_ref=${encodeURIComponent(postRef)}&limit=${limit}`,
    ),
  propose: (body: ProposeBody) => post<BeAction>("/actions/propose", body),
  audit: () => request<BeAudit[]>("/audit?limit=200"),
  settings: () => request<BeSettings>("/settings"),
  agentHealth: () => request<BeAgentHealth>("/agent/health"),
  leadDetail: (id: string) => request<BeLeadDetail>(`/leads/${id}`),
  summary: () => request<BeSummaryItem[]>("/summary/today"),
  contentIdeas: () => request<BeContentIdeas>("/content-ideas"),
  pasteText: (body: { channel: string; text: string; handle?: string; name?: string }) =>
    post<BeEvent>("/events/paste?background=true", body),
  pasteImage: (body: { channel: string; image_base64: string; mime_type: string }) =>
    post<BeEvent>("/events/paste-image?background=true", body),

  approve: (id: string, editedText?: string) =>
    post<BeAction>(`/actions/${id}/approve`, { edited_text: editedText ?? null }),
  reject: (id: string, reason: string) =>
    post<BeAction>(`/actions/${id}/reject`, { reason }),
  retry: (id: string) => post<BeAction>(`/actions/${id}/retry`),
  undoMerge: (id: string) => post<BeAction>(`/actions/${id}/undo-merge`),
  markSent: (id: string) => post<BeAction>(`/actions/${id}/sent`),
  handoff: (id: string) => request<HandoffPackage>(`/actions/${id}/handoff`),
  reanalyze: (eventId: string) => post<BeEvent>(`/events/${eventId}/analyze?background=true`),

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
