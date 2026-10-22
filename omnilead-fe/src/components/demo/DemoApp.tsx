"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowUp, Check, ChevronDown, CircleAlert, Loader2, RotateCcw, Square } from "lucide-react";
import { LogoMark } from "@/components/brand/Logo";
import { ChannelIcon } from "@/components/primitives";
import { usePrefersReducedMotion } from "@/components/landing/Interactive";
import { cn } from "@/lib/utils";
import {
  DEMO_BUSINESS, FALLBACK_REPLY, SCENARIOS, SEED_TASKS, matchScenario,
  type DemoDraft, type DemoStep, type DemoTask,
} from "@/lib/demo-agent";

type Autonomy = "hybrid" | "auto";
type StepState = DemoStep & { id: string; status: "running" | "done" };
type Turn = { id: string; role: "user" | "agent"; text: string; steps: StepState[]; thoughts: string; done: boolean; stopped?: boolean };
type QueueItem = DemoDraft & { status: "pending" | "sent" | "rejected" };
type Tab = "antrean" | "papan";
type View = "chat" | Tab;

const uid = () => Math.random().toString(36).slice(2, 10);
const SAMPLE = SCENARIOS.map((s) => ({ id: s.id, title: s.title, prompt: s.prompt }));

class Aborted extends Error {}

export function DemoApp() {
  const reduced = usePrefersReducedMotion();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [tasks, setTasks] = useState<DemoTask[]>(SEED_TASKS);
  const [autonomy, setAutonomy] = useState<Autonomy>("hybrid");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState<View>("chat");
  const [tab, setTab] = useState<Tab>("antrean");
  const abort = useRef<AbortController | null>(null);
  const autonomyRef = useRef<Autonomy>("hybrid");
  const scroller = useRef<HTMLDivElement>(null);
  const pending = queue.filter((q) => q.status === "pending").length;

  useEffect(() => { autonomyRef.current = autonomy; }, [autonomy]);
  useEffect(() => { scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: reduced ? "auto" : "smooth" }); }, [turns, reduced]);
  useEffect(() => () => abort.current?.abort(), []);

  const wait = (ms: number, signal: AbortSignal) => new Promise<void>((resolve, reject) => {
    if (signal.aborted) return reject(new Aborted());
    const timer = setTimeout(resolve, reduced ? ms * 0.1 : ms);
    signal.addEventListener("abort", () => { clearTimeout(timer); reject(new Aborted()); }, { once: true });
  });

  async function send(raw: string) {
    const text = raw.trim();
    if (!text || busy) return;
    const scenario = matchScenario(text);
    const controller = new AbortController();
    abort.current = controller;
    const agentId = uid();
    const patch = (fn: (t: Turn) => Turn) => setTurns((all) => all.map((t) => (t.id === agentId ? fn(t) : t)));
    setTurns((all) => [...all, { id: uid(), role: "user", text, steps: [], thoughts: "", done: true },
      { id: agentId, role: "agent", text: "", steps: [], thoughts: "", done: false }]);
    setValue(""); setBusy(true); setView("chat");
    const typeOut = async (full: string) => {
      const words = full.split(" ");
      for (let i = 1; i <= words.length; i++) {
        patch((t) => ({ ...t, text: words.slice(0, i).join(" ") }));
        await wait(24, controller.signal);
      }
    };
    try {
      await wait(500, controller.signal);
      if (!scenario) { await typeOut(FALLBACK_REPLY); patch((t) => ({ ...t, done: true })); return; }
      patch((t) => ({ ...t, thoughts: scenario.thoughts }));
      await wait(700, controller.signal);
      for (const step of scenario.steps) {
        const id = uid();
        patch((t) => ({ ...t, steps: [...t.steps, { ...step, id, status: "running" }] }));
        await wait(step.ms, controller.signal);
        patch((t) => ({ ...t, steps: t.steps.map((s) => (s.id === id ? { ...s, status: "done" } : s)) }));
      }
      if (scenario.drafts) {
        const auto = autonomyRef.current === "auto";
        setQueue((q) => [...q, ...scenario.drafts!.filter((d) => !q.some((x) => x.id === d.id))
          .map((d): QueueItem => ({ ...d, status: auto && !d.held ? "sent" : "pending" }))]);
        setTab("antrean");
      }
      if (scenario.tasks) {
        setTasks((all) => [...all, ...scenario.tasks!.filter((t) => !all.some((x) => x.id === t.id))]);
        setTab("papan");
      }
      await typeOut(scenario.reply(autonomyRef.current));
      patch((t) => ({ ...t, done: true }));
    } catch (e) {
      if (!(e instanceof Aborted)) throw e;
      patch((t) => ({ ...t, done: true, stopped: true, steps: t.steps.map((s) => ({ ...s, status: "done" })) }));
    } finally {
      if (abort.current === controller) abort.current = null;
      setBusy(false);
    }
  }

  function reset() {
    abort.current?.abort();
    setTurns([]); setQueue([]); setTasks(SEED_TASKS); setValue(""); setBusy(false); setView("chat"); setTab("antrean");
  }

  const decide = (id: string, status: "sent" | "rejected") => setQueue((q) => q.map((x) => (x.id === id ? { ...x, status } : x)));

  const chat = (
    <section aria-label="Obrolan dengan agen" className={cn("min-h-0 flex-col lg:flex", view === "chat" ? "flex" : "hidden")}>
      <div ref={scroller} className="rc-scrollbar min-h-0 flex-1 overflow-y-auto">
        {turns.length === 0 ? (
          <div className="mx-auto flex h-full w-full max-w-2xl flex-col justify-center px-5 py-8">
            <h2 className="text-2xl font-semibold tracking-tight text-rc-fg">Mau mengerjakan apa hari ini?</h2>
            <p className="mt-2 max-w-xl text-[15px] leading-6 text-rc-fg-muted">
              Ini agen untuk {DEMO_BUSINESS}. Pilih satu skenario atau tulis sendiri, lalu lihat apa yang dia kerjakan langkah demi langkah.
            </p>
            <div className="mt-6 grid gap-2 sm:grid-cols-2">
              {SAMPLE.map((s) => (
                <button key={s.id} type="button" onClick={() => void send(s.prompt)}
                  className="flex cursor-pointer flex-col items-start rounded-xl border border-rc-border bg-rc-surface px-4 py-3 text-left transition-colors hover:border-rc-accent/50 hover:bg-rc-accent-soft focus-visible:outline-2 focus-visible:outline-rc-accent">
                  <span className="text-sm font-medium text-rc-fg">{s.title}</span>
                  <span className="mt-0.5 text-sm leading-snug text-rc-fg-muted">{s.prompt}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto flex w-full max-w-2xl flex-col gap-7 px-4 py-7 sm:px-6">
            {turns.map((t) => t.role === "user"
              ? <div key={t.id} className="flex justify-end"><p className="max-w-[88%] rounded-2xl rounded-br-md bg-rc-accent px-4 py-3 text-[15px] leading-6 text-white">{t.text}</p></div>
              : <AgentTurn key={t.id} turn={t} />)}
          </div>
        )}
      </div>
      <div className="mx-auto w-full max-w-2xl px-4 pb-4 sm:px-6">
        {turns.length > 0 && (
          <div className="rc-scrollbar mb-2 flex gap-2 overflow-x-auto pb-1" aria-label="Skenario lain">
            {SAMPLE.map((s) => (
              <button key={s.id} type="button" disabled={busy} onClick={() => void send(s.prompt)}
                className="shrink-0 cursor-pointer rounded-full border border-rc-border bg-rc-surface px-3 py-1.5 text-sm text-rc-fg-muted transition-colors hover:border-rc-accent/50 hover:text-rc-accent disabled:cursor-not-allowed disabled:opacity-50">
                {s.title}
              </button>
            ))}
          </div>
        )}
        <form onSubmit={(e) => { e.preventDefault(); void send(value); }}
          className="flex items-end gap-2 rounded-xl border border-rc-border-strong bg-rc-surface p-2 shadow-sm focus-within:border-rc-accent focus-within:ring-2 focus-within:ring-rc-accent/15">
          <label className="sr-only" htmlFor="demo-input">Pesan untuk agen</label>
          <textarea id="demo-input" rows={1} value={value} maxLength={300} disabled={busy}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(value); } }}
            placeholder={`Tanya agen ${DEMO_BUSINESS}…`}
            className="max-h-32 min-h-9 flex-1 resize-none border-0 bg-transparent px-2 py-1.5 text-[15px] leading-6 text-rc-fg outline-none placeholder:text-rc-fg-subtle disabled:opacity-60" />
          {busy
            ? <button type="button" onClick={() => abort.current?.abort()} aria-label="Hentikan"
                className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-lg bg-rc-fg text-white"><Square className="h-3.5 w-3.5" /></button>
            : <button type="submit" disabled={!value.trim()} aria-label="Kirim"
                className="flex h-9 w-9 shrink-0 cursor-pointer items-center justify-center rounded-lg bg-rc-accent text-white transition-colors hover:bg-rc-accent-hover disabled:cursor-not-allowed disabled:opacity-35"><ArrowUp className="h-4 w-4" /></button>}
        </form>
      </div>
    </section>
  );

  const panel = (
    <aside aria-label="Antrean dan papan kerja" className={cn("min-h-0 flex-col border-rc-border bg-rc-bg lg:flex lg:border-l", view === "chat" ? "hidden" : "flex")}>
      <div role="tablist" aria-label="Panel" className="hidden shrink-0 gap-1 border-b border-rc-border bg-rc-surface p-2 lg:flex">
        <TabButton active={tab === "antrean"} onClick={() => setTab("antrean")} count={pending}>Antrean</TabButton>
        <TabButton active={tab === "papan"} onClick={() => setTab("papan")}>Papan kerja</TabButton>
      </div>
      <div className="rc-scrollbar min-h-0 flex-1 overflow-y-auto p-4">
        {(view === "papan" || (view !== "antrean" && tab === "papan") ) ? <Board tasks={tasks} /> : (
          <Queue items={queue} onDecide={decide} onAsk={() => void send(SAMPLE[0].prompt)} busy={busy} />
        )}
      </div>
    </aside>
  );

  return (
    <div className="rc-brand rc-app flex min-h-dvh flex-col bg-rc-hero">
      <header className="mx-auto flex w-full max-w-[1320px] items-center gap-3 px-4 py-4 sm:px-6 lg:px-8">
        <Link href="/" aria-label="OmniLead, ke beranda" className="rounded focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"><span className="inline-flex items-center gap-2.5"><LogoMark /><span className="text-base font-semibold tracking-tight text-white">OmniLead</span></span></Link>
        <div className="ml-auto flex items-center gap-2">
          <Link href="/" className="hidden min-h-10 items-center rounded-md px-4 text-sm font-medium text-white/85 hover:text-white sm:inline-flex">Kembali ke beranda</Link>
          <Link href="/dashboard" className="inline-flex min-h-10 items-center rounded-md bg-white px-5 text-sm font-medium text-rc-hero transition-colors hover:bg-white/90">Masuk</Link>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-[1320px] flex-1 flex-col px-3 pb-4 sm:px-6 lg:px-8">
        <div className="mb-4 px-1">
          <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">Coba agennya langsung</h1>
          <p className="mt-1 text-sm text-white/85">Ini demo dengan data contoh. Tidak ada pesan yang benar-benar dikirim.</p>
        </div>

        <div className="flex h-[calc(100dvh-12.5rem)] min-h-[34rem] flex-col overflow-hidden rounded-2xl bg-white shadow-[0_30px_80px_-30px_rgba(0,20,90,0.6)]">
          <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-rc-border px-4 py-3">
            <LogoMark size={24} />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-rc-fg">{DEMO_BUSINESS}</p>
              <p className="text-xs text-rc-fg-muted">Agen aktif di Instagram, WhatsApp, Facebook, Email</p>
            </div>
            <span className="rounded-md bg-rc-highlight-soft px-2 py-0.5 text-xs font-semibold text-[#8a5300]">Demo</span>
            <div className="ml-auto flex items-center gap-2">
              <div role="group" aria-label="Mode izin" className="flex rounded-lg border border-rc-border bg-rc-bg p-0.5">
                {([["hybrid", "Hybrid"], ["auto", "Akses penuh"]] as const).map(([id, label]) => (
                  <button key={id} type="button" aria-pressed={autonomy === id} disabled={busy} onClick={() => setAutonomy(id)}
                    title={id === "hybrid" ? "Semua balasan menunggu persetujuanmu" : "Balasan yang lolos pemeriksaan langsung dikirim (simulasi)"}
                    className={cn("min-h-8 cursor-pointer rounded-md px-3 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                      autonomy === id ? "bg-white font-medium text-rc-accent shadow-sm" : "text-rc-fg-muted hover:text-rc-fg")}>{label}</button>
                ))}
              </div>
              <button type="button" onClick={reset} className="inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-lg border border-rc-border px-3 text-sm text-rc-fg-muted transition-colors hover:bg-rc-surface-hover hover:text-rc-fg">
                <RotateCcw className="h-3.5 w-3.5" aria-hidden />Ulang
              </button>
            </div>
          </div>

          <div role="tablist" aria-label="Tampilan" className="flex shrink-0 gap-1 border-b border-rc-border bg-rc-surface p-2 lg:hidden">
            <TabButton active={view === "chat"} onClick={() => setView("chat")}>Obrolan</TabButton>
            <TabButton active={view === "antrean"} onClick={() => { setTab("antrean"); setView("antrean"); }} count={pending}>Antrean</TabButton>
            <TabButton active={view === "papan"} onClick={() => { setTab("papan"); setView("papan"); }}>Papan</TabButton>
          </div>

          <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_23.5rem]">
            {chat}
            {panel}
          </div>
        </div>
      </main>
    </div>
  );
}

function TabButton({ active, onClick, count, children }: { active: boolean; onClick: () => void; count?: number; children: React.ReactNode }) {
  return (
    <button type="button" role="tab" aria-selected={active} onClick={onClick}
      className={cn("inline-flex min-h-9 flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg px-3 text-sm transition-colors",
        active ? "bg-rc-accent-soft font-medium text-rc-accent" : "text-rc-fg-muted hover:bg-rc-surface-hover hover:text-rc-fg")}>
      {children}
      {count ? <span className="min-w-5 rounded-full bg-rc-highlight px-1.5 text-center text-xs font-semibold text-[#3d2600]">{count}</span> : null}
    </button>
  );
}

function AgentTurn({ turn }: { turn: Turn }) {
  const [expanded, setExpanded] = useState<boolean | null>(null);
  const working = !turn.done;
  const open = expanded ?? working;
  const running = turn.steps.find((s) => s.status === "running");
  const label = running?.label ?? (working ? (turn.steps.length ? "Merangkum hasil" : "Menyiapkan langkah") : `${turn.steps.length} langkah selesai`);
  return (
    <article className="min-w-0 space-y-3" aria-label="Jawaban agen" aria-busy={working}>
      <div className="flex items-center gap-2 text-sm font-semibold text-rc-fg"><LogoMark size={20} />OmniLead</div>
      {(working || turn.steps.length > 0) && (
        <div className="rounded-xl border border-rc-border bg-rc-surface">
          <button type="button" onClick={() => setExpanded(!open)} aria-expanded={open} className="flex w-full cursor-pointer items-center gap-2.5 px-3.5 py-3 text-left text-sm text-rc-fg-muted">
            {working ? <Loader2 className="h-4 w-4 animate-spin text-rc-accent" aria-hidden /> : <Check className="h-4 w-4 text-emerald-600" aria-hidden />}
            <span role="status" className="flex-1">{turn.stopped ? "Dihentikan" : label}</span>
            <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} aria-hidden />
          </button>
          {open && (
            <div className="space-y-4 border-t border-rc-border px-3.5 py-4">
              {turn.thoughts && (
                <details open={working || undefined} className="rounded-lg bg-rc-bg px-3 py-2 text-sm text-rc-fg-muted">
                  <summary className="cursor-pointer select-none font-medium">Ringkasan pemikiran</summary>
                  <p className="mt-2 leading-relaxed">{turn.thoughts}</p>
                </details>
              )}
              <ol className="space-y-4">
                {turn.steps.map((s) => (
                  <li key={s.id} className="space-y-1.5 border-l-2 border-rc-border pl-4">
                    <div className="flex items-start gap-2">
                      <span className="mt-0.5 shrink-0">{s.status === "running" ? <Loader2 className="h-4 w-4 animate-spin text-rc-accent" aria-label="Berjalan" /> : <Check className="h-4 w-4 text-emerald-600" aria-label="Selesai" />}</span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-rc-fg">{s.label}{s.status === "running" && "…"}</p>
                        <p className="mt-0.5 text-sm leading-relaxed text-rc-fg-muted">{s.say}</p>
                        {s.status === "done" && <p className="mt-1.5 text-sm leading-relaxed text-rc-fg">{s.summary}</p>}
                      </div>
                    </div>
                    <details className="text-sm text-rc-fg-muted">
                      <summary className="inline-flex cursor-pointer list-none items-center gap-1.5"><code className="rounded bg-rc-bg px-1.5 py-0.5 font-mono text-xs">{s.tool}</code><ChevronDown className="h-3 w-3" aria-hidden /></summary>
                      <pre className="mt-2 overflow-auto rounded-lg border border-rc-border bg-rc-bg p-3 font-mono text-xs">{JSON.stringify(s.args, null, 2)}</pre>
                    </details>
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
      {turn.text && <p className="whitespace-pre-wrap break-words text-[15px] leading-7 text-rc-fg">{turn.text}</p>}
    </article>
  );
}

const STATUS = {
  pending: { label: "Menunggu keputusan", cls: "bg-rc-accent-soft text-rc-accent" },
  held: { label: "Ditahan Guard", cls: "bg-amber-50 text-amber-800" },
  sent: { label: "Terkirim (simulasi)", cls: "bg-emerald-50 text-emerald-700" },
  rejected: { label: "Ditolak", cls: "bg-rc-surface-hover text-rc-fg-muted" },
} as const;

function Queue({ items, onDecide, onAsk, busy }: { items: QueueItem[]; onDecide: (id: string, s: "sent" | "rejected") => void; onAsk: () => void; busy: boolean }) {
  if (items.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-4 text-center">
        <p className="text-sm font-medium text-rc-fg">Belum ada balasan</p>
        <p className="mt-1.5 text-sm leading-relaxed text-rc-fg-muted">Balasan yang disiapkan agen muncul di sini, menunggu keputusanmu.</p>
        <button type="button" disabled={busy} onClick={onAsk} className="mt-4 inline-flex min-h-9 cursor-pointer items-center rounded-lg border border-rc-border bg-rc-surface px-4 text-sm font-medium text-rc-fg transition-colors hover:bg-rc-surface-hover disabled:opacity-50">Minta agen cek pesan masuk</button>
      </div>
    );
  }
  return (
    <ul className="space-y-3">
      {items.map((q) => {
        const state = q.status === "pending" && q.held ? STATUS.held : STATUS[q.status];
        return (
          <li key={q.id} className="rc-pop rounded-xl border border-rc-border bg-rc-surface p-3.5 shadow-sm">
            <div className="flex items-start gap-2.5">
              <ChannelIcon channel={q.channel} size="md" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-rc-fg">{q.to}</p>
                <p className="text-xs leading-snug text-rc-fg-muted">{q.about}</p>
              </div>
              <span className={cn("shrink-0 rounded-md px-2 py-0.5 text-xs font-medium", state.cls)}>{state.label}</span>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-rc-fg">{q.text}</p>
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {q.checks.map((c) => (
                <li key={c.note} className={cn("inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs", c.ok ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800")}>
                  {c.ok ? <Check className="h-3 w-3" aria-hidden /> : <CircleAlert className="h-3 w-3" aria-hidden />}{c.note}
                </li>
              ))}
            </ul>
            {q.held && q.status === "pending" && <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-sm leading-snug text-amber-900">{q.held}</p>}
            {q.status === "pending" ? (
              <div className="mt-3 flex gap-2">
                <button type="button" onClick={() => onDecide(q.id, "sent")} className="min-h-9 cursor-pointer rounded-lg bg-rc-accent px-3.5 text-sm font-semibold text-white transition-colors hover:bg-rc-accent-hover">Setujui & kirim</button>
                <button type="button" onClick={() => onDecide(q.id, "rejected")} className="min-h-9 cursor-pointer rounded-lg border border-rc-border px-3.5 text-sm font-medium text-rc-fg-muted transition-colors hover:bg-rc-surface-hover">Tolak</button>
              </div>
            ) : q.status === "sent" ? <p className="mt-3 text-xs text-rc-fg-muted">Ini simulasi. Pesan tidak dikirim ke siapa pun.</p> : null}
          </li>
        );
      })}
    </ul>
  );
}

const COLUMNS: { status: DemoTask["status"]; title: string }[] = [
  { status: "todo", title: "To-do" },
  { status: "scheduled", title: "Terjadwal" },
  { status: "done", title: "Selesai" },
];

function Board({ tasks }: { tasks: DemoTask[] }) {
  return (
    <div className="space-y-5">
      {COLUMNS.map((col) => {
        const list = tasks.filter((t) => t.status === col.status);
        return (
          <section key={col.status} aria-label={col.title}>
            <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-rc-fg">{col.title}<span className="text-rc-fg-subtle">{list.length}</span></h3>
            {list.length === 0 ? <p className="rounded-lg border border-dashed border-rc-border-strong px-3 py-3 text-sm text-rc-fg-muted">Kosong.</p> : (
              <ul className="space-y-2">
                {list.map((t) => (
                  <li key={t.id} className="rc-pop rounded-xl border border-rc-border bg-rc-surface p-3 shadow-sm">
                    <p className="text-sm font-semibold leading-snug text-rc-fg">{t.title}</p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      {t.channels.map((c) => <span key={c} className="rounded-md bg-rc-surface-hover px-1.5 py-0.5 text-xs font-medium capitalize text-rc-fg-muted">{c}</span>)}
                    </div>
                    <p className="mt-2 text-xs text-rc-fg-muted">{t.schedule}{t.cron && <code className="ml-2 font-mono">{t.cron}</code>}</p>
                    {t.note && <p className="mt-1.5 text-sm leading-snug text-rc-fg-muted">{t.note}</p>}
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
