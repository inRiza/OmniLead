"use client";

import { useState } from "react";
import { channelLabel } from "@/lib/ui";
import { Button } from "@/components/action/button";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Topbar } from "@/components/dashboard/Topbar";
import { ChannelIcon, Dot, Pill } from "@/components/primitives";

const actionLabel: Record<string, string> = {
  list_posts: "Daftar post",
  read_comments: "Baca komentar",
  post_comment: "Tulis komentar",
  reply_comment: "Balas komentar",
  send_message: "Kirim pesan",
};

export default function IntegrasiPage() {
  const d = useDashboard();
  const [error, setError] = useState<string | null>(null);

  async function guard(fn: () => Promise<void>) {
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal");
    }
  }

  return (
    <>
      <Topbar
        title="Integrasi"
        subtitle="Kanal yang terhubung ke bisnis Anda"
      />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-3 p-4 pb-8 md:p-6">
          <div className="flex flex-wrap items-center gap-3 rounded-lg border border-rc-border bg-rc-surface p-6">
            <div className="min-w-0 flex-1">
              <div className="text-base font-semibold text-rc-fg">Service agen</div>
              <div className="text-sm text-rc-fg-muted">
                {d.agent
                  ? d.agent.reachable
                    ? `Terjangkau · engine ${d.agent.engine ?? "?"}`
                    : "Tidak terjangkau"
                  : "Memeriksa…"}
              </div>
            </div>
            <span className="flex shrink-0 items-center gap-1.5 rounded-md bg-rc-surface-hover/70 px-2 py-1 text-sm text-rc-fg-muted">
              <Dot ok={d.agent?.reachable ?? false} />
              {d.agent?.reachable ? "Aktif" : "Putus"}
            </span>
            <Button
              purpose="action"
              style={d.dryRun ? "primary" : "secondary"}
              onClick={() => guard(() => d.setDryRun(!d.dryRun))}
            >
              Dry-run: {d.dryRun ? "nyala" : "mati"}
            </Button>
          </div>

          {error ? (
            <p role="alert" className="text-sm font-medium text-rc-danger">
              {error}
            </p>
          ) : null}

          {d.channels.map((c) => {
            const enabled = !d.disabledChannels.includes(c.channel);
            return (
              <div
                key={c.channel}
                className="rounded-lg border border-rc-border bg-rc-surface p-6"
              >
                <div className="flex items-center gap-3">
                  <ChannelIcon channel={c.channel} size="md" />
                  <div className="min-w-0 flex-1">
                    <div className="text-base font-semibold text-rc-fg">
                      {channelLabel[c.channel]}
                    </div>
                    <div className="text-sm text-rc-fg-muted">{c.detail}</div>
                  </div>
                  <span className="flex shrink-0 items-center gap-1.5 rounded-md bg-rc-surface-hover/70 px-2 py-1 text-sm text-rc-fg-muted">
                    <Dot ok={c.connected} />
                    {c.connected ? "Aktif" : "Belum terhubung"}
                  </span>
                  <Button
                    purpose="action"
                    style={enabled ? "secondary" : "primary"}
                    onClick={() =>
                      guard(() => d.setChannelEnabled(c.channel, !enabled))
                    }
                  >
                    {enabled ? "Matikan" : "Nyalakan"}
                  </Button>
                </div>

                {!enabled ? (
                  <p className="mt-2 text-sm font-medium text-rc-fg">
                    Kanal dimatikan. Aksi keluar ke kanal ini ditahan.
                  </p>
                ) : null}

                <div className="mt-3 flex flex-wrap gap-2">
                  {c.capabilities.map((cap) => (
                    <span
                      key={cap.action}
                      title={cap.available ? undefined : "Aksi ini belum tersedia melalui koneksi yang aktif."}
                      className="inline-flex items-center gap-2 rounded-md border border-rc-border/80 bg-rc-bg px-2.5 py-1.5 text-sm"
                    >
                      <span className="font-medium text-rc-fg">
                        {actionLabel[cap.action] ?? cap.action}
                      </span>
                      {cap.available ? (
                        <Pill tone="muted">
                          {cap.path === "handoff" ? "Handoff" : "API"}
                        </Pill>
                      ) : (
                        <Pill tone="outline">Belum tersedia</Pill>
                      )}
                    </span>
                  ))}
                </div>
                {c.capabilities.some((cap) => !cap.available) ? (
                  <p className="mt-2 text-sm text-rc-fg-muted">
                    Aksi ini belum tersedia melalui koneksi yang aktif. Agen
                    menyiapkan teks, Anda yang mengirim (handoff).
                  </p>
                ) : null}
              </div>
            );
          })}
        </div>
      </ContentInset>
    </>
  );
}
