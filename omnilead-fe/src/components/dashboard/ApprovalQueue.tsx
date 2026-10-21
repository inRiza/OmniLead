"use client";

import { useState } from "react";
import type { ProposedAction } from "@/lib/types";
import { channelLabel } from "@/lib/ui";
import { Button } from "@/components/action/button";
import { ChannelIcon, Pill } from "@/components/primitives";

export function ApprovalQueue({
  actions,
  paused,
  onApprove,
  onReject,
  onSent,
}: {
  actions: ProposedAction[];
  paused: boolean;
  onApprove: (id: string, text: string) => void;
  onReject: (id: string, reason: string) => void;
  onSent: (id: string) => void;
}) {
  const pending = actions.filter(
    (a) => a.status === "pending" || a.status === "awaiting_manual_send",
  );

  if (pending.length === 0) {
    return (
      <p className="rounded-lg border border-rc-border bg-rc-surface px-4 py-5 text-center text-sm text-rc-fg-muted">
        Semua sudah ditangani untuk percakapan ini.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {pending.map((a) => (
        <ActionCard
          key={a.id}
          action={a}
          paused={paused}
          onApprove={onApprove}
          onReject={onReject}
          onSent={onSent}
        />
      ))}
    </div>
  );
}

function ActionCard({
  action,
  paused,
  onApprove,
  onReject,
  onSent,
}: {
  action: ProposedAction;
  paused: boolean;
  onApprove: (id: string, text: string) => void;
  onReject: (id: string, reason: string) => void;
  onSent: (id: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(action.text);
  const isHandoff = action.path === "handoff";

  return (
    <div className="rounded-lg border border-rc-border bg-rc-surface p-6">
      <div className="flex items-center gap-2">
        <ChannelIcon channel={action.channel} />
        <span className="text-sm font-semibold text-rc-fg">{action.title}</span>
        <span className="ml-auto">
          <Pill tone="muted">{isHandoff ? "Handoff" : "API"}</Pill>
        </span>
      </div>
      <p className="mt-1 text-xs text-rc-fg-muted">
        {channelLabel[action.channel]} ke {action.target}
      </p>

      {editing ? (
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          className="mt-3 w-full resize-none rounded-md border border-rc-border bg-rc-bg px-3 py-2 text-sm leading-relaxed text-rc-fg outline-none focus:border-rc-fg"
        />
      ) : (
        <p className="mt-3 rounded-md bg-rc-surface-hover/60 px-3 py-2 text-sm leading-relaxed text-rc-fg">
          {text}
        </p>
      )}

      {action.reason ? (
        <p className="mt-2 text-xs text-rc-fg-muted">{action.reason}</p>
      ) : null}
      {action.riskNote ? (
        <p className="mt-1 text-xs font-medium text-rc-fg">
          {action.riskNote}
        </p>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {isHandoff ? (
          <>
            <Button
              purpose="action"
              style="primary"
              disabled={paused}
              onClick={() => {
                navigator.clipboard?.writeText(text).catch(() => {});
                onSent(action.id);
              }}
            >
              Salin & buka
            </Button>
            <Button
              purpose="action"
              style="ghost"
              onClick={() => setEditing((v) => !v)}
            >
              {editing ? "Selesai" : "Edit"}
            </Button>
          </>
        ) : (
          <>
            <Button
              purpose="action"
              style="primary"
              disabled={paused}
              onClick={() => onApprove(action.id, text)}
            >
              Setujui & kirim
            </Button>
            <Button
              purpose="action"
              style="ghost"
              onClick={() => setEditing((v) => !v)}
            >
              {editing ? "Selesai" : "Edit"}
            </Button>
            <Button
              purpose="action"
              style="ghost"
              onClick={() => onReject(action.id, "ditolak dari antrean")}
            >
              Tolak
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
