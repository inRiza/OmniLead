import type { Channel, LeadScore } from "./types";

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
  linkedin: "LinkedIn",
  whatsapp: "WhatsApp",
  email: "Email",
  tiktok: "TikTok",
};

export const scoreLabel: Record<LeadScore, string> = {
  hot: "Hot",
  warm: "Warm",
  cold: "Cold",
};
