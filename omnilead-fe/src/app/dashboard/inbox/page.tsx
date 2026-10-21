"use client";

import { useMemo, useState } from "react";
import {
  activities as seedActivities,
  leads,
  proposedActions as seedActions,
  traces,
} from "@/lib/mock";
import type { ProposedAction } from "@/lib/types";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { ActivityTable } from "@/components/dashboard/ActivityTable";
import { ActivityDetail } from "@/components/dashboard/ActivityDetail";
import { ApprovalQueue } from "@/components/dashboard/ApprovalQueue";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import {
  Sheet,
  SheetBody,
  SheetContent,
  SheetHeader,
} from "@/components/ui/sheet";

export default function InboxPage() {
  const { paused } = useDashboard();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [actions, setActions] = useState<ProposedAction[]>(seedActions);

  const selected = useMemo(
    () => (selectedId ? seedActivities.find((a) => a.id === selectedId) : null),
    [selectedId],
  );
  const lead = selected ? leads[selected.leadId] : null;
  const trace = selected ? traces[selected.id] : undefined;
  const activityActions = selectedId
    ? actions.filter((a) => a.activityId === selectedId)
    : [];
  const queueCount = activityActions.filter(
    (a) => a.status === "pending" || a.status === "awaiting_manual_send",
  ).length;

  function update(id: string, patch: Partial<ProposedAction>) {
    setActions((prev) => prev.map((a) => (a.id === id ? { ...a, ...patch } : a)));
  }

  return (
    <>
      <Topbar
        title="Workspace"
        subtitle="Pesan masuk dari semua kanal. Anda yang putuskan balasannya."
      />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="p-5 md:p-6">
          <ActivityTable
            activities={seedActivities}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </div>
      </ContentInset>

      <Sheet
        open={selectedId !== null && selected !== null && lead !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedId(null);
        }}
      >
        <SheetContent className="gap-0 p-0 sm:max-w-lg">
          {selected && lead ? (
            <>
              <SheetHeader>
                <p className="text-base font-semibold text-rc-fg">
                  {selected.authorName}
                </p>
                <p className="text-sm text-rc-fg-muted">
                  {queueCount > 0
                    ? `${queueCount} balasan menunggu persetujuan`
                    : "Tinjau percakapan"}
                </p>
              </SheetHeader>
              <SheetBody className="flex flex-col gap-5">
                <ActivityDetail
                  activity={selected}
                  lead={lead}
                  trace={trace}
                />
                <div>
                  <h2 className="mb-2 text-sm font-semibold text-rc-fg">
                    Balasan siap kirim
                  </h2>
                  <ApprovalQueue
                    actions={activityActions}
                    paused={paused}
                    onApprove={(id, text) =>
                      update(id, { status: "executed", text })
                    }
                    onReject={(id) => update(id, { status: "rejected" })}
                    onSent={(id) => update(id, { status: "sent_manually" })}
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
