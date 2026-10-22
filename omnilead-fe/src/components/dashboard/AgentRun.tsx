"use client";

import { useCallback, useRef, useState, type ReactNode } from "react";
import { Check, CircleDashed, CircleX, Loader2, Minus } from "lucide-react";
import type { AgentExecutionEvent } from "@/lib/types";
import { api, type BeEvent } from "@/lib/api";
import { cn } from "@/lib/ui";

const TOOL_LABEL: Record<string, string> = {
  get_timeline: "membaca riwayat pelanggan",
  search_catalog_faq: "mencari jawaban di pengetahuan dan katalog bisnis",
  check_channel_window: "memeriksa izin waktu balasan kanal",
  score_lead: "menghitung prioritas pelanggan",
  propose_reply: "menyusun balasan",
  propose_private_reply: "menyusun balasan pribadi",
  propose_crm_update: "memperbarui data pelanggan",
  propose_followup: "menjadwalkan tindak lanjut",
  cari_katalog: "mencari di katalog",
  cek_kebijakan: "memeriksa kebijakan bisnis",
  cek_riwayat: "membaca riwayat pelanggan",
  hitung_harga: "menghitung harga",
};

export function toolText(tool: string) {
  return TOOL_LABEL[tool] ?? tool.replace(/_/g, " ");
}

const INTENT: Record<string, string> = {
  tanya_harga: "tanya harga",
  tanya_stok: "tanya stok",
  minta_penawaran: "minta penawaran",
  order: "mau pesan",
  komplain: "komplain",
  follow_up: "menagih balasan",
  konfirmasi_bayar: "konfirmasi bayar",
  batal_pesan: "batal pesan",
  pertanyaan_umum: "pertanyaan umum",
  spam: "spam",
};

type StepState = "done" | "active" | "waiting" | "skipped" | "failed";

type Step = {
  key: string;
  label: string;
  phases: string[];
  detail: (items: AgentExecutionEvent[]) => string | undefined;
};

const last = (items: AgentExecutionEvent[], phase: string) => [...items].reverse().find((i) => i.phase === phase);

const STEPS: Step[] = [
  {
    key: "users",
    label: "Mencari pengguna",
    phases: ["context"],
    detail: (items) => {
      const c = last(items, "context");
      if (!c) return undefined;
      return c.known ? `Pelanggan dikenal, ${c.history ?? 0} pesan di riwayat` : "Pelanggan baru";
    },
  },
  {
    key: "unread",
    label: "Mencari pesan yang belum dibalas",
    phases: ["context"],
    detail: (items) => {
      const c = last(items, "context");
      if (!c) return undefined;
      return c.unanswered ? `${c.unanswered} pesan menunggu balasan` : "Pesan terbaru ini saja";
    },
  },
  {
    key: "chunking",
    label: "Chunking pengetahuan bisnis",
    phases: ["knowledge"],
    detail: (items) => {
      const k = last(items, "knowledge");
      return k ? `${k.documents ?? 0} dokumen jadi ${k.chunks ?? 0} potongan, ${k.products ?? 0} produk` : undefined;
    },
  },
  {
    key: "lead",
    label: "Memastikan pesan tergolong lead",
    phases: ["triage_done"],
    detail: (items) => {
      const t = last(items, "triage_done");
      if (!t) return undefined;
      const intents = (t.intents ?? []).map((i) => INTENT[i] ?? i.replace(/_/g, " "));
      if (intents.includes("spam")) return "Bukan lead, terdeteksi spam";
      return `${intents.join(", ") || "Maksud belum jelas"}${t.urgency ? `, urgensi ${t.urgency}` : ""}`;
    },
  },
  {
    key: "extra",
    label: "Mencari status tambahan",
    phases: ["tool"],
    detail: (items) => {
      const tools = items.filter((i) => i.phase === "tool" && i.tool);
      if (!tools.length) return undefined;
      return [...new Set(tools.map((t) => toolText(t.tool!)))].join(", ");
    },
  },
  {
    key: "draft",
    label: "Menyusun balasan",
    phases: ["proposal"],
    detail: (items) => {
      const n = items.filter((i) => i.phase === "proposal").length;
      return n ? `${n} usulan tindakan` : undefined;
    },
  },
  {
    key: "score",
    label: "Menghitung potensi lead",
    phases: ["score"],
    detail: (items) => {
      const s = last(items, "score");
      if (!s) return undefined;
      return `Skor ${s.score ?? 0}, ${s.score_label ?? "Cold"}${s.reasons?.length ? `. ${s.reasons.slice(0, 2).join(", ")}` : ""}`;
    },
  },
  {
    key: "guard",
    label: "Pengecekan keamanan",
    phases: ["complete"],
    detail: (items) => last(items, "complete")?.guard_summary || undefined,
  },
];

const FINAL = new Set(["analyzed", "review", "agent_error", "held"]);

export function stepStates(items: AgentExecutionEvent[], status: string): StepState[] {
  const finished = FINAL.has(status);
  const seen = STEPS.map((s) => s.phases.some((p) => items.some((i) => i.phase === p)));
  const furthest = seen.lastIndexOf(true);
  const states: StepState[] = STEPS.map((_, i) => {
    if (seen[i]) return "done";
    if (i < furthest || finished) return "skipped";
    return "waiting";
  });
  if (status === "agent_error") {
    const firstOpen = states.findIndex((s) => s !== "done");
    if (firstOpen >= 0) states[firstOpen] = "failed";
    return states;
  }
  if (!finished) {
    const next = states.findIndex((s) => s === "waiting");
    if (next >= 0) states[next] = "active";
  }
  return states;
}

function StepIcon({ state }: { state: StepState }) {
  if (state === "done")
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-rc-accent text-white motion-safe:animate-[rc-pop_0.3s_ease-out]">
        <Check className="h-3 w-3" strokeWidth={3} aria-hidden />
      </span>
    );
  if (state === "active") return <Loader2 className="h-5 w-5 text-rc-accent motion-safe:animate-spin" aria-hidden />;
  if (state === "failed") return <CircleX className="h-5 w-5 text-red-600" aria-hidden />;
  if (state === "skipped")
    return (
      <span className="flex h-5 w-5 items-center justify-center rounded-full bg-rc-surface-hover text-rc-fg-subtle">
        <Minus className="h-3 w-3" aria-hidden />
      </span>
    );
  return <CircleDashed className="h-5 w-5 text-rc-border-strong" aria-hidden />;
}

export function AgentSteps({ items, status, className }: { items: AgentExecutionEvent[]; status: string; className?: string }) {
  const states = stepStates(items, status);
  return (
    <ol className={cn("flex flex-col", className)} aria-live="polite">
      {STEPS.map((step, i) => {
        const state = states[i];
        const detail = step.detail(items);
        return (
          <li key={step.key} className="relative flex gap-3 pb-3.5 last:pb-0">
            {i < STEPS.length - 1 ? (
              <span
                aria-hidden
                className={cn("absolute top-6 bottom-0 left-2.5 w-px -translate-x-1/2", state === "done" ? "bg-rc-accent/40" : "bg-rc-border")}
              />
            ) : null}
            <span className="relative z-10 shrink-0 bg-inherit">
              <StepIcon state={state} />
            </span>
            <div className="min-w-0 flex-1 pt-px">
              <p
                className={cn(
                  "font-mono text-[13px] leading-5",
                  state === "active" ? "font-medium text-rc-accent" : state === "done" ? "text-rc-fg" : "text-rc-fg-subtle",
                  state === "skipped" && "line-through decoration-rc-border-strong",
                )}
              >
                [{step.label}
                {state === "active" ? "…" : ""}]
              </p>
              {detail && state !== "waiting" ? <p className="mt-0.5 text-xs leading-relaxed text-rc-fg-muted">{detail}</p> : null}
              {state === "skipped" && !detail ? <p className="mt-0.5 text-xs text-rc-fg-subtle">Tidak diperlukan untuk pesan ini</p> : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export type RunResult = { id: string; name: string; status: string; score?: number; label?: string; proposals: number };

type RunState = {
  ids: string[];
  index: number;
  current: BeEvent | null;
  results: RunResult[];
  error: string;
};

const POLL_MS = 700;
const TIMEOUT_MS = 200_000;

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function useAgentRun(onFinished: () => Promise<void>) {
  const [run, setRun] = useState<RunState | null>(null);
  const stop = useRef(false);
  const names = useRef<Record<string, string>>({});

  const start = useCallback(
    async (targets: { id: string; name: string }[], queued = false) => {
      if (!targets.length) return;
      stop.current = false;
      names.current = Object.fromEntries(targets.map((t) => [t.id, t.name]));
      const ids = targets.map((t) => t.id);
      setRun({ ids, index: 0, current: null, results: [], error: "" });
      for (const [index, id] of ids.entries()) {
        if (stop.current) break;
        setRun((r) => (r ? { ...r, index, current: null } : r));
        let event: BeEvent | null = null;
        try {
          event = queued ? await api.event(id) : await api.reanalyze(id);
          setRun((r) => (r ? { ...r, current: event } : r));
          const deadline = Date.now() + TIMEOUT_MS;
          while (!FINAL.has(event.status) && Date.now() < deadline) {
            await wait(POLL_MS);
            event = await api.event(id);
            setRun((r) => (r ? { ...r, current: event } : r));
          }
        } catch (e) {
          setRun((r) => (r ? { ...r, error: e instanceof Error ? e.message : "Sebagian pesan gagal diproses" } : r));
        }
        const score = last(event?.trace?.activity ?? [], "score");
        const result: RunResult = {
          id,
          name: names.current[id] ?? "Pelanggan",
          status: event?.status ?? "agent_error",
          score: score?.score,
          label: score?.score_label,
          proposals: event?.trace?.activity?.filter((a) => a.phase === "proposal").length ?? 0,
        };
        setRun((r) => (r ? { ...r, results: [...r.results, result] } : r));
      }
      await onFinished();
      setRun((r) => (r ? { ...r, index: r.ids.length, current: null } : r));
    },
    [onFinished],
  );

  const running = run !== null && run.index < run.ids.length;
  return {
    run,
    running,
    start,
    requestStop: () => {
      stop.current = true;
    },
    dismiss: () => setRun(null),
  };
}

const RESULT_TONE: Record<string, string> = {
  Hot: "bg-rc-accent text-rc-accent-fg",
  Warm: "bg-rc-accent-soft text-rc-accent",
  Cold: "bg-rc-surface-hover text-rc-fg-muted",
};

export function AgentRunPanel({
  run,
  running,
  onStop,
  done: doneSlot,
}: {
  run: RunState;
  running: boolean;
  onStop: () => void;
  done?: ReactNode;
}) {
  const total = run.ids.length;
  const done = run.results.length;
  const name = running ? (run.current ? run.current.sender.name || run.current.sender.handle : null) : null;
  const pct = Math.round(((done + (running ? 0.5 : 0)) / total) * 100);
  return (
    <section className="overflow-hidden rounded-xl border border-rc-border bg-rc-surface motion-safe:animate-[rc-fade-up_0.25s_ease-out]">
      <div className="h-1 w-full bg-rc-surface-hover">
        <div className="h-full bg-rc-accent transition-[width] duration-500 ease-out" style={{ width: `${pct}%` }} />
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 pt-4">
        <div className="flex min-w-0 items-center gap-3">
          {running ? (
            <Loader2 className="h-5 w-5 text-rc-accent motion-safe:animate-spin" aria-hidden />
          ) : (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-rc-accent text-white">
              <Check className="h-3 w-3" strokeWidth={3} aria-hidden />
            </span>
          )}
          <div className="min-w-0">
            <p className="text-sm font-semibold text-rc-fg">{running ? "Menjawab pesan" : "Selesai"}</p>
            <p className="truncate text-xs text-rc-fg-muted">
              {running
                ? `Pesan ${Math.min(done + 1, total)} dari ${total}${name ? `, ${name}` : ""}`
                : `${done} dari ${total} pesan diproses`}
            </p>
          </div>
        </div>
        {running ? (
          <button type="button" onClick={onStop} className="rounded-md px-2.5 py-1 text-xs font-medium text-rc-fg-muted transition-colors hover:bg-rc-surface-hover hover:text-rc-fg">
            Berhenti setelah pesan ini
          </button>
        ) : null}
      </div>

      <div className="grid gap-5 px-5 py-4 md:grid-cols-[minmax(0,1fr)_minmax(0,16rem)]">
        {running ? (
          <AgentSteps items={run.current?.trace?.activity ?? []} status={run.current?.status ?? "new"} className="bg-rc-surface" />
        ) : (
          <div>{doneSlot}</div>
        )}
        {run.results.length ? (
          <ul className="flex flex-col gap-1.5 md:border-l md:border-rc-border md:pl-5">
            {run.results.map((r) => (
              <li key={r.id} className="flex items-center justify-between gap-2 text-sm motion-safe:animate-[rc-fade-up_0.2s_ease-out]">
                <span className="flex min-w-0 items-center gap-1.5">
                  {r.status === "agent_error" ? (
                    <CircleX className="h-3.5 w-3.5 shrink-0 text-red-600" aria-hidden />
                  ) : (
                    <Check className="h-3.5 w-3.5 shrink-0 text-rc-accent" aria-hidden />
                  )}
                  <span className="truncate text-rc-fg">{r.name}</span>
                </span>
                {r.label ? (
                  <span className={cn("shrink-0 rounded-md px-1.5 py-0.5 text-xs font-medium tabular-nums", RESULT_TONE[r.label] ?? RESULT_TONE.Cold)}>
                    {r.score} {r.label}
                  </span>
                ) : (
                  <span className="shrink-0 text-xs text-rc-fg-subtle">{r.status === "agent_error" ? "Gagal" : "Tanpa skor"}</span>
                )}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      {run.error ? <p role="alert" className="mx-5 mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{run.error}</p> : null}
    </section>
  );
}
