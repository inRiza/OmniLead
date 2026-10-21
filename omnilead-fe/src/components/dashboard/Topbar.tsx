"use client";

import { channelStatuses } from "@/lib/mock";
import { channelLabel } from "@/lib/ui";
import { cn } from "@/lib/utils";
import { Button } from "@/components/action/button";
import { ChannelIcon, Dot } from "@/components/primitives";
import { useDashboard } from "./DashboardContext";

export function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  const { paused, togglePause } = useDashboard();

  return (
    <header className="shrink-0 bg-rc-bg">
      <div className="flex min-h-14 items-center justify-between gap-4 py-3 pr-1 pl-1 md:pl-0">
        <div className="min-w-0 space-y-0.5">
          <h1 className="truncate text-lg font-semibold tracking-tight text-rc-fg">
            {title}
          </h1>
          {subtitle ? (
            <p className="truncate text-sm leading-snug text-rc-fg-muted">
              {subtitle}
            </p>
          ) : null}
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-0.5 rounded-md border border-rc-border bg-rc-surface p-1 lg:flex">
            {channelStatuses.map((c) => (
              <span
                key={c.channel}
                className="inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5"
                title={channelLabel[c.channel]}
              >
                <ChannelIcon channel={c.channel} />
                <Dot ok={c.connected} />
              </span>
            ))}
          </div>

          <Button
            purpose="action"
            style={paused ? "primary" : "secondary"}
            className="gap-2"
            onClick={togglePause}
          >
            <span
              className={cn(
                "inline-block h-2 w-2 rounded-full",
                paused ? "bg-rc-primary-fg" : "bg-rc-fg",
              )}
            />
            {paused ? "Lanjutkan agen" : "Jeda agen"}
          </Button>
        </div>
      </div>

      {paused ? (
        <p className="mb-0.5 rounded-lg border border-rc-border bg-rc-surface px-3 py-2 text-center text-sm text-rc-fg-muted">
          Agen dijeda. Balasan baru tidak terkirim sampai Anda melanjutkan.
        </p>
      ) : null}
    </header>
  );
}
