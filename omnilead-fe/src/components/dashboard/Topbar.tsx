"use client";

import { useState } from "react";
import { channelLabel } from "@/lib/ui";
import { cn } from "@/lib/utils";
import { Button } from "@/components/action/button";
import { ChannelIcon, Dot } from "@/components/primitives";
import { useDashboard } from "./DashboardContext";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

export function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  const { paused, togglePause, channels, error, agent, loaded } = useDashboard();
  const [busy, setBusy] = useState(false);

  async function onToggle() {
    setBusy(true);
    try {
      await togglePause();
    } catch {
      /* error koneksi ditampilkan lewat banner */
    } finally {
      setBusy(false);
    }
  }

  return (
    <header className="shrink-0 bg-rc-bg">
      <div className="mx-auto flex min-h-14 w-full max-w-6xl flex-wrap items-center justify-between gap-3 py-3">
        <div className="min-w-0 space-y-0.5">
          <h1 className="text-lg font-semibold tracking-tight text-rc-fg">
            {title}
          </h1>
          {subtitle ? (
            <p className="text-sm leading-snug text-rc-fg-muted">
              {subtitle}
            </p>
          ) : null}
        </div>

        <div className="ml-auto flex max-w-full flex-wrap items-center justify-end gap-2">
          <WorkspaceSwitcher />
          <div className="hidden items-center gap-0.5 rounded-md border border-rc-border bg-rc-surface p-1 lg:flex">
            {channels.map((c) => (
              <span
                key={c.channel}
                className="inline-flex items-center gap-1 rounded-sm px-1.5 py-0.5"
                title={`${channelLabel[c.channel]}: ${c.connected ? "terhubung" : "belum terhubung"}`}
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
            disabled={busy || (loaded && error !== null)}
            onClick={onToggle}
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

      <div className="mx-auto flex w-full max-w-6xl flex-col gap-1.5">
        {error ? (
          <p
            role="alert"
            className="rounded-lg border border-rc-danger bg-rc-surface px-3 py-2 text-sm text-rc-danger"
          >
            Backend tidak terhubung. {error}. Data di layar mungkin sudah usang.
          </p>
        ) : null}
        {!error && agent && !agent.reachable ? (
          <p
            role="alert"
            className="rounded-lg border border-rc-border bg-rc-surface px-3 py-2 text-sm text-rc-fg-muted"
          >
            Service agen tidak terjangkau. Pesan baru akan ditandai dan bisa
            dianalisis ulang setelah agen menyala.
          </p>
        ) : null}
        {paused ? (
          <p
            role="status"
            className="rounded-lg bg-rc-danger px-3 py-2 text-center text-sm font-medium text-rc-danger-fg"
          >
            Agent dijeda. Semua aksi ditahan.
          </p>
        ) : null}
      </div>
    </header>
  );
}
