import type { ReactNode } from "react";
import type { Channel, LeadScore } from "@/lib/types";
import { channelIconUrl } from "@/lib/channel-icons";
import { cn, scoreLabel } from "@/lib/ui";

export function ChannelIcon({
  channel,
  size = "sm",
}: {
  channel: Channel;
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
      title={channel}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={channelIconUrl(channel)}
        alt=""
        width={icon}
        height={icon}
        className="object-contain"
        loading="lazy"
      />
    </span>
  );
}

export function ScoreBadge({ score }: { score: LeadScore }) {
  const tone =
    score === "hot"
      ? "bg-rc-fg text-rc-primary-fg"
      : score === "warm"
        ? "border border-rc-border bg-rc-surface-hover text-rc-fg"
        : "bg-rc-surface-hover text-rc-fg-muted";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-sm font-medium",
        tone,
      )}
    >
      {scoreLabel[score]}
    </span>
  );
}

export function Label({ children }: { children: ReactNode }) {
  return (
    <span className="text-sm font-medium text-rc-fg-subtle">{children}</span>
  );
}

export function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={cn(
        "inline-block h-1.5 w-1.5 rounded-full",
        ok ? "bg-rc-fg" : "bg-rc-fg-subtle",
      )}
    />
  );
}

export function Pill({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "outline" | "muted";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-sm font-medium",
        tone === "default" && "bg-rc-fg text-rc-primary-fg",
        tone === "outline" && "border border-rc-border text-rc-fg-muted",
        tone === "muted" && "bg-rc-surface-hover text-rc-fg-muted",
      )}
    >
      {children}
    </span>
  );
}
