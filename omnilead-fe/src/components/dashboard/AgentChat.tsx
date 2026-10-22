"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, Bot, Check, ChevronDown, CircleX, Copy, History, ListTodo, Loader2, MessageSquarePlus, RotateCcw, Square, Wrench } from "lucide-react";
import { applyEvent, finishTurn, streamChat, type ChatTurn, type ConversationSummary, type ToolStep } from "@/lib/chat";
import { api, ApiError } from "@/lib/api";
import { channelLabel, cn } from "@/lib/ui";
import type { Channel } from "@/lib/types";
import { useDashboard } from "./DashboardContext";
import { useAccount } from "./AccountProvider";
import { AgentWorkPanel } from "./AgentWorkPanel";
import { AgentConversationSidebar } from "./AgentConversationSidebar";

const SUGGESTIONS = [
  { title: "Cek pesan masuk", text: "Cek DM dan komentar Instagram baru" },
  { title: "Prioritaskan prospek", text: "Siapa lead yang paling panas?" },
  { title: "Lihat pekerjaan agen", text: "Tampilkan tugas dan jadwal agen yang tersimpan" },
];
const newTurn = (role: ChatTurn["role"], text = ""): ChatTurn => ({ id: crypto.randomUUID(), role, text, steps: [], error: "", done: role === "user" });
const iconButton = "inline-flex shrink-0 items-center justify-center gap-2 rounded-lg p-2 text-rc-fg-muted transition-colors hover:bg-rc-surface-hover hover:text-rc-fg focus-visible:outline-2 focus-visible:outline-rc-accent disabled:opacity-40";

function StepIcon({ status }: { status: ToolStep["status"] }) {
  if (status === "running") return <Loader2 className="h-4 w-4 animate-spin text-rc-accent" aria-label="Sedang berjalan" />;
  if (status === "failed") return <CircleX className="h-4 w-4 text-rc-danger" aria-label="Gagal" />;
  if (status === "stopped") return <Square className="h-3.5 w-3.5 text-rc-fg-subtle" aria-label="Pemantauan dihentikan" />;
  return <Check className="h-4 w-4 text-emerald-600" aria-label="Selesai" />;
}

function Thinking({ text, live = false }: { text?: string; live?: boolean }) {
  if (!text) return null;
  return <details open={live || undefined} className="rounded-xl bg-rc-bg px-3 py-2 text-xs text-rc-fg-muted">
    <summary className="cursor-pointer select-none font-medium">{live ? "Sedang mempertimbangkan langkah…" : "Ringkasan pemikiran model"}</summary>
    <p className="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap break-words leading-relaxed">{text}</p>
  </details>;
}

function StepCard({ step }: { step: ToolStep }) {
  return <li className="space-y-2 border-l border-rc-border pl-4">
    <div className="flex items-start gap-2"><span className="mt-0.5"><StepIcon status={step.status} /></span><div className="min-w-0 flex-1">
      <p className="text-sm font-medium">{step.label}{step.status === "running" && "…"}</p>
      {step.say && <p className="mt-1 text-xs leading-relaxed text-rc-fg-muted">{step.say}</p>}
      {step.progress && step.status === "running" && <p role="status" className="mt-2 text-xs text-rc-accent">{step.progress}{step.elapsed !== undefined && ` · ${step.elapsed} dtk`}</p>}
      {step.summary && <p className={cn("mt-2 text-sm leading-relaxed", step.status === "failed" ? "text-rc-danger" : "text-rc-fg-muted")}>{step.summary}</p>}
    </div></div>
    <Thinking text={step.thoughts} />
    <details className="text-xs text-rc-fg-muted"><summary className="flex cursor-pointer list-none items-center gap-1.5"><Wrench className="h-3 w-3" /><code>{step.tool}</code><ChevronDown className="h-3 w-3" /></summary>
      <div className="mt-2 overflow-hidden rounded-lg border border-rc-border"><p className="border-b border-rc-border bg-rc-bg px-3 py-1.5 font-medium">Argumen</p>
        <pre className="max-h-40 overflow-auto whitespace-pre-wrap break-all p-3 font-mono text-[11px]">{JSON.stringify(step.args, null, 2)}</pre>
        {Object.keys(step.data).length > 0 && <><p className="border-y border-rc-border bg-rc-bg px-3 py-1.5 font-medium">Hasil tool</p><pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all p-3 font-mono text-[11px]">{JSON.stringify(step.data, null, 2)}</pre></>}
      </div>
    </details>
  </li>;
}

function AgentTurn({ turn, retry, busy }: { turn: ChatTurn; retry: () => void; busy: boolean }) {
  const [expanded, setExpanded] = useState<boolean | null>(null);
  const [copied, setCopied] = useState(false);
  const working = !turn.done;
  const open = expanded ?? working;
  const running = turn.steps.find((s) => s.status === "running");
  const label = running?.label || (working ? turn.steps.length ? "Merangkum hasil" : "Menyiapkan langkah" : `${turn.steps.length} langkah selesai`);
  async function copy() {
    try { await navigator.clipboard.writeText(turn.text); setCopied(true); } catch { setCopied(false); }
  }
  return <article className="min-w-0 space-y-4" aria-label="Jawaban agen" aria-busy={working}>
    <div className="flex items-center gap-2 text-xs font-semibold text-rc-fg-muted"><Bot className="h-4 w-4 text-rc-accent" />OmniLead</div>
    {(working || turn.steps.length > 0) && <div className="rounded-xl border border-rc-border bg-rc-surface">
      <button onClick={() => setExpanded(!open)} aria-expanded={open} className="flex w-full items-center gap-2.5 px-3.5 py-3 text-left text-xs text-rc-fg-muted">
        {working ? <Loader2 className="h-3.5 w-3.5 animate-spin text-rc-accent" /> : <Check className="h-3.5 w-3.5" />}<span role="status" className="flex-1">{turn.error ? "Proses terhenti" : label}</span><ChevronDown className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")} />
      </button>
      {open && <div className="space-y-3 border-t border-rc-border px-3.5 py-4">
        {turn.steps.length > 0 && <ol className="space-y-4">{turn.steps.map((s, i) => <StepCard key={i} step={s} />)}</ol>}
        <Thinking text={turn.thinking} live={working} />
        {working && turn.narration && <p className="whitespace-pre-wrap text-sm leading-relaxed text-rc-fg-muted">{turn.narration}</p>}
        {working && !running && !turn.thinking && !turn.narration && <p className="text-xs text-rc-fg-muted">Menunggu respons model…</p>}
      </div>}
    </div>}
    <Thinking text={turn.thoughts} />
    {turn.text && <div className="whitespace-pre-wrap break-words text-[15px] leading-7 text-rc-fg">{turn.text}</div>}
    {turn.error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{turn.error}</div>}
    {turn.done && <div className="flex items-center gap-1">
      {turn.text && <button onClick={() => void copy()} aria-label={copied ? "Jawaban disalin" : "Salin jawaban"} className={iconButton}>{copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}</button>}
      {turn.error && <button disabled={busy} onClick={retry} className={cn(iconButton, "text-xs")}><RotateCcw className="h-3.5 w-3.5" />Coba lagi</button>}
    </div>}
  </article>;
}

export function AgentChat({ onChanged, className }: { onChanged: () => Promise<void> | void; className?: string }) {
  const d = useDashboard();
  const { session } = useAccount();
  const business = session.user?.business || "bisnis Anda";
  const [selectedChannel, setSelectedChannel] = useState<Channel | "all">("all");
  const focusChannel = selectedChannel === "all" ? "instagram" : selectedChannel;
  const channelConfig = d.settings?.agent_channels?.[focusChannel];
  const storageKey = `omnilead.agent-chat.${session.user?.workspace_id || "legacy"}`;
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [restoring, setRestoring] = useState(true);
  const [sessionError, setSessionError] = useState("");
  const [historyVisible, setHistoryVisible] = useState(true);
  const [mobileHistory, setMobileHistory] = useState(false);
  const [boardWidth, setBoardWidth] = useState(480);
  const [resizing, setResizing] = useState(false);
  const shell = useRef<HTMLElement>(null);
  const drag = useRef<{ x: number; width: number } | null>(null);
  const widthKey = `omnilead.agent-board-width.${session.user?.workspace_id || "legacy"}`;
  function clampWidth(width: number) {
    const available = shell.current?.clientWidth || 1200;
    const historyWidth = historyVisible && window.innerWidth >= 1536 ? 224 : 0;
    return Math.max(320, Math.min(width, Math.max(320, available - historyWidth - 400)));
  }
  function saveWidth(width: number) {
    setBoardWidth(width);
    try { localStorage.setItem(widthKey, String(width)); } catch {}
  }
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [panel, setPanel] = useState(false);
  const [revision, setRevision] = useState(0);
  const [away, setAway] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const scroll = useRef<HTMLDivElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const anchored = useRef(true);
  const mounted = useRef(true);
  const creating = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; abort.current?.abort(); }; }, []);
  useEffect(() => {
    const timer = setTimeout(() => { try { const saved = Number(localStorage.getItem(widthKey)); if (saved >= 320 && saved <= 1600) setBoardWidth(saved); } catch {} }, 0);
    return () => clearTimeout(timer);
  }, [widthKey]);
  const refreshConversations = useCallback(async () => {
    try { const list = await api.conversations(); if (mounted.current) setConversations(list); }
    catch (e) { if (mounted.current) setSessionError(e instanceof Error ? e.message : "Riwayat belum bisa dimuat"); }
  }, []);
  useEffect(() => {
    let live = true;
    const timer = setTimeout(() => { void (async () => {
      try {
        const list = await api.conversations();
        if (!live) return;
        setConversations(list);
        let saved: string | null = null;
        try { saved = localStorage.getItem(storageKey); } catch { /* Private browser storage may be unavailable. */ }
        if (saved) {
          const previous = await api.conversation(saved);
          if (live) { setConversationId(previous.id); setTurns(previous.turns); setSelectedChannel(previous.channel || "all"); }
        }
      } catch (e) {
        if (live && !(e instanceof ApiError && e.status === 404)) setSessionError(e instanceof Error ? e.message : "Riwayat belum bisa dimuat");
      } finally { if (live) setRestoring(false); }
    })(); }, 0);
    return () => { live = false; clearTimeout(timer); };
  }, [storageKey]);
  const pendingRemote = turns.some((turn) => !turn.done) && !busy;
  useEffect(() => {
    if (!conversationId || !pendingRemote) return;
    const poll = setInterval(() => { void api.conversation(conversationId).then((saved) => { if (mounted.current) setTurns(saved.turns); }).catch(() => {}); }, 3000);
    return () => clearInterval(poll);
  }, [conversationId, pendingRemote]);
  async function selectConversation(id: string) {
    if (busy || creating.current) return;
    setRestoring(true); setSessionError("");
    try { const saved = await api.conversation(id); setConversationId(id); setTurns(saved.turns); setSelectedChannel(saved.channel || "all"); setValue(""); setMobileHistory(false); anchored.current = true; try { localStorage.setItem(storageKey, id); } catch {} }
    catch (e) { setSessionError(e instanceof Error ? e.message : "Percakapan belum dapat dibuka"); }
    finally { setRestoring(false); }
  }
  function startNew() {
    if (busy || creating.current) return;
    setTurns([]); setConversationId(null); setValue(""); setSessionError(""); setMobileHistory(false);
    try { localStorage.removeItem(storageKey); } catch {}
    field.current?.focus();
  }
  useEffect(() => { if (anchored.current && scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight; }, [turns]);
  useEffect(() => { if (field.current) { field.current.style.height = "auto"; field.current.style.height = `${Math.min(field.current.scrollHeight, 180)}px`; } }, [value]);

  const send = useCallback(async (raw: string) => {
    const text = raw.trim();
    if (!text || abort.current || restoring || pendingRemote || creating.current) return;
    creating.current = true;
    let active = conversationId;
    if (!active) {
      try {
        const saved = await api.createConversation();
        active = saved.id;
        if (!active) throw new Error("Percakapan belum dapat dibuat.");
        setConversationId(active);
        try { localStorage.setItem(storageKey, active); } catch {}
      } catch (e) { setSessionError(e instanceof Error ? e.message : "Percakapan belum dapat dibuat."); creating.current = false; return; }
    }
    creating.current = false; setSessionError("");
    const history = turns.filter((t) => t.text && !t.error).slice(-10).map((t) => ({ role: t.role, text: t.text }));
    const mine = newTurn("user", text), reply = newTurn("agent");
    anchored.current = true; setAway(false);
    setTurns((t) => [...t, mine, reply]); setValue(""); setBusy(true);
    const controller = new AbortController(); abort.current = controller;
    const patch = (fn: (t: ChatTurn) => ChatTurn) => { if (mounted.current) setTurns((all) => all.map((t) => t.id === reply.id ? fn(t) : t)); };
    let refresh = false;
    let refreshedTitle = false;
    try {
      await streamChat(text, history, (event) => {
        if (!refreshedTitle) { refreshedTitle = true; void refreshConversations(); }
        if (event.type === "tool_result" && event.refresh) refresh = true;
        if (event.type === "step" && ["buat_tugas", "ubah_tugas", "lihat_tugas"].includes(event.tool)) setPanel(true);
        if (event.type === "tool_result") setRevision((r) => r + 1);
        patch((turn) => applyEvent(turn, event));
      }, AbortSignal.any([controller.signal, AbortSignal.timeout(600_000)]), active, selectedChannel === "all" ? null : selectedChannel);
      patch((t) => t.done ? t : finishTurn(t, "Koneksi berakhir sebelum jawaban selesai. Anda bisa mencoba lagi."));
    } catch (e) {
      patch((t) => finishTurn(t, controller.signal.aborted ? "Pemantauan dihentikan. Langkah yang sudah dimulai di server dapat tetap selesai." : e instanceof DOMException && e.name === "TimeoutError" ? "Proses terlalu lama. Periksa aktivitas sebelum mencoba lagi." : e instanceof TypeError ? "Koneksi ke agen terputus. Periksa hasil langkah terakhir sebelum mencoba lagi." : e instanceof Error ? e.message : "Chat gagal."));
    } finally {
      if (mounted.current) { setBusy(false); setRevision((r) => r + 1); }
      abort.current = null;
      void refreshConversations();
      if (refresh) { try { await onChanged(); } catch { /* Dashboard owns refresh errors. */ } }
    }
  }, [turns, onChanged, restoring, pendingRemote, conversationId, storageKey, refreshConversations, selectedChannel]);

  const empty = turns.length === 0;
  const composer = <div className={cn("mx-auto w-full max-w-4xl px-4 pb-3 md:px-8", !empty && "pt-3")}>
    <form onSubmit={(e) => { e.preventDefault(); void send(value); }} className="rounded-2xl border border-rc-border-strong bg-rc-surface p-3 shadow-sm transition-shadow focus-within:border-rc-accent/50 focus-within:shadow-md">
      <textarea ref={field} value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => {
        if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(value); }
      }} rows={2} maxLength={1000} placeholder={`Apa yang ingin Anda kerjakan untuk ${business}?`} aria-label="Pesan untuk agen" className="rc-scrollbar max-h-44 min-h-16 w-full resize-none border-0 bg-transparent px-1 py-1 text-[15px] leading-6 text-rc-fg outline-none placeholder:text-rc-fg-subtle" />
      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="flex min-w-0 flex-wrap items-center gap-1.5">
          <select aria-label="Kanal percakapan" disabled={busy || pendingRemote} value={selectedChannel} onChange={(e) => setSelectedChannel(e.target.value as Channel | "all")} className="max-w-full rounded-lg border border-rc-border bg-rc-surface px-2 py-2 text-xs text-rc-fg-muted outline-none focus:border-rc-accent disabled:opacity-50">
            <option value="all">Otomatis · semua kanal</option>
            {(["instagram", "whatsapp", "facebook", "email"] as Channel[]).map((channel) => <option key={channel} value={channel}>{channelLabel[channel]}</option>)}
          </select>
          <button type="button" onClick={() => setPanel(true)} className={cn(iconButton, "px-2 text-xs")}><ListTodo className="h-4 w-4" /><span className="hidden sm:inline">Tugas & jadwal</span></button>
        </div>
        <div className="flex items-center gap-3"><span className="hidden text-[11px] text-rc-fg-subtle sm:block">{value.length > 850 ? `${value.length}/1000` : "Enter kirim · Shift+Enter baris baru"}</span>
          {busy ? <button type="button" onClick={() => abort.current?.abort()} aria-label="Hentikan pemantauan jawaban" className="flex h-9 w-9 items-center justify-center rounded-xl bg-rc-fg text-rc-surface"><Square className="h-3.5 w-3.5" /></button> : <button type="submit" disabled={!value.trim() || restoring || pendingRemote} aria-label="Kirim pesan" className="flex h-9 w-9 items-center justify-center rounded-xl bg-rc-accent text-white transition-opacity disabled:opacity-35"><ArrowUp className="h-4 w-4" /></button>}
        </div>
      </div>
    </form>
    {selectedChannel !== "all" && selectedChannel !== "instagram" && <p className="mt-2 text-center text-[11px] text-rc-fg-muted">{channelLabel[selectedChannel]}: perencanaan dan data yang sudah tersimpan tersedia; eksekusi inbox terjadwal belum tersedia.</p>}
    <p className="mt-2 text-center text-[10px] leading-relaxed text-rc-fg-subtle">{d.paused ? "Agen dijeda. Chat tetap tersedia; pelaksanaan tugas ditahan." : d.autonomy === "hybrid" ? "Balasan pelanggan menunggu persetujuan Anda di Workspace." : "Pengiriman mengikuti pengaturan otonomi dan pemeriksaan agen."}</p>
  </div>;

  return <section ref={shell} className={cn("relative flex min-h-0 min-w-0 flex-col overflow-hidden rounded-2xl border border-rc-border bg-rc-surface", resizing && "select-none", className)}>
    <div className="flex shrink-0 items-center gap-2 border-b border-rc-border px-3 py-2 md:px-5">
      <button onClick={() => { if (window.matchMedia("(min-width: 1024px)").matches) setHistoryVisible(!historyVisible); else setMobileHistory(true); }} aria-label="Buka riwayat percakapan" title="Buka/tutup percakapan" className={cn(iconButton, "mr-1 border border-rc-border")}><History className="h-4 w-4" /></button>
      <div className="min-w-0 flex-1"><p className="truncate text-xs font-medium">Ruang agen <span className="mx-1 text-rc-fg-subtle">/</span> {business}</p><Link href="/dashboard/integrasi" className="text-[11px] text-rc-fg-muted hover:underline">Kelola akun & koneksi kanal</Link></div>
      <button disabled={busy || restoring} onClick={startNew} title="Chat baru" aria-label="Mulai chat baru" className={iconButton}><MessageSquarePlus className="h-4 w-4" /></button>
      <button onClick={() => setPanel(!panel)} aria-label="Papan kerja" aria-expanded={panel} aria-controls="agent-work-panel" className={cn(iconButton, "border border-rc-border px-3 text-xs", panel && "bg-rc-accent-soft text-rc-accent")}><ListTodo className="h-4 w-4" /><span className="hidden sm:inline">Papan kerja</span></button>
    </div>
    <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-1 border-b border-rc-border bg-rc-bg/50 px-4 py-2 text-[11px] text-rc-fg-muted md:px-5">
      <span>{channelLabel[focusChannel]} · Bisnis: <strong className="font-medium text-rc-fg">{channelConfig?.business_name?.trim() || "Belum diatur"}</strong></span>
      <span>{channelConfig?.knowledge_base_ids.length ?? 0} sumber pengetahuan</span>
      <Link href="/dashboard/knowledge" className="ml-auto text-rc-accent hover:underline">Atur bisnis & pengetahuan</Link>
    </div>
    <div className="relative flex min-h-0 flex-1">
      {(historyVisible || mobileHistory) && <AgentConversationSidebar conversations={conversations} current={conversationId} onSelect={(id) => void selectConversation(id)} onNew={startNew} onClose={() => { setHistoryVisible(false); setMobileHistory(false); }} disabled={busy || restoring} mobile={mobileHistory} boardOpen={panel} />}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {sessionError && <p role="alert" className="mx-4 mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{sessionError}</p>}
        {restoring ? <p role="status" className="m-auto p-6 text-sm text-rc-fg-muted">Memuat percakapan…</p> : empty ? <div className="rc-scrollbar flex min-h-0 flex-1 flex-col justify-center overflow-y-auto py-8">
          <div className="mx-auto mb-8 w-full max-w-4xl px-5 md:px-9"><h2 className="text-3xl font-medium leading-tight tracking-tight text-rc-fg md:text-4xl">Mau mengerjakan apa hari ini?</h2><p className="mt-3 max-w-xl text-sm leading-6 text-rc-fg-muted">Cek pesan, siapkan balasan, dan susun pekerjaan agen. Semua dalam satu percakapan.</p></div>
          {composer}
          <div className="mx-auto mt-3 flex w-full max-w-4xl flex-wrap gap-2 px-4 md:px-8">{SUGGESTIONS.map((s) => <button key={s.title} onClick={() => void send(s.text)} className="rounded-xl border border-rc-border px-3 py-2 text-xs text-rc-fg-muted transition-colors hover:bg-rc-surface-hover">{s.title}</button>)}</div>
        </div> : <>
          <div ref={scroll} onScroll={() => { const el = scroll.current; if (el) { anchored.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100; setAway(!anchored.current); } }} className="rc-scrollbar min-h-0 flex-1 overflow-y-auto overscroll-contain">
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-7 px-4 py-7 md:px-8 md:py-9">{turns.map((turn, i) => turn.role === "user" ? <div key={turn.id} className="flex justify-end"><p className="max-w-[88%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-rc-surface-hover px-4 py-3 text-[15px] leading-6">{turn.text}</p></div> : <AgentTurn key={turn.id} turn={turn} busy={busy} retry={() => void send(turns[i - 1]?.text || "")} />)}</div>
          </div>
          {away && <div className="relative h-0"><button onClick={() => { anchored.current = true; setAway(false); scroll.current?.scrollTo({ top: scroll.current.scrollHeight, behavior: "smooth" }); }} className="absolute bottom-2 left-1/2 flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-rc-border bg-rc-surface px-3 py-2 text-xs shadow-md"><ArrowDown className="h-3.5 w-3.5" />Ke pesan terbaru</button></div>}
          {composer}
        </>}
      </div>
      {panel && <>
        <div role="separator" tabIndex={0} aria-label="Ubah lebar chat dan papan kerja" aria-orientation="vertical" aria-valuenow={boardWidth} aria-valuemin={320} aria-valuemax={1600}
          onPointerDown={(event) => { drag.current = { x: event.clientX, width: boardWidth }; event.currentTarget.setPointerCapture(event.pointerId); setResizing(true); }}
          onPointerMove={(event) => { if (drag.current) setBoardWidth(clampWidth(drag.current.width + drag.current.x - event.clientX)); }}
          onPointerUp={(event) => { if (!drag.current) return; drag.current = null; setResizing(false); event.currentTarget.releasePointerCapture(event.pointerId); saveWidth(boardWidth); }}
          onPointerCancel={() => { drag.current = null; setResizing(false); }}
          onKeyDown={(event) => { if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); saveWidth(clampWidth(boardWidth + (event.key === "ArrowLeft" ? 24 : -24))); } }}
          className="group hidden w-2 shrink-0 touch-none cursor-col-resize items-center justify-center bg-rc-bg transition-colors hover:bg-rc-accent-soft focus-visible:bg-rc-accent-soft focus-visible:outline-2 focus-visible:outline-rc-accent xl:flex"><span className="h-10 w-0.5 rounded-full bg-rc-border-strong group-hover:bg-rc-accent" /></div>
        <div id="agent-work-panel" className="contents"><AgentWorkPanel revision={revision} width={boardWidth} channel={selectedChannel === "all" ? undefined : selectedChannel} onClose={() => setPanel(false)} /></div>
      </>}
    </div>
  </section>;
}
