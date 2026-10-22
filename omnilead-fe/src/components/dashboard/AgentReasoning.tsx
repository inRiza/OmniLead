"use client";

import { useState } from "react";
import { CircleAlert, CircleCheck, CircleX, RotateCcw, Sparkles } from "lucide-react";
import type { Activity, AgentExecutionEvent, AgentTrace, ProposedAction } from "@/lib/types";
import { api } from "@/lib/api";
import { cap } from "@/lib/ui";
import { LogoMark } from "@/components/brand/Logo";
import { Button } from "@/components/action/button";
import { TimeAgo } from "@/components/TimeAgo";
import { AgentSteps, toolText } from "@/components/dashboard/AgentRun";

type Line = { key: string; text: string; detail?: string; tone?: "ok" | "warn" | "bad"; at?: string };

function fromActivity(item: AgentExecutionEvent, i: number): Line | null {
  const key = `${item.sequence}-${i}`;
  if (["plan", "context", "knowledge", "triage", "drafting", "score", "complete"].includes(item.phase)) return null;
  if (item.tool) return { key, text: `Saya ${toolText(item.tool)}.`, detail: item.result, at: item.at };
  if (item.phase === "triage_done" && item.intents?.length)
    return { key, text: `Saya memahami maksud pesan: ${item.intents.map((x) => x.replace(/_/g, " ")).join(", ")}.`, detail: item.reason, at: item.at };
  if (item.phase === "proposal" && item.text)
    return { key, text: "Saya menyiapkan usulan balasan.", detail: item.text, at: item.at };
  if (item.phase === "guard" && item.guard_summary) return { key, text: cap(item.guard_summary), at: item.at };
  if (!item.label) return null;
  return { key, text: cap(item.label), detail: item.reason || item.result, at: item.at };
}

function Bubble({ line }: { line: Line }) {
  const Icon = line.tone === "ok" ? CircleCheck : line.tone === "bad" ? CircleX : line.tone === "warn" ? CircleAlert : null;
  return (
    <li className="flex gap-2.5">
      <LogoMark size={22} className="mt-0.5 rounded-full" />
      <div className="min-w-0 flex-1">
        <div className="w-fit max-w-full rounded-lg rounded-tl-none bg-rc-bg px-3.5 py-2.5">
          <p className="flex items-start gap-1.5 text-sm text-rc-fg">
            {Icon ? (
              <Icon
                aria-hidden
                className={`mt-0.5 h-4 w-4 shrink-0 ${line.tone === "ok" ? "text-emerald-600" : line.tone === "bad" ? "text-red-600" : "text-amber-600"}`}
              />
            ) : null}
            <span>{line.text}</span>
          </p>
          {line.detail ? <p className="mt-1.5 border-l-2 border-rc-border pl-2.5 text-sm whitespace-pre-wrap break-words text-rc-fg-muted">{line.detail}</p> : null}
        </div>
        {line.at ? (
          <p className="mt-1 text-[11px] text-rc-fg-subtle">
            <TimeAgo iso={line.at} />
          </p>
        ) : null}
      </div>
    </li>
  );
}

export function AgentReasoning({
  activity,
  trace,
  actions,
  onRefresh,
}: {
  activity: Activity;
  trace?: AgentTrace;
  actions: ProposedAction[];
  onRefresh: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const queued = activity.analysis === "queued";
  const fresh = activity.eventStatus === "new" && !trace && !queued;
  const working = activity.eventStatus === "processing" || (activity.eventStatus === "new" && !!trace);
  const lines: Line[] = [];
  const steps = trace?.activity ?? [];
  const scored = [...steps].reverse().find((s) => s.phase === "score");

  if (trace?.goal) lines.push({ key: "goal", text: `Tujuan saya: ${trace.goal.charAt(0).toLowerCase()}${trace.goal.slice(1)}.` });
  if (trace?.plan.length) lines.push({ key: "plan", text: "Rencana saya:", detail: trace.plan.map((p, i) => `${i + 1}. ${cap(p)}`).join("\n") });
  const records = (trace?.activity ?? []).map(fromActivity).filter((x): x is Line => x !== null);
  if (records.length) lines.push(...records);
  else trace?.steps.forEach((s, i) => lines.push({ key: `s${i}`, text: `Saya ${toolText(s.tool)}.`, detail: s.output }));
  if (scored && !working)
    lines.push({
      key: "score",
      text: `Saya menghitung potensi lead: skor ${scored.score ?? 0}, ${scored.score_label ?? "Cold"}.`,
      detail: scored.reasons?.length ? scored.reasons.join("\n") : undefined,
    });
  trace?.guard.forEach((g, i) =>
    lines.push({ key: `g${i}`, text: g.passed ? `Pengecekan lolos: ${g.label.toLowerCase()}.` : `Perlu ditinjau: ${g.label.toLowerCase()}.`, tone: g.passed ? "ok" : "warn" }),
  );
  if (queued) lines.push({ key: "queued", text: "Pesan ini sudah masuk antrean. Saya analisis setelah pesan sebelumnya selesai." });
  if (fresh) lines.push({ key: "fresh", text: "Pesan ini belum saya proses. Klik Jawab dengan agen bila ingin saya siapkan balasannya." });
  else if (!working) {
    if (activity.eventStatus === "held") lines.push({ key: "end", text: "Agen sedang dijeda. Pesan ini saya proses setelah agen dilanjutkan.", tone: "warn" });
    else if (activity.eventStatus === "agent_error") lines.push({ key: "end", text: "Analisis saya gagal karena service agen tidak terjangkau.", tone: "bad" });
    else if (activity.eventStatus === "review") lines.push({ key: "end", text: "Pesan ini saya tandai untuk ditinjau manusia dan tidak saya balas otomatis.", tone: "warn" });
    else if (actions.length) lines.push({ key: "end", text: `Selesai. Saya menyiapkan ${actions.length} tindakan; hasilnya ada di bawah.`, tone: "ok" });
    else if (trace) lines.push({ key: "end", text: "Selesai. Tidak ada tindakan yang perlu saya ambil.", tone: "ok" });
  }

  async function retry() {
    setBusy(true);
    setError("");
    try {
      await api.reanalyze(activity.id);
      await onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Pesan belum bisa diproses ulang");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border border-rc-border bg-rc-surface">
      <header className="flex items-center justify-between gap-3 border-b border-rc-border px-5 py-3.5">
        <div>
          <h2 className="text-sm font-semibold text-rc-fg">Agen</h2>
          <p className="text-xs text-rc-fg-muted">{queued ? "Menunggu giliran" : fresh ? "Belum diproses" : working ? trace?.status || "Sedang berpikir" : "Jejak reasoning untuk pesan ini"}</p>
        </div>
        {fresh ? (
          <Button purpose="action" style="primary" className="gap-1.5" disabled={busy} onClick={() => void retry()}>
            <Sparkles className="h-4 w-4" aria-hidden />
            {busy ? "Memproses…" : "Jawab dengan agen"}
          </Button>
        ) : ["agent_error", "held"].includes(activity.eventStatus) ? (
          <Button purpose="action" className="gap-1.5" disabled={busy} onClick={() => void retry()}>
            <RotateCcw className="h-4 w-4" aria-hidden />
            {busy ? "Memproses…" : "Proses ulang"}
          </Button>
        ) : null}
      </header>
      <ol className="flex flex-col gap-3 px-5 py-4" aria-live="polite">
        {lines.length === 0 && !working ? <li className="text-sm text-rc-fg-muted">Belum ada jejak reasoning untuk pesan ini.</li> : null}
        {working ? null : lines.map((line) => <Bubble key={line.key} line={line} />)}
        {working ? (
          <li className="rounded-lg bg-rc-bg px-4 py-3.5">
            <AgentSteps items={trace?.activity ?? []} status={activity.eventStatus} className="bg-rc-bg" />
          </li>
        ) : null}
      </ol>
      {error ? <p role="alert" className="mx-5 mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
    </section>
  );
}
