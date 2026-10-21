import type { Channel } from "./types";

/** Slug untuk https://cdn.simpleicons.org/{slug}/{color} */
export const channelIconSlug: Record<Channel, string> = {
  instagram: "instagram",
  linkedin: "linkedin",
  whatsapp: "whatsapp",
  email: "gmail",
  tiktok: "tiktok",
};

export function channelIconUrl(channel: Channel, color = "09090b"): string {
  return `https://cdn.simpleicons.org/${channelIconSlug[channel]}/${color}`;
}
