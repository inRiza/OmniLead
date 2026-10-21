"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { Channel } from "@/lib/types";
import { channelLabel, cn } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { ActivityTable } from "@/components/dashboard/ActivityTable";
import { ActivityDetail } from "@/components/dashboard/ActivityDetail";
import { ApprovalQueue } from "@/components/dashboard/ApprovalQueue";
import { PasteMessage } from "@/components/dashboard/PasteMessage";
import { Button } from "@/components/action/button";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import {
  Sheet,
  SheetBody,
  SheetContent,
  SheetHeader,
} from "@/components/ui/sheet";

const OPEN = new Set(["pending", "awaiting_manual_send", "failed"]);

const KIND_LABEL = { komentar: "Komentar", dm: "DM / pesan", email: "Email" } as const;
type KindFilter = keyof typeof KIND_LABEL | "all";

export default function InboxPage() {
  const d = useDashboard();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [channel, setChannel] = useState<Channel | "all">("all");
  const [kind, setKind] = useState<KindFilter>("all");
  const [pasting, setPasting] = useState(false);

  const rows = useMemo(
    () =>
      d.activities.filter(
        (a) =>
          (channel === "all" || a.channel === channel) &&
          (kind === "all" || a.kind === kind),
      ),
    [d.activities, channel, kind],
  );
  const channelsInUse = useMemo(
    () => [...new Set(d.activities.map((a) => a.channel))],
    [d.activities],
  );

  const selected = selectedId
    ? (d.activities.find((a) => a.id === selectedId) ?? null)
    : null;
  const lead = selected ? (d.leadsById[selected.leadId] ?? null) : null;
  const trace = selected ? d.traces[selected.id] : undefined;
  const activityActions = selectedId
    ? d.actions.filter((a) => a.activityId === selectedId)
    : [];
  const queueCount = activityActions.filter((a) => OPEN.has(a.status)).length;

  return (
    <>
      <Topbar
        title="Workspace"
        subtitle="Pesan masuk dari semua kanal. Anda yang putuskan balasannya."
      />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="flex flex-col gap-3 p-5 md:p-6">
          <div className="flex flex-wrap items-center justify-end gap-2">
            <Link href="/dashboard/agent" className="rounded-md border border-rc-border px-3 py-2 text-sm font-medium text-rc-fg hover:bg-rc-surface-hover">Aktivitas agen</Link>
            <Button
              purpose="action"
              style={pasting ? "primary" : "secondary"}
              onClick={() => setPasting((v) => !v)}
            >
              {pasting ? "Tutup" : "Tempel pesan"}
            </Button>
          </div>
          {pasting ? (
            <PasteMessage
              onCreated={(id) => {
                setPasting(false);
                setChannel("all");
                setKind("all");
                setSelectedId(id);
              }}
            />
          ) : null}

          <div className="rc-scrollbar -mx-1 flex items-center gap-3 overflow-x-auto px-1 pb-1">
          <div className="flex shrink-0 gap-1.5" role="group" aria-label="Filter jenis aktivitas">
            {(["all", "komentar", "dm", "email"] as const).map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => setKind(k)}
                aria-pressed={kind === k}
                className={cn(
                  "shrink-0 whitespace-nowrap rounded-md border px-2.5 py-1 text-sm transition-colors",
                  kind === k
                    ? "border-rc-accent bg-rc-accent-soft text-rc-accent"
                    : "border-rc-border bg-rc-surface text-rc-fg-muted hover:bg-rc-surface-hover",
                )}
              >
                {k === "all" ? "Semua jenis" : KIND_LABEL[k]}
              </button>
            ))}
          </div>

          {channelsInUse.length > 1 ? (
            <div className="flex shrink-0 gap-1.5 border-l border-rc-border pl-3" role="group" aria-label="Filter kanal">
              {(["all", ...channelsInUse] as const).map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setChannel(c)}
                  aria-pressed={channel === c}
                  className={cn(
                    "shrink-0 whitespace-nowrap rounded-md border px-2.5 py-1 text-sm transition-colors",
                    channel === c
                      ? "border-rc-accent bg-rc-accent-soft text-rc-accent"
                      : "border-rc-border bg-rc-surface text-rc-fg-muted hover:bg-rc-surface-hover",
                  )}
                >
                  {c === "all" ? "Semua kanal" : channelLabel[c]}
                </button>
              ))}
            </div>
          ) : null}
          </div>

          {d.loaded && rows.length === 0 ? (
            <p className="rounded-lg border border-rc-border bg-rc-surface px-4 py-8 text-center text-sm text-rc-fg-muted">
              {d.channels.some((c) => c.connected)
                ? "Akun sudah terhubung, tetapi belum ada pesan yang diterima pada filter ini. Kirim pesan baru dari akun lain, atau gunakan Tempel pesan."
                : "Belum ada aktivitas. Hubungkan kanal komunikasi atau media sosial untuk mulai."}
            </p>
          ) : (
            <ActivityTable
              activities={rows}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          )}
        </div>
      </ContentInset>

      <Sheet
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null);
        }}
      >
        <SheetContent className="gap-0 p-0 sm:max-w-3xl">
          {selected ? (
            <>
              <SheetHeader>
                <p className="text-base font-semibold text-rc-fg">
                  {selected.authorName}
                </p>
                <p className="text-sm text-rc-fg-muted">
                  {queueCount > 0
                    ? `${queueCount} aksi menunggu keputusan Anda`
                    : "Tinjau percakapan"}
                </p>
              </SheetHeader>
              <SheetBody className="flex flex-col gap-5">
                {lead ? (
                  <ActivityDetail activity={selected} lead={lead} trace={trace} actions={activityActions} />
                ) : null}
                <div>
                  <h2 className="mb-2 text-sm font-semibold text-rc-fg">
                    Balasan siap kirim
                  </h2>
                  <ApprovalQueue
                    actions={activityActions}
                    paused={d.paused}
                    leadsById={d.leadsById}
                    onApprove={d.approve}
                    onReject={d.reject}
                    onRetry={d.retry}
                    onSent={d.markSent}
                  />
                </div>
              </SheetBody>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </>
  );
}
