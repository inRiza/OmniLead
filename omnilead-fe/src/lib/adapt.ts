// Mengubah respons backend ke tipe FE. Satu-satunya tempat yang tahu bentuk JSON BE.

import type {
  BeAction,
  BeAudit,
  BeChannel,
  BeEvent,
  BeLead,
  BeLeadDetail,
  BeSummaryItem,
  BeTrace,
} from "./api";
import { channelLabel } from "./ui";
import type {
  Activity,
  ActionStatus,
  AgentTrace,
  AuditEntry,
  Channel,
  ChannelStatus,
  LeadProfile,
  LeadScore,
  ProposedAction,
  Capability,
  LeadDetail,
  LeadNeeds,
  SummaryItem,
} from "./types";

const CHANNELS: Channel[] = ["instagram", "facebook", "whatsapp", "email"];
// Kanal dengan private reply (pesan atas komentar publik).
const PRIVATE_REPLY: string[] = ["instagram", "facebook"];

function asChannel(c: string): Channel {
  return (CHANNELS as string[]).includes(c) ? (c as Channel) : "email";
}

function asScore(label: string | null): LeadScore {
  const l = (label ?? "").toLowerCase();
  return l === "hot" || l === "warm" ? l : "cold";
}

const KIND: Record<BeEvent["kind"], Activity["kind"]> = {
  comment: "komentar",
  dm: "dm",
  message: "dm",
  email: "email",
};

export function asNeeds(raw: Record<string, unknown> | undefined | null): LeadNeeds {
  const r = raw ?? {};
  const text = (v: unknown) => (typeof v === "string" && v.trim() ? v.trim() : undefined);
  const num = (v: unknown) => (typeof v === "number" && v > 0 ? v : undefined);
  return {
    product: text(r.product),
    qty: num(r.qty),
    unit: text(r.unit),
    date: text(r.date),
    location: text(r.location),
    budget: num(r.budget),
    company: text(r.company),
  };
}

export function adaptEvent(
  e: BeEvent,
  lead: BeLead | undefined,
  pendingCount: number,
): Activity {
  const person = e.sender.name || e.sender.handle || e.sender.email || e.sender.phone;
  const authorName = [person || "Tidak dikenal", lead?.company]
    .filter(Boolean)
    .join(", ");

  let status: Activity["status"] = "baru";
  if (e.status === "analyzed") status = pendingCount > 0 ? "menunggu" : "selesai";
  else if (e.status === "review" || e.status === "held") status = "menunggu";

  const reasons: string[] = [];
  if (e.triage?.urgency_reason) reasons.push(e.triage.urgency_reason);
  if (e.status === "review" && e.review_reason) reasons.push(e.review_reason);
  if (e.status === "held") reasons.push("Agen dijeda; menunggu dilanjutkan.");
  if (e.status === "agent_error") reasons.push(e.review_reason || "Service agen tidak tersedia.");

  return {
    id: e.id,
    channel: asChannel(e.channel),
    kind: KIND[e.kind],
    authorName,
    authorHandle: e.sender.handle || e.sender.email || e.sender.phone || "",
    text: e.text,
    postContext: e.post_ref ? `Post: ${e.post_ref}` : undefined,
    receivedAt: e.ts ?? new Date().toISOString(),
    status,
    urgency: e.triage?.urgency ?? "rendah",
    score: asScore(lead?.label ?? null),
    scoreValue: lead?.score ?? 0,
    reason: reasons.join(" "),
    leadId: e.lead_id ?? "",
    eventStatus: e.status,
    source: e.meta?.source === "openclaw_text" ? "openclaw" : e.meta?.source === "meta_api_sync" ? "meta_api" : "webhook",
    folder: typeof e.meta?.folder === "string" ? e.meta.folder : undefined,
    sentiment: e.triage?.sentiment,
    needs: asNeeds(e.triage?.entities),
  };
}

const CHECK_LABEL: Record<string, string> = {
  konsistensi_harga: "Harga sesuai katalog",
  harga_di_publik: "Harga tidak di komentar publik",
  kebijakan_diskon: "Diskon sesuai kebijakan",
  kebocoran_data: "Tanpa data pihak lain",
  batas_kanal_jendela: "Jendela balasan kanal terbuka",
  batas_panjang: "Panjang teks sesuai batas kanal",
  duplikat: "Bukan pesan duplikat",
  nada: "Nada dan janji wajar",
  internal: "Perubahan internal",
  prompt_injection: "Tidak ada instruksi manipulatif",
};

export const checkLabel = (check: string) => CHECK_LABEL[check] ?? check;

const CAP_FOR_KIND: Record<BeAction["kind"], string | null> = {
  merge: null,
  comment_post: "post_comment",
  reply_comment: "reply_comment",
  send_message: "send_message",
  crm_update: null,
  followup: null,
};

function title(a: BeAction): string {
  switch (a.kind) {
    case "reply_comment":
      return a.public ? "Balasan publik di komentar" : "Balasan komentar";
    case "comment_post":
      return "Komentar baru di post";
    case "send_message":
      return a.comment_ref && PRIVATE_REPLY.includes(a.channel)
        ? "Private reply (DM) berisi detail"
        : `Pesan ${channelLabel[asChannel(a.channel)]}`;
    case "crm_update":
      return `Ubah tahap penjualan ke ${String(a.payload.stage ?? "?")}`;
    case "followup":
      return "Pengingat follow-up";
    case "merge":
      return "Gabungkan dua profil pelanggan";
  }
}

export function adaptAction(a: BeAction, channels: BeChannel[]): ProposedAction {
  const internal = a.kind === "crm_update" || a.kind === "followup" || a.kind === "merge";
  const handedOff = a.status === "awaiting_manual_send" || a.status === "sent_manually";

  let path: ProposedAction["path"] = "official_api";
  if (!internal) {
    if (handedOff) path = "handoff";
    else {
      const cap = channels
        .find((c) => c.channel === a.channel)
        ?.capabilities.find((c) => c.action === CAP_FOR_KIND[a.kind]);
      path = cap?.available ? "official_api" : "handoff";
    }
  }

  let text = a.text;
  if (a.kind === "crm_update") {
    const tags = Array.isArray(a.payload.tags) ? ` (${a.payload.tags.join(", ")})` : "";
    text = `Tahap penjualan menjadi "${String(a.payload.stage ?? "?")}"${tags}`;
  }

  const notes = a.guard.filter((g) => g.status !== "pass" && g.note);
  const risks: string[] = [];
  if (a.public) risks.push("Balasan ini terlihat publik.");
  if (path === "handoff" && !internal) risks.push("Dikirim manual oleh pengguna.");
  risks.push(...notes.map((n) => n.note));

  return {
    id: a.id,
    activityId: a.event_id ?? "",
    channel: asChannel(a.channel),
    kind:
      a.kind === "send_message" && a.comment_ref && PRIVATE_REPLY.includes(a.channel)
        ? "private_reply"
        : a.kind === "comment_post"
          ? "reply_comment"
          : a.kind,
    title: title(a),
    target: a.recipient || a.post_ref || "-",
    text,
    reason: a.reason,
    path,
    status: a.status as ActionStatus,
    riskNote: risks.length ? risks.join(" ") : undefined,
    guard: a.guard,
    internal,
    isPublic: a.public,
    error: a.error ?? undefined,
    deliveryStatus: a.delivery_status ?? null,
    feedback: a.feedback ?? [],
    payload: a.payload,
  };
}

function fmtInput(input: Record<string, unknown> | undefined): string {
  return Object.entries(input ?? {})
    .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(", ");
}

export function adaptTrace(
  trace: BeTrace | null,
  actions: BeAction[],
  event: BeEvent,
): AgentTrace | undefined {
  if (!trace?.goal) return undefined;

  const seen = new Map<string, boolean>();
  for (const a of actions) {
    for (const g of a.guard) {
      if (g.check === "internal") continue;
      seen.set(g.check, (seen.get(g.check) ?? true) && g.status === "pass");
    }
  }
  const guard = [...seen].map(([check, passed]) => ({ label: checkLabel(check), passed }));
  if (event.status === "review" && event.review_reason) {
    guard.push({ label: event.review_reason, passed: false });
  }

  return {
    goal: trace.goal,
    plan: trace.plan ?? [],
    steps: (trace.steps ?? []).map((s) => ({
      tool: s.tool,
      input: fmtInput(s.input),
      output: s.result,
    })),
    guard,
    guardSummary: trace.guard_summary,
    status: trace.status,
    activity: trace.activity ?? [],
  };
}

export function adaptLead(l: BeLead): LeadProfile {
  const channels = new Set<Channel>();
  for (const h of l.handles) channels.add(asChannel(h.split(":")[0]));
  if (l.phones.length) channels.add("whatsapp");
  if (l.emails.length) channels.add("email");
  return {
    id: l.id,
    name: l.name ?? "Tanpa nama",
    company: l.company ?? undefined,
    score: asScore(l.label),
    scoreValue: l.score ?? 0,
    stage: (["baru", "tertarik", "penawaran", "deal", "batal"].includes(l.stage)
      ? l.stage
      : "baru") as LeadProfile["stage"],
    summary: l.summary,
    channels: [...channels],
    scoreReason: l.score_reason ?? "",
    scoreReasons: l.score_reasons?.length ? l.score_reasons : (l.score_reason ?? "").split(";").map((r) => r.trim()).filter(Boolean),
    scoredAt: l.scored_at ?? undefined,
    scoreRubric: l.score_rubric || undefined,
    needs: asNeeds(l.needs),
    nextStep: l.next_step || undefined,
    estimatedValue: l.estimated_value ?? null,
    createdAt: l.created_at,
    updatedAt: l.updated_at,
  };
}

export function adaptChannel(c: BeChannel): ChannelStatus {
  return {
    channel: asChannel(c.channel),
    connected: c.connected,
    detail: c.detail,
    capabilities: c.capabilities.map(
      (cap): Capability => ({
        action: cap.action as Capability["action"],
        available: cap.available,
        path: cap.path,
        note: cap.note,
      }),
    ),
  };
}

const AUDIT_LABEL: Record<string, string> = {
  event_received: "Aktivitas masuk",
  event_analyzed: "Agen selesai menganalisis",
  event_held: "Event ditahan (agen dijeda)",
  agent_error: "Service agen tidak tersedia",
  lead_created: "Lead baru",
  identity_merged: "Identitas digabung",
  identity_split: "Profil dipisah kembali",
  followup_due: "Follow-up jatuh tempo",
  followup_skipped: "Follow-up dilewati (pelanggan sudah membalas)",
  summary_updated: "Skor dan ringkasan diperbarui",
  flag_for_review: "Ditandai untuk tinjauan manual",
  proposed: "Draf disiapkan",
  approved: "Disetujui",
  auto_approved: "Disetujui otomatis oleh agen",
  auto_held: "Dikembalikan ke pemilik",
  lead_updated: "Lead diubah pemilik",
  channel_connected: "Kanal dihubungkan",
  channel_disconnected: "Kanal diputus",
  knowledge_saved: "Pengetahuan disimpan",
  knowledge_deleted: "Pengetahuan dihapus",
  agent_channel_configured: "Pengaturan agen per kanal diubah",
  instagram_notification: "Notifikasi Instagram diterima",
  "approved (edited)": "Disetujui (diedit)",
  rejected: "Ditolak",
  retry: "Dicoba ulang",
  executed: "Terkirim",
  executed_internal: "Perubahan internal diterapkan",
  execute_failed: "Gagal kirim",
  handoff: "Disiapkan untuk kirim manual",
  sent_manually: "Dikirim manual",
  dry_run: "Dry-run (tidak dikirim)",
  blocked_paused: "Ditahan: agen dijeda",
  blocked_channel: "Ditahan: kanal dimatikan",
  blocked_rate_limit: "Ditahan: batas kirim per jam",
  paused: "Agen dijeda",
  resumed: "Agen dilanjutkan",
  channel_switch: "Saklar kanal diubah",
  settings_changed: "Pengaturan diubah",
  preference_learned: "Preferensi bisnis dipelajari",
  seed_reset: "Data demo direset",
  proposal_skipped: "Usulan dilewati",
};

const AUDIT_OUTCOME: Record<string, AuditEntry["outcome"]> = {
  proposed: "pending",
  auto_held: "pending",
  handoff: "pending",
  followup_due: "pending",
  flag_for_review: "review",
  event_held: "blocked",
  rejected: "blocked",
  blocked_paused: "blocked",
  blocked_channel: "blocked",
  blocked_rate_limit: "blocked",
  dry_run: "blocked",
  proposal_skipped: "blocked",
  followup_skipped: "blocked",
  execute_failed: "failed",
  agent_error: "failed",
};

const ACTION_WORD: Record<string, string> = {
  send_message: "Balasan pesan",
  send_email: "Balasan email",
  reply_comment: "Balasan komentar",
  post_comment: "Komentar baru",
  followup: "Follow-up",
  crm_update: "Update CRM",
  merge: "Gabung profil",
};

const ACTOR_LABEL: Record<string, string> = { agent: "Agen", ingest: "Sistem", system: "Sistem", owner: "Pemilik" };

// Detail audit dari backend memakai istilah internal; tampilkan dalam bahasa awam.
function auditDetail(detail: string): string {
  const action = detail.match(/^(\w+) di (\w+)(?: untuk (.+))?$/);
  if (action && ACTION_WORD[action[1]]) {
    const channel = channelLabel[action[2] as keyof typeof channelLabel] ?? action[2];
    const target = action[3] && action[3] !== "-" ? ` untuk ${action[3]}` : "";
    return `${ACTION_WORD[action[1]]} di ${channel}${target}`;
  }
  const score = detail.match(/^skor=(\d+)\s*(\w*)$/);
  if (score) return `Skor ${score[1]}${score[2] ? ` (${score[2]})` : ""}`;
  const mode = detail.match(/^mode (manual|hybrid|auto)$/);
  if (mode) return `Mode izin: ${AUTONOMY_LABEL[mode[1] as Autonomy]}`;
  return detail;
}

export type Autonomy = "manual" | "hybrid" | "auto";
export const AUTONOMY_LABEL: Record<Autonomy, string> = { manual: "Selalu tanya", hybrid: "Hybrid", auto: "Percaya penuh" };

export function adaptAudit(a: BeAudit): AuditEntry {
  return {
    id: a.id,
    ts: a.ts,
    kind: a.event,
    event: AUDIT_LABEL[a.event] ?? a.event,
    outcome: AUDIT_OUTCOME[a.event] ?? "success",
    leadId: a.lead_id,
    actionId: a.action_id,
    detail: auditDetail(a.detail),
    actor: ACTOR_LABEL[a.actor] ?? a.actor,
    channel: a.channel,
  };
}

export function adaptLeadDetail(d: BeLeadDetail): LeadDetail {
  return {
    lead: {
      ...adaptLead(d.lead),
      phones: d.lead.phones,
      emails: d.lead.emails,
      handles: d.lead.handles,
      scoreReason: d.lead.score_reason,
      notes: d.lead.notes ?? "",
      estimatedValue: d.lead.estimated_value ?? null,
      lostReason: d.lead.lost_reason ?? "",
      tags: d.lead.tags ?? [],
    },
    timeline: d.timeline.map((t) => ({
      ts: t.ts,
      direction: t.direction,
      channel: asChannel(t.channel),
      text: t.text,
    })),
    mergeEvidence: d.merge_evidence.map((e) => ({ id: e.id, ts: e.ts, detail: e.detail })),
    undoableMerges: (d.undoable_merges ?? []).map((m) => ({
      actionId: m.action_id,
      sourceName: m.source_name ?? "profil lain",
      evidence: m.evidence,
    })),
  };
}

export function adaptSummary(s: BeSummaryItem): SummaryItem {
  return {
    priority: s.priority,
    kind: s.kind,
    title: s.title,
    detail: s.detail,
    leadId: s.lead_id ?? null,
  };
}
