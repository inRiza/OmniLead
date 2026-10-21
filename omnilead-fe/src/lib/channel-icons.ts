import type { Channel } from "./types";

/** Slug untuk https://cdn.simpleicons.org/{slug}/{color} */
export const channelIconSlug: Record<Channel, string> = {
  instagram: "instagram",
  linkedin: "linkedin",
  whatsapp: "whatsapp",
  email: "gmail",
  tiktok: "tiktok",
};

/** Simple Icons tidak lagi menyediakan LinkedIn (CDN 404); pakai glyph lokal. */
const LOCAL_ICONS: Partial<Record<Channel, string>> = {
  linkedin: "/icons/linkedin.svg",
};

export function channelIconUrl(channel: Channel, color = "09090b"): string {
  const local = LOCAL_ICONS[channel];
  if (local) return local;
  return `https://cdn.simpleicons.org/${channelIconSlug[channel]}/${color}`;
}
