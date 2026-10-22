"use client";

import { useState } from "react";
import { CircleAlert, CircleCheck, CircleX, MessageSquareWarning, Sparkles } from "lucide-react";
import type { ActionStatus, ProposedAction } from "@/lib/types";
import { checkLabel } from "@/lib/adapt";
import { cap, channelLabel, type Tone } from "@/lib/ui";
import { Button } from "@/components/action/button";
import { Badge } from "@/components/primitives";

const STATUS: Record<ActionStatus, { label: string; tone: Tone }> = {
  pending: { label: "Disiapkan agen", tone: "blue" },
  approved: { label: "Diproses", tone: "blue" },
  edited: { label: "Diproses", tone: "blue" },
  executing: { label: "Mengirim", tone: "blue" },
  executed: { label: "Terkirim", tone: "green" },
  failed: { label: "Gagal", tone: "red" },
  rejected: { label: "Ditandai kurang tepat", tone: "gray" },
  awaiting_manual_send: { label: "Perlu kirim manual", tone: "amber" },
  sent_manually: { label: "Dikirim manual", tone: "green" },
};

export function AgentResults({
  actions,
  onFeedback,
}: {
  actions: ProposedAction[];
  onFeedback: (id: string, reason: string) => Promise<void>;
}) {
  if (actions.length === 0)
    return (
      <p className="rounded-xl border border-dashed border-rc-border-strong px-5 py-6 text-center text-sm text-rc-fg-muted">
        Agen belum mengambil tindakan untuk pesan ini.
      </p>
    );
  return (
    <ol className="relative flex flex-col gap-3 pl-5">
      <span aria-hidden className="absolute top-3 bottom-3 left-[5px] w-px bg-rc-border" />
      {actions.map((a) => (
        <ResultItem key={a.id} action={a} onFeedback={onFeedback} />
      ))}
    </ol>
  );
}

function ResultItem({ action, onFeedback }: { action: ProposedAction; onFeedback: (id: string, reason: string) => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const status = STATUS[action.status] ?? { label: action.status, tone: "gray" as Tone };
  const reviewable = action.status === "pending" || action.status === "awaiting_manual_send";

  async function send() {
    if (!reason.trim()) return;
    setBusy(true);
    setError("");
    try {
      await onFeedback(action.id, reason.trim());
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Masukan belum tersimpan");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="relative rounded-xl border border-rc-border bg-rc-surface p-4">
      <span
        aria-hidden
        className={`absolute top-5 -left-5 h-2.5 w-2.5 rounded-full ring-4 ring-rc-surface ${status.tone === "green" ? "bg-emerald-500" : status.tone === "red" ? "bg-red-500" : status.tone === "amber" ? "bg-amber-500" : "bg-rc-accent"}`}
      />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-rc-fg">{action.title}</p>
          <p className="text-xs text-rc-fg-muted">
            {channelLabel[action.channel]}
            {action.target ? `, ${action.target}` : ""}
          </p>
        </div>
        <Badge tone={status.tone} dot>
          {status.label}
        </Badge>
      </div>
      {action.text ? <p className="mt-3 rounded-lg bg-rc-bg px-3.5 py-2.5 text-sm leading-relaxed whitespace-pre-line text-rc-fg">{action.text}</p> : null}
      {(action.reason || action.guard.length > 0) && (
        <div className="mt-3 rounded-lg bg-rc-accent-soft/60 p-3.5">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-rc-accent">
            <Sparkles className="h-3.5 w-3.5" aria-hidden />
            Ringkasan AI
          </p>
          {action.reason ? <p className="mt-1.5 text-sm leading-relaxed text-rc-fg">{cap(action.reason)}</p> : null}
          {action.guard.length > 0 && (
            <ul className="mt-2.5 flex flex-col gap-1.5 border-t border-rc-accent/10 pt-2.5">
              {action.guard.map((g, i) => {
                const Icon = g.status === "pass" ? CircleCheck : g.status === "block" ? CircleX : CircleAlert;
                const color = g.status === "pass" ? "text-emerald-600" : g.status === "block" ? "text-red-600" : "text-amber-600";
                return (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${color}`} aria-hidden />
                    <span className="min-w-0">
                      <span className="font-medium text-rc-fg">{cap(checkLabel(g.check))}</span>
                      {g.note ? <span className="text-rc-fg-muted">. {cap(g.note)}</span> : null}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
      {action.error ? <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{action.error}</p> : null}
      {reviewable && !open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="mt-3 inline-flex cursor-pointer items-center gap-1.5 text-xs font-medium text-rc-fg-muted hover:text-rc-accent"
        >
          <MessageSquareWarning className="h-3.5 w-3.5" aria-hidden />
          Hasil kurang tepat?
        </button>
      )}
      {open && (
        <div className="mt-3 flex flex-col gap-2">
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            placeholder="Apa yang kurang tepat? Masukan ini dipakai agen untuk balasan berikutnya."
            className="w-full resize-none rounded-md border border-rc-border bg-rc-bg px-3 py-2 text-sm text-rc-fg outline-none focus:border-rc-accent"
          />
          {error && <p role="alert" className="text-xs text-red-700">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button purpose="action" style="muted" disabled={busy} onClick={() => setOpen(false)}>
              Batal
            </Button>
            <Button purpose="action" style="primary" disabled={busy || !reason.trim()} onClick={() => void send()}>
              {busy ? "Menyimpan…" : "Kirim masukan"}
            </Button>
          </div>
        </div>
      )}
    </li>
  );
}
