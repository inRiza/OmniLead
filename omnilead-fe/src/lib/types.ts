// Tipe FE OmniLead. Dibuat selaras dengan models backend (omnilead-be).

export type Channel =
  | "instagram"
  | "linkedin"
  | "whatsapp"
  | "email"
  | "tiktok";

export type LeadScore = "hot" | "warm" | "cold";

export type Urgency = "tinggi" | "sedang" | "rendah";

export type ActivityStatus = "baru" | "diproses" | "menunggu" | "selesai";

export type AccessPath = "official_api" | "handoff";

export interface Capability {
  action: "list_posts" | "read_comments" | "post_comment" | "reply_comment" | "send_dm";
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
}

export type ActionStatus =
  | "pending"
  | "executed"
  | "rejected"
  | "awaiting_manual_send"
  | "sent_manually";

export type ActionKind =
  | "reply_comment"
  | "private_reply"
  | "send_message"
  | "crm_update"
  | "followup";

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
