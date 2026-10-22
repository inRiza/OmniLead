"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { ArrowRight, Check, Loader2, Play } from "lucide-react";
import { api, type InstagramSync } from "@/lib/api";
import { cn } from "@/lib/ui";
import { Button } from "@/components/action/button";
import { ChannelIcon } from "@/components/primitives";
import { TimeAgo } from "@/components/TimeAgo";
import { AgentRunPanel, useAgentRun } from "@/components/dashboard/AgentRun";

const DOT = { green: "bg-emerald-500", amber: "bg-amber-500", gray: "bg-rc-border-strong" } as const;

function Row({ dot, label, children }: { dot?: keyof typeof DOT; label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2.5 text-sm">
      <dt className="text-rc-fg-muted">{label}</dt>
      <dd className="flex items-center gap-1.5 text-right text-rc-fg">
        {dot ? <span aria-hidden className={cn("h-1.5 w-1.5 rounded-full", DOT[dot])} /> : null}
        {children}
      </dd>
    </div>
  );
}

type Phase = "idle" | "reading" | "answering" | "done";

export function InstagramAgent({ onFinished }: { onFinished: () => Promise<void> }) {
  const [status, setStatus] = useState<InstagramSync | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [read, setRead] = useState<InstagramSync | null>(null);
  const [answered, setAnswered] = useState(0);
  const [error, setError] = useState("");
  const agent = useAgentRun(onFinished);

  const load = useCallback(async () => {
    try {
      setStatus(await api.instagramSyncStatus());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Status Instagram belum bisa dimuat");
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => void load(), 0);
    return () => clearTimeout(t);
  }, [load]);

  async function start() {
    setError("");
    setRead(null);
    setAnswered(0);
    setPhase("reading");
    try {
      const synced = await api.instagramSync();
      setStatus(synced);
      setRead(synced);
      const events = await api.events();
      const targets = events
        .filter((e) => e.channel === "instagram" && e.status === "new" && !e.trace?.goal)
        .map((e) => ({ id: e.id, name: e.sender.name || e.sender.handle || "Pelanggan" }));
      setAnswered(targets.length);
      if (targets.length) {
        setPhase("answering");
        await agent.start(targets);
      } else {
        await onFinished();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agen gagal membaca Instagram");
    }
    setPhase("done");
  }

  const busy = phase === "reading" || phase === "answering";
  const summary =
    read &&
    `${read.dms ?? 0} DM dan ${read.comments ?? 0} komentar baru dibaca. ${answered ? `${answered} pesan dijawab agen.` : "Tidak ada pesan yang perlu dijawab."}`;

  return (
    <div className="flex flex-col gap-4">
      <section className="rounded-xl border border-rc-border bg-rc-surface p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <ChannelIcon channel="instagram" size="md" />
            <div>
              <p className="text-sm font-semibold text-rc-fg">Instagram</p>
              <p className="text-xs text-rc-fg-muted">Baca DM dan komentar baru, lalu siapkan balasannya</p>
            </div>
          </div>
          <Button purpose="action" style="primary" className="gap-1.5" disabled={busy} onClick={() => void start()}>
            {busy ? <Loader2 aria-hidden className="h-4 w-4 motion-safe:animate-spin" /> : <Play aria-hidden className="h-4 w-4" />}
            {phase === "reading" ? "Membaca…" : phase === "answering" ? "Menjawab…" : "Mulai baca"}
          </Button>
        </div>
        <dl className="mt-4 divide-y divide-rc-border border-t border-rc-border">
          <Row label="Webhook" dot={status?.webhook_last_at ? (status.webhook_stale ? "amber" : "green") : "gray"}>
            {status?.webhook_last_at ? (
              <>
                {status.webhook_stale ? "Sepi" : "Aktif"}, <TimeAgo iso={status.webhook_last_at} />
              </>
            ) : (
              "Belum menerima"
            )}
          </Row>
          <Row label="Terakhir dibaca">{status?.last_run_at ? <TimeAgo iso={status.last_run_at} /> : "Belum pernah"}</Row>
        </dl>
      </section>

      {phase === "reading" ? (
        <section className="flex items-center gap-3 rounded-xl border border-rc-border bg-rc-surface px-5 py-4 text-sm text-rc-fg">
          <Loader2 aria-hidden className="h-5 w-5 text-rc-accent motion-safe:animate-spin" />
          Membaca DM dan komentar baru dari Instagram…
        </section>
      ) : null}

      {phase !== "reading" && read ? (
        <section className="flex items-center gap-3 rounded-xl border border-rc-border bg-rc-surface px-5 py-4 text-sm text-rc-fg">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-rc-accent text-white">
            <Check className="h-3 w-3" strokeWidth={3} aria-hidden />
          </span>
          {read.dms ?? 0} DM dan {read.comments ?? 0} komentar baru dibaca
        </section>
      ) : null}

      {read?.error ? (
        <p role="alert" className="rounded-lg bg-amber-50 px-4 py-2.5 text-sm text-amber-800">
          {read.error}
        </p>
      ) : null}

      {agent.run ? <AgentRunPanel run={agent.run} running={agent.running} onStop={agent.requestStop} /> : null}

      {phase === "done" ? (
        <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rc-border bg-rc-surface px-5 py-4">
          <div>
            <p className="text-sm font-semibold text-rc-fg">{error ? "Belum selesai" : "Selesai"}</p>
            <p className="text-sm text-rc-fg-muted">{error || summary || "Tidak ada pesan baru."} Buka Workspace untuk meninjau hasilnya.</p>
          </div>
          <Button purpose="nav" href="/dashboard/inbox" style="primary" className="gap-1.5">
            Buka Workspace
            <ArrowRight aria-hidden className="h-4 w-4" />
          </Button>
        </section>
      ) : null}
    </div>
  );
}
