"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent, type CSSProperties } from "react";
import { CalendarClock, Check, ChevronDown, ClipboardList, Loader2, Pause, Play, Plus, RefreshCw, X } from "lucide-react";
import { api } from "@/lib/api";
import { scheduleLabels, taskDate, taskStatusLabels, type AgentTask, type TaskBoard, type TaskSchedule } from "@/lib/agent-tasks";
import type { Channel } from "@/lib/types";
import { channelLabel, cn } from "@/lib/ui";

const CHANNELS: Channel[] = ["instagram", "whatsapp", "facebook", "email"];
const smallButton = "inline-flex items-center gap-1.5 rounded-lg border border-rc-border px-2.5 py-1.5 text-xs text-rc-fg-muted hover:bg-rc-surface-hover disabled:opacity-40";

function TaskCard({ task, mutate, busy, scheduled = false }: {
  task: AgentTask; mutate: (id: string, operation: "run" | "pause" | "resume" | "complete") => void; busy: boolean; scheduled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return <article className="rounded-xl border border-rc-border bg-rc-surface p-3.5 shadow-sm">
    <div className="mb-2 flex flex-wrap items-center gap-1.5">
      {task.channels.map((channel) => <span key={channel} className="rounded-md bg-rc-surface-hover px-1.5 py-0.5 text-[10px] font-medium text-rc-fg-muted">{channelLabel[channel]}</span>)}
      {task.status === "running" && <Loader2 className="ml-auto h-3.5 w-3.5 animate-spin text-rc-accent" aria-label="Sedang berjalan" />}
    </div>
    <h3 className="break-words text-sm font-semibold leading-snug">{task.title}</h3>
    <p className="mt-1.5 line-clamp-3 break-words text-xs leading-relaxed text-rc-fg-muted">{task.instruction}</p>
    <p className={cn("mt-3 text-[11px]", task.status === "blocked" ? "text-rc-danger" : "text-rc-fg-muted")}>{taskStatusLabels[task.status]}{task.next_run_at && ` · ${taskDate(task.next_run_at)}`}</p>
    {scheduled && <div className="mt-2 space-y-1 rounded-lg bg-rc-bg p-2 text-xs text-rc-fg-muted"><p>{scheduleLabels[task.schedule]}</p>{task.cron && <code className="block font-mono">{task.cron} · WIB</code>}</div>}
    {task.result && <p className="mt-2 line-clamp-4 break-words text-xs leading-relaxed text-rc-fg-muted">{task.result}</p>}
    <div className="mt-3 flex flex-wrap gap-1.5">
      {["todo", "scheduled", "blocked"].includes(task.status) && <button disabled={busy} onClick={() => mutate(task.id, "run")} className={smallButton}><Play className="h-3 w-3" />Jalankan</button>}
      {["scheduled", "todo", "blocked"].includes(task.status) && <button disabled={busy} aria-label={`Jeda ${task.title}`} onClick={() => mutate(task.id, "pause")} className={smallButton}><Pause className="h-3 w-3" /></button>}
      {task.status === "paused" && <button disabled={busy} onClick={() => mutate(task.id, "resume")} className={smallButton}><Play className="h-3 w-3" />Aktifkan</button>}
      {!["running", "done"].includes(task.status) && <button disabled={busy} aria-label={`Tandai selesai ${task.title}`} onClick={() => mutate(task.id, "complete")} className={smallButton}><Check className="h-3 w-3" /></button>}
      {task.events.length > 0 && <button onClick={() => setOpen(!open)} aria-expanded={open} className={smallButton}>Proses<ChevronDown className={cn("h-3 w-3", open && "rotate-180")} /></button>}
    </div>
    {open && <ol className="mt-3 max-h-80 space-y-2 overflow-auto border-t border-rc-border pt-3 text-xs">
      {task.events.map((event, i) => <li key={i} className="break-words">
        {event.type === "thoughts" ? <span className="whitespace-pre-wrap text-rc-fg-muted">{event.text}</span> :
          event.type === "step" ? <details><summary className="cursor-pointer font-medium">{event.label} · {event.tool}</summary><pre className="overflow-auto text-[10px]">{JSON.stringify(event.args, null, 2)}</pre></details> :
          event.type === "tool_result" ? <p className={event.ok ? "text-rc-fg-muted" : "text-rc-danger"}>{event.summary}</p> :
          event.type === "tool_progress" ? <p className="text-rc-fg-muted">{event.label} · {event.elapsed_s} dtk</p> :
          event.type === "error" ? <p className="text-rc-danger">{event.message}</p> : <p className="whitespace-pre-wrap">{event.text}</p>}
      </li>)}
    </ol>}
  </article>;
}

export function AgentWorkPanel({ onClose, revision, channel = "instagram", width = 480 }: { onClose: () => void; revision: number; channel?: Channel; width?: number }) {
  const [board, setBoard] = useState<TaskBoard | null>(null);
  const [view, setView] = useState<"board" | "schedule">("board");
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [schedule, setSchedule] = useState<TaskSchedule>("manual");
  const inflight = useRef(false);
  const refresh = useCallback(async () => {
    if (inflight.current) return;
    inflight.current = true;
    try { setBoard(await api.agentTasks()); setError(""); }
    catch (e) { setError(e instanceof Error ? e.message : "Papan tugas belum bisa dimuat"); }
    finally { inflight.current = false; }
  }, []);
  useEffect(() => {
    const first = setTimeout(() => void refresh(), 0);
    const poll = setInterval(() => { if (document.visibilityState === "visible") void refresh(); }, 3000);
    return () => { clearTimeout(first); clearInterval(poll); };
  }, [refresh, revision]);

  async function mutate(id: string, operation: "run" | "pause" | "resume" | "complete") {
    setBusy(true); setError("");
    try {
      if (operation === "run") await api.runAgentTask(id);
      else await api.changeAgentTask(id, operation);
      await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Tugas belum bisa diperbarui"); }
    finally { setBusy(false); }
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const at = String(data.get("at") || "");
    setBusy(true); setError("");
    try {
      if (data.getAll("channels").length === 0) throw new Error("Pilih setidaknya satu platform tujuan.");
      await api.createAgentTask({ title: String(data.get("title")), instruction: String(data.get("instruction")),
        channels: data.getAll("channels") as Channel[], schedule,
        // The datetime input is explicitly WIB, independent of the browser's local timezone.
        at: at ? new Date(`${at}:00+07:00`).toISOString() : null,
        time: String(data.get("time") || "09:00"), weekday: Number(data.get("weekday") || 1) });
      setCreating(false); setSchedule("manual"); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "Tugas belum dapat disimpan"); }
    finally { setBusy(false); }
  }
  const tasks = board?.tasks ?? [];
  const columns = [
    { title: "To-do", statuses: ["todo", "scheduled", "paused"], dot: "bg-rc-fg-subtle" },
    { title: "Dikerjakan", statuses: ["running", "blocked"], dot: "bg-rc-highlight" },
    { title: "Selesai", statuses: ["done"], dot: "bg-emerald-500" },
  ];
  return <aside aria-label="Papan kerja agen" style={{ "--agent-board-width": `${width}px` } as CSSProperties} className="absolute inset-0 z-20 flex min-h-0 flex-col border-l border-rc-border bg-rc-bg xl:static xl:w-[var(--agent-board-width)] xl:max-w-[65%] xl:shrink-0">
    <div className="flex items-center justify-between gap-2 border-b border-rc-border bg-rc-surface px-4 py-3">
      <div><h2 className="text-sm font-semibold">Papan kerja agen</h2><p className="mt-0.5 text-xs text-rc-fg-muted">Tugas, platform tujuan, dan jadwal</p></div>
      <button onClick={onClose} aria-label="Tutup papan kerja" className="rounded-lg p-2 hover:bg-rc-surface-hover"><X className="h-4 w-4" /></button>
    </div>
    <div className="flex flex-wrap items-center gap-2 border-b border-rc-border px-4 py-3">
      <div className="flex rounded-lg bg-rc-surface-hover p-1">
        {(["board", "schedule"] as const).map((tab) => <button key={tab} onClick={() => setView(tab)} aria-pressed={view === tab} className={cn("flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs", view === tab ? "bg-rc-surface font-medium shadow-sm" : "text-rc-fg-muted")}>{tab === "board" ? <ClipboardList className="h-3.5 w-3.5" /> : <CalendarClock className="h-3.5 w-3.5" />}{tab === "board" ? "Board" : "Jadwal & cron"}</button>)}
      </div>
      <button onClick={() => setCreating(!creating)} aria-expanded={creating} className={cn(smallButton, "ml-auto bg-rc-surface")}><Plus className="h-3.5 w-3.5" />Tugas</button>
      <button onClick={() => void refresh()} aria-label="Muat ulang papan kerja" className="rounded-lg p-1.5 text-rc-fg-muted hover:bg-rc-surface-hover"><RefreshCw className="h-3.5 w-3.5" /></button>
    </div>
    <div className="rc-scrollbar min-h-0 flex-1 overflow-y-auto p-4">
      <p className="mb-3 text-[11px] leading-relaxed text-rc-fg-muted">{view === "board" ? "Semua tugas berdasarkan status pengerjaannya. Tugas terjadwal juga tampil di sini." : "Tugas yang memiliki waktu jalan atau pengulangan. Data tugasnya sama dengan Board."}</p>
      {error && <p role="alert" className="mb-3 rounded-lg bg-red-50 p-3 text-xs text-red-700">{error}</p>}
      {creating && <form onSubmit={(e) => void create(e)} className="mb-4 space-y-3 rounded-xl border border-rc-border bg-rc-surface p-4 text-xs">
        <h3 className="font-semibold">Tugas baru</h3>
        <label className="block">Judul<input name="title" required maxLength={120} placeholder="Cek pesan pelanggan" className="mt-1 w-full rounded-lg border border-rc-border bg-transparent px-3 py-2 text-sm" /></label>
        <label className="block">Instruksi untuk agen<textarea name="instruction" required maxLength={1000} rows={3} placeholder="Baca DM baru dan siapkan draf balasan." className="mt-1 w-full resize-y rounded-lg border border-rc-border bg-transparent px-3 py-2 text-sm" /></label>
        <fieldset><legend className="mb-2">Platform tujuan</legend><div className="flex flex-wrap gap-3">{CHANNELS.map((c) => <label key={c} className="flex items-center gap-1.5"><input name="channels" type="checkbox" value={c} defaultChecked={c === channel} />{channelLabel[c]}</label>)}</div><p className="mt-2 text-rc-fg-muted">Eksekusi saat ini tersedia untuk Instagram. Kanal lain dapat dicatat sebagai rencana.</p></fieldset>
        <label className="block">Jadwal<select aria-label="Jadwal tugas" value={schedule} onChange={(e) => setSchedule(e.target.value as TaskSchedule)} className="mt-1 w-full rounded-lg border border-rc-border bg-transparent px-3 py-2">{Object.entries(scheduleLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        {schedule === "once" && <label className="block">Tanggal dan jam (WIB)<input name="at" type="datetime-local" required className="mt-1 w-full rounded-lg border border-rc-border p-2" /></label>}
        {(schedule === "daily" || schedule === "weekly") && <label className="block">Jam (WIB)<input name="time" type="time" required defaultValue="09:00" className="ml-2 rounded-lg border border-rc-border p-2" /></label>}
        {schedule === "weekly" && <label className="block">Hari<select name="weekday" defaultValue="1" className="ml-2 rounded-lg border border-rc-border p-2">{["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"].map((day, i) => <option key={day} value={i}>{day}</option>)}</select></label>}
        <div className="flex justify-end gap-2"><button type="button" onClick={() => setCreating(false)} className={smallButton}>Batal</button><button disabled={busy} className="rounded-lg bg-rc-accent px-3 py-2 text-white disabled:opacity-40">{busy ? "Menyimpan…" : "Simpan tugas"}</button></div>
      </form>}
      {!board && !error && <p role="status" className="p-4 text-sm text-rc-fg-muted">Memuat papan kerja…</p>}
      {board && tasks.length === 0 && <div className="rounded-xl border border-dashed border-rc-border-strong p-7 text-center"><ClipboardList className="mx-auto mb-3 h-7 w-7 text-rc-fg-subtle" /><p className="text-sm font-medium">Belum ada tugas</p><p className="mt-2 text-xs leading-relaxed text-rc-fg-muted">Buat di sini atau bilang di chat: “Jadwalkan cek DM Instagram setiap hari jam 09.00 WIB.”</p><button onClick={() => setCreating(true)} className={cn(smallButton, "mt-4")}>Buat tugas pertama</button></div>}
      {tasks.length > 0 && view === "board" && <div className="grid grid-cols-1 items-start gap-3 sm:grid-cols-3">
        {columns.map((column) => <section key={column.title} className="min-w-0"><h3 className="mb-3 flex items-center gap-2 text-xs font-semibold"><span className={cn("h-2 w-2 rounded-full", column.dot)} />{column.title}<span className="ml-auto text-rc-fg-subtle">{tasks.filter((t) => column.statuses.includes(t.status)).length}</span></h3><div className="space-y-3">{tasks.filter((t) => column.statuses.includes(t.status)).map((task) => <TaskCard key={task.id} task={task} mutate={(...args) => void mutate(...args)} busy={busy} />)}</div></section>)}
      </div>}
      {view === "schedule" && tasks.length > 0 && <div className="space-y-3">
        <p className="text-xs leading-relaxed text-rc-fg-muted">{board?.scheduler === "local" ? "Scheduler lokal memeriksa tugas setiap 15 detik selama backend berjalan." : "Jadwal menunggu pemicu scheduler cloud. Menyimpan jadwal belum mengaktifkan pemicu cloud."} Semua jam ditampilkan dalam WIB.</p>
        {tasks.filter((t) => t.schedule !== "manual").sort((a, b) => (a.next_run_at ?? "z").localeCompare(b.next_run_at ?? "z")).map((task) => <TaskCard key={task.id} task={task} mutate={(...args) => void mutate(...args)} busy={busy} scheduled />)}
        {tasks.every((t) => t.schedule === "manual") && <p className="rounded-xl border border-dashed border-rc-border p-6 text-center text-sm text-rc-fg-muted">Belum ada tugas terjadwal.</p>}
      </div>}
    </div>
  </aside>;
}
