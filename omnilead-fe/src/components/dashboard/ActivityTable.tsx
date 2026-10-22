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
import { Badge, ChannelIcon, ScoreBadge } from "@/components/primitives";
import { TimeAgo } from "@/components/TimeAgo";

const urgencyRank = { tinggi: 0, sedang: 1, rendah: 2 } as const;

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
                </TableCell>
                <TableCell>
                  <Badge tone={status.tone} dot>
                    {status.label}
                  </Badge>
                </TableCell>
                <TableCell className="hidden lg:table-cell">
                  <span className="flex items-center gap-2">
                    <ScoreBadge score={a.score} />
                    <span className="text-xs text-rc-fg-muted tabular-nums">{a.scoreValue}</span>
                  </span>
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  <Badge tone={urgencyTone[a.urgency]}>
                    {cap(a.urgency)}
                  </Badge>
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
