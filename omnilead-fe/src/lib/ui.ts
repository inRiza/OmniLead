import type { Activity, AuditEntry, EventSource, Channel, LeadScore, LeadProfile, Sentiment, Urgency } from "./types";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

export { cn } from "./utils";

export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Date.now() - then;
  const m = Math.round(diff / 60000);
  if (Number.isNaN(m)) return "";
  if (m < 1) return "baru saja";
  if (m < 60) return `${m} mnt lalu`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} jam lalu`;
  return `${Math.round(h / 24)} hr lalu`;
}

export const channelLabel: Record<Channel, string> = {
  instagram: "Instagram",
  facebook: "Facebook",
  whatsapp: "WhatsApp",
  email: "Email",
};

export const scoreLabel: Record<LeadScore, string> = {
  hot: "Hot",
  warm: "Warm",
  cold: "Cold",
};

export type Tone = "blue" | "amber" | "green" | "red" | "gray";

export const toneClass: Record<Tone, string> = {
  blue: "bg-rc-accent-soft text-rc-accent",
  amber: "bg-amber-50 text-amber-700",
  green: "bg-emerald-50 text-emerald-700",
  red: "bg-red-50 text-red-700",
  gray: "bg-rc-surface-hover text-rc-fg-muted",
};

export function activityStatus(a: Pick<Activity, "status" | "eventStatus">): { label: string; tone: Tone } {
  if (a.eventStatus === "review" || a.eventStatus === "held" || a.eventStatus === "agent_error")
    return { label: "Perlu tinjauan", tone: "red" };
  if (a.status === "menunggu") return { label: "Ditangani agen", tone: "blue" };
  if (a.status === "selesai") return { label: "Selesai", tone: "green" };
  if (a.status === "diproses") return { label: "Diproses", tone: "blue" };
  return { label: "Perlu dibalas", tone: "blue" };
}

export const urgencyTone: Record<Urgency, Tone> = { tinggi: "red", sedang: "amber", rendah: "gray" };

export const stageLabel: Record<LeadProfile["stage"], string> = {
  baru: "Baru",
  tertarik: "Tertarik",
  penawaran: "Penawaran",
  deal: "Deal",
  batal: "Batal",
};

export const stageTone: Record<LeadProfile["stage"], Tone> = {
  baru: "gray",
  tertarik: "blue",
  penawaran: "amber",
  deal: "green",
  batal: "red",
};

export const outcomeMeta: Record<AuditEntry["outcome"], { label: string; tone: Tone }> = {
  success: { label: "Berhasil", tone: "green" },
  pending: { label: "Disiapkan", tone: "blue" },
  review: { label: "Perlu tinjauan", tone: "red" },
  blocked: { label: "Ditahan", tone: "gray" },
  failed: { label: "Gagal", tone: "red" },
};

export function actorKind(actor: string): "AI" | "Pengguna" | "Sistem" {
  const a = actor.toLowerCase();
  if (a === "agent" || a === "agen" || a === "ai") return "AI";
  if (a === "system" || a === "sistem" || a === "scheduler") return "Sistem";
  return "Pengguna";
}

export function cap(s: string) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

export const kindLabel: Record<Activity["kind"], string> = { komentar: "Komentar", dm: "Pesan langsung", email: "Email" };

export const sentimentTone: Record<Sentiment, Tone> = { positif: "green", netral: "gray", negatif: "red" };

export const sourceMeta: Record<EventSource, { label: string; tone: Tone }> = {
  webhook: { label: "Webhook Meta", tone: "green" },
  meta_api: { label: "Meta API", tone: "green" },
  openclaw: { label: "OpenClaw (layar)", tone: "amber" },
};
