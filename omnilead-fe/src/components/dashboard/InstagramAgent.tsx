"use client";

import { useEffect, useState } from "react";
import { ArrowRight, Check, Loader2, MailCheck, MailOpen, Play, ShieldCheck } from "lucide-react";
import { api, type BrowserPermission, type InstagramSync, type PendingThread } from "@/lib/api";
import { Button } from "@/components/action/button";
import { ChannelIcon } from "@/components/primitives";
import { AgentRunPanel, useAgentRun } from "@/components/dashboard/AgentRun";

type Phase = "idle" | "reading" | "answering" | "done";
type Pending = Partial<Record<BrowserPermission, PendingThread[]>>;

const PERMISSION_COPY: Record<BrowserPermission, { title: (n: number) => string; detail: string; icon: typeof MailOpen }> = {
  read_unread: {
    title: (n) => `Buka ${n} DM yang belum dibaca`,
    detail: "Pengirim akan melihat pesannya sudah dibaca.",
    icon: MailOpen,
  },
  accept_request: {
    title: (n) => `Terima ${n} permintaan pesan`,
    detail: "Percakapan pindah ke kotak masuk Utama sehingga agen bisa membalas.",
    icon: MailCheck,
  },
};

function waiting(pending?: Pending): Pending | null {
  const kinds = (Object.keys(PERMISSION_COPY) as BrowserPermission[]).filter((k) => pending?.[k]?.length);
  return kinds.length ? Object.fromEntries(kinds.map((k) => [k, pending![k]])) : null;
}

function names(threads: PendingThread[]): string {
  const shown = threads.slice(0, 4).map((t) => t.name).join(", ");
  return threads.length > 4 ? `${shown}, dan ${threads.length - 4} lainnya` : shown;
}

export function InstagramAgent({ onFinished }: { onFinished: () => Promise<void> }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [read, setRead] = useState<InstagramSync | null>(null);
  const [answered, setAnswered] = useState(0);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<Pending | null>(null);
  const agent = useAgentRun(onFinished);

  useEffect(() => {
    api.instagramSyncStatus().then((s) => setPending(waiting(s.pending))).catch(() => undefined);
  }, []);

  async function start(allow: BrowserPermission[] = []) {
    setError("");
    setRead(null);
    setAnswered(0);
    setPending(null);
    setPhase("reading");
    try {
      const synced = await api.instagramSync(true, true, allow);
      setRead(synced);
      setPending(waiting(synced.pending));
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
        {/* <p className="mt-3 text-xs text-rc-fg-muted">
          Membuka Instagram lewat OpenClaw di komputer ini. Pastikan gateway sudah jalan (`tools/openclaw/start.sh`).
        </p> */}
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

      {pending && !busy ? (
        <section className="rounded-xl border border-rc-accent bg-rc-accent-soft p-5">
          <div className="flex items-start gap-3">
            <ShieldCheck aria-hidden className="mt-0.5 h-5 w-5 shrink-0 text-rc-accent" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-rc-fg">Agen butuh izin Anda</p>
              <p className="mt-1 text-sm text-rc-fg-muted">Mode Hybrid aktif. Setelah diizinkan, agen langsung membaca dan menyiapkan balasan.</p>
              <ul className="mt-4 flex flex-col gap-3">
                {(Object.keys(pending) as BrowserPermission[]).map((kind) => {
                  const copy = PERMISSION_COPY[kind];
                  const Icon = copy.icon;
                  const threads = pending[kind] ?? [];
                  return (
                    <li key={kind} className="flex items-start gap-3">
                      <Icon aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-rc-fg-muted" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-rc-fg">{copy.title(threads.length)}</p>
                        <p className="text-sm text-rc-fg-muted">{copy.detail}</p>
                        <p className="mt-0.5 truncate text-xs text-rc-fg-muted">{names(threads)}</p>
                      </div>
                    </li>
                  );
                })}
              </ul>
              <div className="mt-5 flex flex-wrap gap-2">
                <Button
                  purpose="action"
                  style="primary"
                  className="gap-1.5"
                  onClick={() => void start(Object.keys(pending) as BrowserPermission[])}
                >
                  <Check aria-hidden className="h-4 w-4" />
                  Izinkan dan baca
                </Button>
                <Button purpose="action" onClick={() => setPending(null)}>
                  Nanti saja
                </Button>
              </div>
            </div>
          </div>
        </section>
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
