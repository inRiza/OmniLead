import { channelIconSlug } from "@/lib/channel-icons";
import type { Channel } from "@/lib/types";
import { channelLabel } from "@/lib/ui";
import { cn } from "@/lib/utils";

// Kanal yang ditampilkan di landing = kanal MVP (PRD 4.0), sama dengan kanal aplikasi.
export type LandingChannel = Channel;

export const landingChannelLabel: Record<LandingChannel, string> = channelLabel;

const slug: Record<LandingChannel, string> = channelIconSlug;

/** Sama dengan `ChannelIcon` di dashboard, tetapi menerima kanal landing. */
export function LandingChannelIcon({
  channel,
  size = "sm",
}: {
  channel: LandingChannel;
  size?: "sm" | "md";
}) {
  const box = size === "sm" ? "h-6 w-6" : "h-9 w-9";
  const icon = size === "sm" ? 14 : 18;
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-md border border-rc-border bg-rc-surface",
        box,
      )}
      title={landingChannelLabel[channel]}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`https://cdn.simpleicons.org/${slug[channel]}/09090b`}
        alt=""
        width={icon}
        height={icon}
        className="object-contain"
        loading="lazy"
      />
    </span>
  );
}
