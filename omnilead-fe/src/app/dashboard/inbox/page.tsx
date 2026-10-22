"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import type { Channel } from "@/lib/types";
import { activityStatus, channelLabel } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { ActivityTable, sortActivities, type ActivitySort } from "@/components/dashboard/ActivityTable";
import { ActivityDetail } from "@/components/dashboard/ActivityDetail";
import { AgentReasoning } from "@/components/dashboard/AgentReasoning";
import { AgentResults } from "@/components/dashboard/AgentResults";
import { Select } from "@/components/ui/select";
import { ChannelIcon } from "@/components/primitives";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import {
  Sheet,
  SheetBody,
  SheetContent,
  SheetHeader,
} from "@/components/ui/sheet";

const KIND_LABEL = { komentar: "Komentar", dm: "Pesan langsung", email: "Email" } as const;
type KindFilter = keyof typeof KIND_LABEL | "all";

const STATUSES = ["Perlu dibalas", "Ditangani agen", "Perlu tinjauan", "Selesai"] as const;
type StatusFilter = (typeof STATUSES)[number] | "all";

const CHANNELS: Channel[] = ["whatsapp", "instagram", "facebook", "email"];

export default function InboxPage() {
  return (
    <Suspense>
      <InboxView />
    </Suspense>
  );
}

function InboxView() {
  const d = useDashboard();
  const params = useSearchParams();
  const [selectedId, setSelectedId] = useState<string | null>(params.get("id"));
  const [channel, setChannel] = useState<Channel | "all">("all");
  const [kind, setKind] = useState<KindFilter>("all");
  const [status, setStatus] = useState<StatusFilter>((params.get("status") as StatusFilter | null) ?? "all");
  const [sort, setSort] = useState<ActivitySort>("priority");
  const [query, setQuery] = useState("");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return sortActivities(
      d.activities.filter(
        (a) =>
          (channel === "all" || a.channel === channel) &&
          (kind === "all" || a.kind === kind) &&
          (status === "all" || activityStatus(a).label === status) &&
          (!q || `${a.authorName} ${a.authorHandle} ${a.text}`.toLowerCase().includes(q)),
      ),
      sort,
    );
  }, [d.activities, channel, kind, status, sort, query]);
  const filtered = channel !== "all" || kind !== "all" || status !== "all" || query.trim() !== "";

  const selected = selectedId
    ? (d.activities.find((a) => a.id === selectedId) ?? null)
    : null;
  const lead = selected ? (d.leadsById[selected.leadId] ?? null) : null;
  const trace = selected ? d.traces[selected.id] : undefined;
  const activityActions = selectedId
    ? d.actions.filter((a) => a.activityId === selectedId)
    : [];

  return (
    <>
      <Topbar
        title="Workspace"
        subtitle="Pesan masuk dari semua kanal. Anda yang putuskan balasannya."
      />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="flex flex-col gap-3 p-5 md:p-6">
          <div className="flex flex-wrap items-center gap-2">
            <label className="relative min-w-56 flex-1">
              <span className="sr-only">Cari percakapan</span>
              <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-rc-fg-subtle" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Cari nama, handle, atau isi pesan"
                className="min-h-10 w-full rounded-md border border-rc-border bg-rc-surface pr-3 pl-9 text-sm text-rc-fg outline-none placeholder:text-rc-fg-subtle focus:border-rc-accent focus:ring-2 focus:ring-rc-accent/15"
              />
            </label>
            <Select
              label="Kanal"
              className="w-40"
              value={channel}
              onChange={setChannel}
              options={[
                { value: "all", label: "Semua kanal" },
                ...CHANNELS.map((c) => ({ value: c, label: channelLabel[c], icon: <ChannelIcon channel={c} /> })),
              ]}
            />
            <Select
              label="Jenis"
              className="w-40"
              value={kind}
              onChange={setKind}
              options={[
                { value: "all", label: "Semua jenis" },
                ...(Object.keys(KIND_LABEL) as (keyof typeof KIND_LABEL)[]).map((k) => ({ value: k, label: KIND_LABEL[k] })),
              ]}
            />
            <Select
              label="Status"
              className="w-52"
              value={status}
              onChange={setStatus}
              options={[{ value: "all", label: "Semua status" }, ...STATUSES.map((v) => ({ value: v, label: v }))]}
            />
            <Select
              label="Urutkan"
              className="w-44"
              align="right"
              value={sort}
              onChange={setSort}
              options={[
                { value: "priority", label: "Prioritas" },
                { value: "newest", label: "Terbaru" },
                { value: "oldest", label: "Paling lama menunggu" },
              ]}
            />
          </div>

          <p className="text-sm text-rc-fg-muted">
            {rows.length} percakapan{filtered ? " sesuai filter" : ""}
          </p>

          {d.loaded && rows.length === 0 ? (
            <p className="rounded-xl border border-dashed border-rc-border-strong bg-rc-surface px-4 py-12 text-center text-sm text-rc-fg-muted">
              {filtered
                ? "Tidak ada percakapan yang cocok dengan filter ini."
                : "Pesan dari kanal yang terhubung akan muncul di sini."}
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
                  {activityActions.length ? `${activityActions.length} tindakan agen` : "Tinjau percakapan"}
                </p>
              </SheetHeader>
              <SheetBody className="flex flex-col gap-5">
                <ActivityDetail activity={selected} lead={lead} />
                <AgentReasoning activity={selected} trace={trace} actions={activityActions} onRefresh={d.refresh} />
                <div>
                  <h2 className="mb-3 text-sm font-semibold text-rc-fg">Hasil kerja agen</h2>
                  <AgentResults
                    actions={activityActions}
                    onFeedback={(id, reason) => d.feedback(id, "bad", reason)}
                    onApprove={d.approve}
                    onSent={d.markSent}
                    onRetry={d.retry}
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
