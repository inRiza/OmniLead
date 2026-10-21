// Tipe FE OmniLead. Dibuat selaras dengan models backend (omnilead-be).

export type Channel = "instagram" | "facebook" | "whatsapp" | "email";

export type LeadScore = "hot" | "warm" | "cold";

export type Urgency = "tinggi" | "sedang" | "rendah";

export type ActivityStatus = "baru" | "diproses" | "menunggu" | "selesai";

export type AccessPath = "official_api" | "handoff";

export interface Capability {
  action:
    | "list_posts"
    | "read_comments"
    | "post_comment"
    | "reply_comment"
    | "send_message";
  available: boolean;
  path: AccessPath | null;
  note?: string;
}

export interface ChannelStatus {
  channel: Channel;
  connected: boolean;
  detail: string;
  capabilities: Capability[];
}

export interface Activity {
  id: string;
  channel: Channel;
  kind: "komentar" | "dm" | "email";
  authorName: string;
  authorHandle: string;
  text: string;
  postContext?: string;
  receivedAt: string; // ISO
  status: ActivityStatus;
  urgency: Urgency;
  score: LeadScore;
  scoreValue: number; // 0-100
  reason: string; // alasan prioritas, bahasa awam
  leadId: string;
  /** Status event di BE: new | analyzed | review | held | agent_error */
  eventStatus: string;
}

export interface TraceStep {
  tool: string;
  input: string;
  output: string;
}

export interface GuardCheck {
  label: string;
  passed: boolean;
}

export interface AgentTrace {
  goal: string;
  plan: string[];
  steps: TraceStep[];
  guard: GuardCheck[];
  guardSummary?: string;
  status?: string;
}

export type ActionStatus =
  | "pending"
  | "approved"
  | "edited"
  | "executing"
  | "executed"
  | "failed"
  | "rejected"
  | "awaiting_manual_send"
  | "sent_manually";

export type ActionKind =
  | "merge"
  | "reply_comment"
  | "private_reply"
  | "send_message"
  | "crm_update"
  | "followup";

export interface GuardNote {
  check: string;
  status: "pass" | "warn" | "block";
  note: string;
}

export interface AuditEntry {
  id: number;
  ts: string;
  event: string;
  detail: string;
  actor: string;
  channel: string | null;
}

export interface ProposedAction {
  id: string;
  activityId: string;
  channel: Channel;
  kind: ActionKind;
  title: string; // mis. "Balasan publik di komentar IG"
  target: string; // mis. "@ani.majujaya"
  text: string;
  reason: string;
  path: AccessPath;
  status: ActionStatus;
  riskNote?: string;
  guard: GuardNote[];
  /** Aksi internal (ubah tahap, pengingat): tidak dikirim ke platform. */
  internal: boolean;
  isPublic: boolean;
  error?: string;
  /** Data tambahan dari agen (mis. merge: source/target, bukti, keyakinan). */
  payload: Record<string, unknown>;
}

export interface TimelineEntry {
  ts: string | null;
  direction: "in" | "out";
  channel: Channel;
  text: string;
}

export interface LeadDetail {
  lead: LeadProfile & { phones: string[]; emails: string[]; handles: string[]; scoreReason: string };
  timeline: TimelineEntry[];
  mergeEvidence: { id: number; ts: string; detail: string }[];
  /** Merge yang sudah dieksekusi dan masih bisa dipisah. */
  undoableMerges: { actionId: string; sourceName: string; evidence: string[] }[];
}

export interface SummaryItem {
  priority: number;
  kind: string;
  title: string;
  detail: string;
  leadId?: string | null;
}

export interface LeadProfile {
  id: string;
  name: string;
  company?: string;
  score: LeadScore;
  scoreValue: number;
  stage: "baru" | "tertarik" | "penawaran" | "deal" | "batal";
  summary: string;
  channels: Channel[];
  mergedEvidence?: string;
}
