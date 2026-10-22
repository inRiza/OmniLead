"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { channelLabel, cn } from "@/lib/ui";
import { ChannelIcon } from "@/components/primitives";
import { TimeAgo } from "@/components/TimeAgo";
import { Button } from "@/components/action/button";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { ActivityDetail } from "@/components/dashboard/ActivityDetail";
import { AgentActivity, agentStatus } from "@/components/dashboard/AgentActivity";
import { AgentResults } from "@/components/dashboard/AgentResults";
import { PasteMessage } from "@/components/dashboard/PasteMessage";

type Filter = "all" | "working" | "waiting" | "error";
const FILTERS: [Filter, string][] = [["all", "Semua"], ["working", "Sedang berjalan"], ["waiting", "Perlu keputusan"], ["error", "Perlu ditangani"]];
const OPEN_ACTION = new Set(["pending", "awaiting_manual_send", "failed"]);
const OUTCOME: Record<string, string> = { approved: "Disetujui", edited: "Disetujui dengan perubahan", executing: "Sedang dijalankan", executed: "Selesai dijalankan", rejected: "Ditolak", sent_manually: "Ditandai sudah dikirim manual" };

export default function AgentPage() {
  const d = useDashboard();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [pasting, setPasting] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [error, setError] = useState("");
  const actionsFor = (id: string) => d.actions.filter((a) => a.activityId === id);
  const isWorking = (status: string) => status === "processing" || status === "new";
  const rows = d.activities.filter((a) => filter === "all"
    || (filter === "working" && isWorking(a.eventStatus))
    || (filter === "waiting" && (a.eventStatus === "review" || actionsFor(a.id).some((item) => item.status === "pending")))
    || (filter === "error" && (["agent_error", "held"].includes(a.eventStatus) || actionsFor(a.id).some((item) => item.status === "failed"))));
  const selected = rows.find((a) => a.id === selectedId) ?? rows.find((a) => isWorking(a.eventStatus)) ?? rows[0];
  const actions = selected ? actionsFor(selected.id) : [];
  const trace = selected ? d.traces[selected.id] : undefined;
  const lead = selected ? d.leadsById[selected.leadId] : undefined;
  const workingCount = d.activities.filter((a) => isWorking(a.eventStatus)).length;
  const waitingCount = d.activities.filter((a) => actionsFor(a.id).some((item) => item.status === "pending")).length;
  const state = !d.loaded ? "Menghubungkan…" : d.error ? "Pembaruan terputus" : !d.agent?.reachable ? "Agent tidak terjangkau" : d.paused ? "Agent dijeda" : "Memantau pesan masuk";

  async function retry() {
    if (!selected) return;
    setRetrying(true); setError("");
    try { await api.reanalyze(selected.id); await d.refresh(); }
    catch (e) { setError(e instanceof Error ? e.message : "Gagal memproses ulang pesan"); }
    finally { setRetrying(false); }
  }

  return <>
    <Topbar title="Aktivitas agen" subtitle="Ikuti proses pesan, tool yang dijalankan, dan usulan balasan untuk bisnis ini." />
    <ContentInset className="rc-scrollbar overflow-y-auto">
      <div className="mx-auto w-full max-w-6xl space-y-5 pt-1 pb-10">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rc-border bg-rc-surface p-4">
          <div>
            <p role="status" className="flex items-center gap-2 text-sm font-semibold text-rc-fg"><span className={`h-2 w-2 rounded-full ${d.error || !d.agent?.reachable ? "bg-rc-danger" : "bg-rc-fg"}`} />{state}</p>
            <p className="mt-1 text-xs text-rc-fg-muted">Pembaruan setiap 3 detik · {workingCount} diproses · {waitingCount} pesan menunggu persetujuan</p>
            <p className="mt-1 text-xs text-rc-fg-muted">{d.channels.filter((channel) => channel.connected).length} kanal terhubung · {d.activities.length} pesan dalam riwayat yang dimuat</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button purpose="action" style="secondary" onClick={() => void d.refresh()}>Muat ulang</Button>
            <Button purpose="action" style={pasting ? "secondary" : "primary"} onClick={() => setPasting((v) => !v)}>{pasting ? "Tutup formulir" : "Tempel pesan"}</Button>
          </div>
        </div>

        {pasting && <PasteMessage onCreated={(id) => { setSelectedId(id); setFilter("all"); setPasting(false); }} />}
        <div className="flex flex-wrap gap-2" role="group" aria-label="Filter aktivitas agen">{FILTERS.map(([value, label]) => <button key={value} type="button" aria-pressed={filter === value} onClick={() => setFilter(value)} className={cn("rounded-md border px-3 py-1.5 text-sm", filter === value ? "border-rc-accent bg-rc-accent-soft text-rc-accent" : "border-rc-border text-rc-fg-muted hover:bg-rc-surface-hover")}>{label}</button>)}</div>

        {!d.loaded ? <p role="status" className="py-10 text-center text-sm text-rc-fg-muted">Memuat aktivitas agen…</p>
          : !rows.length ? <div className="rounded-lg border border-rc-border bg-rc-surface p-8 text-center">
            <h2 className="text-base font-semibold text-rc-fg">{filter === "all" ? "Belum ada pesan yang diterima" : "Tidak ada aktivitas pada filter ini"}</h2>
            <p className="mx-auto mt-2 max-w-lg text-sm text-rc-fg-muted">{filter === "all" ? "Setelah pesan masuk melalui kanal yang terhubung, prosesnya muncul di sini. Anda juga bisa menempel pesan untuk melihat agen bekerja." : "Pilih Semua untuk melihat riwayat proses pesan."}</p>
            {filter === "all" && <Link href="/dashboard/integrasi" className="mt-4 inline-block text-sm font-medium text-rc-fg underline underline-offset-4">Lihat koneksi kanal</Link>}
          </div> : <div className="grid min-w-0 items-start gap-5 xl:grid-cols-[minmax(240px,320px)_minmax(0,1fr)]">
            <div className="max-h-96 space-y-2 overflow-y-auto xl:max-h-[72vh]" aria-label="Daftar proses pesan">
              {rows.map((item) => <button key={item.id} type="button" aria-pressed={selected?.id === item.id} onClick={() => { setSelectedId(item.id); setError(""); }} className={cn("w-full rounded-lg border bg-rc-surface p-4 text-left", selected?.id === item.id ? "border-rc-fg" : "border-rc-border hover:bg-rc-surface-hover")}>
                <span className="flex items-center gap-2 text-sm font-semibold text-rc-fg"><ChannelIcon channel={item.channel} /><span className="min-w-0 flex-1 truncate">{item.authorName}</span></span>
                <p className="mt-2 line-clamp-2 break-words text-sm text-rc-fg-muted">{item.text}</p>
                <p className="mt-3 flex items-center gap-2 text-xs font-medium text-rc-fg">{isWorking(item.eventStatus) && <span className="h-1.5 w-1.5 rounded-full bg-rc-fg motion-safe:animate-pulse" />}{agentStatus(item, actionsFor(item.id))}</p>
                <p className="mt-1 text-xs text-rc-fg-subtle">{channelLabel[item.channel]} · <TimeAgo iso={item.receivedAt} /></p>
              </button>)}
            </div>
            {selected && <div className="min-w-0 space-y-5">
              {lead ? <ActivityDetail activity={selected} lead={lead} trace={trace} /> : <AgentActivity activity={selected} trace={trace} actions={actions} />}
              {selected.eventStatus === "agent_error" && <Button purpose="action" style="secondary" disabled={retrying || d.paused} onClick={retry}>{retrying ? "Memulai ulang…" : "Proses ulang pesan"}</Button>}
              {error && <p role="alert" className="text-sm text-rc-danger">{error}</p>}
              <section><h2 className="mb-2 text-base font-semibold text-rc-fg">Usulan &amp; draf balasan</h2>
                {isWorking(selected.eventStatus) && !actions.length ? <p className="rounded-lg border border-dashed border-rc-border p-4 text-sm text-rc-fg-muted">Agen sedang menyiapkan usulan. Draf yang selesai diperiksa akan muncul di sini.</p> : <AgentResults actions={actions} onFeedback={d.reject} onApprove={d.approve} onSent={d.markSent} onRetry={d.retry} />}
              </section>
              {actions.some((a) => !OPEN_ACTION.has(a.status)) && <section className="space-y-3"><h2 className="text-base font-semibold text-rc-fg">Hasil tindakan</h2>{actions.filter((a) => !OPEN_ACTION.has(a.status)).map((action) => <div key={action.id} className="rounded-lg border border-rc-border bg-rc-surface p-4">
                <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-sm font-semibold text-rc-fg">{action.title}</h3><span className="text-xs text-rc-fg-muted">{OUTCOME[action.status] ?? action.status}</span></div>
                {action.text && <p className="mt-2 whitespace-pre-wrap break-words text-sm text-rc-fg">{action.text}</p>}
                {action.reason && <p className="mt-2 text-sm text-rc-fg-muted">Alasan usulan: {action.reason}</p>}
              </div>)}</section>}
            </div>}
          </div>}
      </div>
    </ContentInset>
  </>;
}
