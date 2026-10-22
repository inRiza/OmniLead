"use client";

import { useState } from "react";
import { ArrowRight, Check, Loader2, Play } from "lucide-react";
import { api, type InstagramSync } from "@/lib/api";
import { Button } from "@/components/action/button";
import { ChannelIcon } from "@/components/primitives";
import { AgentRunPanel, useAgentRun } from "@/components/dashboard/AgentRun";

type Phase = "idle" | "reading" | "answering" | "done";

export function InstagramAgent({ onFinished }: { onFinished: () => Promise<void> }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [read, setRead] = useState<InstagramSync | null>(null);
  const [answered, setAnswered] = useState(0);
  const [error, setError] = useState("");
  const agent = useAgentRun(onFinished);

  async function start() {
    setError("");
    setRead(null);
    setAnswered(0);
    setPhase("reading");
    try {
      const synced = await api.instagramSync(true, true);
      setRead(synced);
      const queued = new Set(synced.queued ?? []);
      const events = await api.events();
      const targets = (synced.queued ?? [])
        .map((id) => events.find((e) => e.id === id))
        .filter((e) => e && queued.has(e.id))
        .map((e) => ({ id: e!.id, name: e!.sender.name || e!.sender.handle || "Pelanggan" }));
      setAnswered(targets.length);
      if (targets.length) {
        setPhase("answering");
        void onFinished();
        await agent.start(targets, true);
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
        <p className="mt-3 text-xs text-rc-fg-muted">
          Membuka Instagram lewat OpenClaw di komputer ini. Pastikan gateway sudah jalan (`tools/openclaw/start.sh`).
        </p>
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
        <p role="alert" className="rounded-lg border border-rc-border bg-rc-surface px-4 py-2.5 text-sm text-rc-fg-muted">
          {read.error}
        </p>
      ) : null}

      {phase === "answering" ? (
        <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-rc-border bg-rc-surface px-5 py-4">
          <p className="text-sm text-rc-fg-muted">Hasil analisis muncul satu per satu di Workspace selagi agen bekerja.</p>
          <Button purpose="nav" href="/dashboard/inbox" className="gap-1.5">
            Lihat di Workspace
            <ArrowRight aria-hidden className="h-4 w-4" />
          </Button>
        </section>
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
