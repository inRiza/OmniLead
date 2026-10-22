"use client";

import type { Activity } from "@/lib/types";
import { activityStatus, cap, channelLabel, kindLabel, urgencyTone } from "@/lib/ui";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableShell,
} from "@/components/ui/table";
import { Loader2 } from "lucide-react";
import { Badge, ChannelIcon, ScoreBadge } from "@/components/primitives";
import { TimeAgo } from "@/components/TimeAgo";

const urgencyRank = { tinggi: 0, sedang: 1, rendah: 2 } as const;

function Skeleton({ className }: { className: string }) {
  return <span aria-hidden className={`block animate-pulse rounded-md bg-rc-surface-hover motion-reduce:animate-none ${className}`} />;
}

function Pending() {
  return <span className="text-xs text-rc-fg-subtle">Belum dianalisis</span>;
}

export type ActivitySort = "priority" | "newest" | "oldest";

export function sortActivities(list: Activity[], sort: ActivitySort) {
  const rows = [...list];
  if (sort === "newest") return rows.sort((a, b) => b.receivedAt.localeCompare(a.receivedAt));
  if (sort === "oldest") return rows.sort((a, b) => a.receivedAt.localeCompare(b.receivedAt));
  return rows.sort(
    (a, b) => urgencyRank[a.urgency] - urgencyRank[b.urgency] || b.scoreValue - a.scoreValue,
  );
}

export function ActivityTable({
  activities,
  selectedId,
  onSelect,
}: {
  activities: Activity[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <TableShell>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Pelanggan</TableHead>
            <TableHead className="hidden md:table-cell">Pesan</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="hidden lg:table-cell">Skor</TableHead>
            <TableHead className="hidden sm:table-cell">Urgensi</TableHead>
            <TableHead className="text-right">Waktu</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {activities.map((a) => {
            const active = a.id === selectedId;
            const status = activityStatus(a);
            const loading = a.analysis === "queued" || a.analysis === "running";
            return (
              <TableRow
                key={a.id}
                data-state={active ? "selected" : undefined}
                onClick={() => onSelect(a.id)}
                className="cursor-pointer"
              >
                <TableCell>
                  <div className="flex items-center gap-3">
                    <ChannelIcon channel={a.channel} size="md" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        {a.status === "baru" && <span aria-label="Belum dibaca" className="h-2 w-2 shrink-0 rounded-full bg-rc-accent" />}
                        <span className="truncate font-medium text-rc-fg">{a.authorName}</span>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-1">
                        <Badge>Kanal: {channelLabel[a.channel]}</Badge>
                        <Badge>Asal: {kindLabel[a.kind]}</Badge>
                      </div>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <p className="line-clamp-2 max-w-xl text-rc-fg-muted">{a.text}</p>
                  {loading ? <Skeleton className="mt-2 h-3 w-2/3" /> : null}
                </TableCell>
                <TableCell>
                  {loading ? (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-rc-accent">
                      <Loader2 aria-hidden className={`h-3.5 w-3.5 ${a.analysis === "running" ? "motion-safe:animate-spin" : "opacity-40"}`} />
                      {a.analysis === "running" ? "Menganalisis…" : "Menunggu giliran"}
                    </span>
                  ) : (
                    <Badge tone={status.tone}>{status.label}</Badge>
                  )}
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  {loading ? (
                    <Skeleton className="h-6 w-20" />
                  ) : a.analysis === "none" ? (
                    <Pending />
                  ) : (
                    <span className="flex items-center gap-2 motion-safe:animate-[rc-fade-up_0.3s_ease-out]">
                      <ScoreBadge score={a.score} />
                      <span className="text-xs text-rc-fg-muted tabular-nums">{a.scoreValue}</span>
                    </span>
                  )}
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  {loading ? (
                    <Skeleton className="h-6 w-16" />
                  ) : a.analysis === "none" ? (
                    <Pending />
                  ) : (
                    <span className="motion-safe:animate-[rc-fade-up_0.3s_ease-out]">
                      <Badge tone={urgencyTone[a.urgency]}>{cap(a.urgency)}</Badge>
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-right text-xs whitespace-nowrap text-rc-fg-subtle">
                  <TimeAgo iso={a.receivedAt} />
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableShell>
  );
}
