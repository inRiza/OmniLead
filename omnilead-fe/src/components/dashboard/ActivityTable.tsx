"use client";

import type { Activity } from "@/lib/types";
import { channelLabel, cn } from "@/lib/ui";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableShell,
} from "@/components/ui/table";
import { ChannelIcon, ScoreBadge } from "@/components/primitives";
import { TimeAgo } from "@/components/TimeAgo";

const urgencyRank = { tinggi: 0, sedang: 1, rendah: 2 } as const;

export function ActivityTable({
  activities,
  selectedId,
  onSelect,
}: {
  activities: Activity[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const rows = [...activities].sort(
    (a, b) =>
      urgencyRank[a.urgency] - urgencyRank[b.urgency] ||
      b.scoreValue - a.scoreValue,
  );

  return (
    <TableShell>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Pelanggan</TableHead>
            <TableHead className="hidden md:table-cell">Pesan</TableHead>
            <TableHead>Skor</TableHead>
            <TableHead className="hidden sm:table-cell">Urgensi</TableHead>
            <TableHead className="text-right">Waktu</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((a) => {
            const active = a.id === selectedId;
            return (
              <TableRow
                key={a.id}
                data-state={active ? "selected" : undefined}
                onClick={() => onSelect(a.id)}
                className="cursor-pointer"
              >
                <TableCell>
                  <div className="flex items-start gap-2.5">
                    <ChannelIcon channel={a.channel} size="md" />
                    <div className="min-w-0">
                      <div className="truncate font-medium text-rc-fg">
                        {a.authorName}
                      </div>
                      <div className="text-xs text-rc-fg-muted">
                        {channelLabel[a.channel]} · {a.kind}
                      </div>
                    </div>
                  </div>
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <p className="line-clamp-2 max-w-xl text-rc-fg-muted">
                    {a.text}
                  </p>
                </TableCell>
                <TableCell>
                  <ScoreBadge score={a.score} />
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  <span
                    className={cn(
                      "text-xs capitalize",
                      a.urgency === "tinggi"
                        ? "font-medium text-rc-fg"
                        : "text-rc-fg-muted",
                    )}
                  >
                    {a.urgency}
                  </span>
                </TableCell>
                <TableCell className="text-right text-xs text-rc-fg-subtle">
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
