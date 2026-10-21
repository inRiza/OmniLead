"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { checkLabel } from "@/lib/adapt";
import type { LeadProfile, ProposedAction } from "@/lib/types";
import { channelLabel } from "@/lib/ui";
import { Button } from "@/components/action/button";
import { ChannelIcon, Pill } from "@/components/primitives";
import { MergeEvidence } from "./MergeCard";

const OPEN = new Set(["pending", "awaiting_manual_send", "failed"]);

// Urutan tampil: balasan publik, DM/pesan, lalu perubahan internal.
const KIND_ORDER: Record<ProposedAction["kind"], number> = {
  merge: -1,
  reply_comment: 0,
  private_reply: 1,
  send_message: 2,
  crm_update: 3,
  followup: 4,
};

export interface QueueHandlers {
  onApprove: (id: string, editedText?: string) => Promise<void>;
  onReject: (id: string, reason: string) => Promise<void>;
  onRetry: (id: string) => Promise<void>;
  onSent: (id: string) => Promise<void>;
}

export function ApprovalQueue({
  actions,
  paused,
  leadsById,
  ...handlers
}: {
  actions: ProposedAction[];
  paused: boolean;
  leadsById: Record<string, LeadProfile>;
} & QueueHandlers) {
  const open = actions
    .filter((a) => OPEN.has(a.status))
    .sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind]);

  if (open.length === 0) {
    return (
      <p className="rounded-lg border border-rc-border bg-rc-surface px-4 py-5 text-center text-sm text-rc-fg-muted">
        Tidak ada aksi yang perlu disetujui.
      </p>
    );
  }

  // Komentar publik + private reply tampil berdampingan, masing-masing dengan tombol sendiri.
  const pair = open.filter(
    (a) => a.kind === "private_reply" || (a.kind === "reply_comment" && a.isPublic),
  );
  const sideBySide = pair.length === 2 ? pair : [];
  const rest = open.filter((a) => !sideBySide.includes(a));
  const card = (a: ProposedAction) => (
    <ActionCard
      key={a.id}
      action={a}
      paused={paused}
      leadsById={leadsById}
      {...handlers}
    />
  );

  return (
    <div className="flex flex-col gap-3">
      {rest.filter((a) => a.kind === "merge").map(card)}
      {sideBySide.length ? (
        <div className="grid items-start gap-3 md:grid-cols-2">{sideBySide.map(card)}</div>
      ) : null}
      {rest.filter((a) => a.kind !== "merge").map(card)}
    </div>
  );
}

function ActionCard({
  action,
  paused,
  leadsById,
  onApprove,
  onReject,
  onRetry,
  onSent,
}: {
  action: ProposedAction;
  paused: boolean;
  leadsById: Record<string, LeadProfile>;
} & QueueHandlers) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(action.text);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const awaitingManual = action.status === "awaiting_manual_send";
  const failed = action.status === "failed";
  const isHandoff = action.path === "handoff";
  const editable = !action.internal && action.status === "pending";

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal");
    } finally {
      setBusy(false);
    }
  }

  async function copyAndOpen() {
    await run(async () => {
      const pkg = await api.handoff(action.id);
      await navigator.clipboard?.writeText(pkg.copy_text).catch(() => {});
      if (pkg.open_url) window.open(pkg.open_url, "_blank", "noopener,noreferrer");
    });
  }

  const approveLabel = action.kind === "merge"
    ? "Setujui gabung"
    : action.internal
    ? "Setujui"
    : isHandoff
      ? "Setujui & siapkan kirim manual"
      : "Setujui & kirim";

  return (
    <div className="rounded-lg border border-rc-border bg-rc-surface p-6">
      <div className="flex items-center gap-2">
        <ChannelIcon channel={action.channel} />
        <span className="text-sm font-semibold text-rc-fg">{action.title}</span>
        <span className="ml-auto">
          <Pill tone="muted">
            {action.internal ? "Internal" : isHandoff ? "Handoff" : "API"}
          </Pill>
        </span>
      </div>
      <p className="mt-1 text-sm text-rc-fg-muted">
        {action.kind === "followup"
          ? "Pengingat internal; pesan follow-up baru diusulkan saat jatuh tempo"
          : action.kind === "merge"
          ? "Perubahan data pelanggan: gabung identitas"
          : action.kind === "crm_update"
          ? "Perubahan data pelanggan di CRM"
          : `${channelLabel[action.channel]} ke ${action.target}`}
      </p>

      {action.kind === "merge" ? (
        <MergeEvidence action={action} leadsById={leadsById} />
      ) : editing && editable ? (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          className="mt-3 w-full resize-none rounded-md border border-rc-border bg-rc-bg px-3 py-2 text-sm leading-relaxed text-rc-fg outline-none focus:border-rc-fg"
        />
      ) : (
        <p className="mt-3 whitespace-pre-line rounded-md bg-rc-surface-hover/60 px-3 py-2 text-sm leading-relaxed text-rc-fg">
          {text}
        </p>
      )}

      {action.reason ? (
        <p className="mt-2 text-sm text-rc-fg-muted">{action.reason}</p>
      ) : null}
      {action.riskNote ? (
        <p className="mt-1 text-sm font-medium text-rc-fg">{action.riskNote}</p>
      ) : null}
      {action.guard.some((g) => g.status !== "pass") ? (
        <ul className="mt-1 list-disc pl-4 text-sm text-rc-fg-muted">
          {action.guard
            .filter((g) => g.status !== "pass")
            .map((g) => (
              <li key={g.check}>
                {checkLabel(g.check)}: {g.note}
              </li>
            ))}
        </ul>
      ) : null}
      {failed && action.error ? (
        <p role="alert" className="mt-2 text-sm font-medium text-rc-danger">
          Gagal kirim: {action.error}
        </p>
      ) : null}

      {rejecting ? (
        <div className="mt-3 flex flex-col gap-2">
          <label className="text-sm font-medium text-rc-fg-subtle" htmlFor={`rj-${action.id}`}>
            Alasan penolakan (agen akan mempelajarinya)
          </label>
          <input
            id={`rj-${action.id}`}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="mis. terlalu formal"
            className="w-full rounded-md border border-rc-border bg-rc-bg px-3 py-2 text-sm text-rc-fg outline-none focus:border-rc-fg"
          />
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="mt-2 text-sm font-medium text-rc-danger">
          {error}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {awaitingManual ? (
          <>
            <Button purpose="action" style="primary" disabled={busy} onClick={copyAndOpen}>
              Salin & buka
            </Button>
            <Button
              purpose="action"
              style="secondary"
              disabled={busy}
              onClick={() => run(() => onSent(action.id))}
            >
              Sudah dikirim
            </Button>
          </>
        ) : failed ? (
          <>
            <Button
              purpose="action"
              style="primary"
              disabled={busy || paused}
              onClick={() => run(() => onRetry(action.id))}
            >
              Coba ulang
            </Button>
            <Button
              purpose="action"
              style="secondary"
              disabled={busy}
              onClick={() => run(copyAndOpen)}
            >
              Tangani manual
            </Button>
          </>
        ) : rejecting ? (
          <>
            <Button
              purpose="action"
              style="primary"
              disabled={busy || paused || reason.trim() === ""}
              onClick={() => run(() => onReject(action.id, reason.trim()))}
            >
              Konfirmasi tolak
            </Button>
            <Button purpose="action" style="ghost" onClick={() => setRejecting(false)}>
              Batal
            </Button>
          </>
        ) : (
          <>
            <Button
              purpose="action"
              style="primary"
              disabled={busy || paused}
              onClick={() =>
                run(() =>
                  onApprove(action.id, text !== action.text ? text : undefined),
                )
              }
            >
              {approveLabel}
            </Button>
            {editable ? (
              <Button
                purpose="action"
                style="ghost"
                disabled={paused}
                onClick={() => setEditing((v) => !v)}
              >
                {editing ? "Selesai" : "Edit"}
              </Button>
            ) : null}
            <Button
              purpose="action"
              style="ghost"
              disabled={busy || paused}
              onClick={() => setRejecting(true)}
            >
              Tolak
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
