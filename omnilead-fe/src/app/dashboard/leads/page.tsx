import { leads } from "@/lib/mock";
import { channelLabel } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { ChannelIcon, ScoreBadge } from "@/components/primitives";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableShell,
} from "@/components/ui/table";

const stageLabel: Record<string, string> = {
  baru: "Baru",
  tertarik: "Tertarik",
  penawaran: "Penawaran",
  deal: "Deal",
  batal: "Batal",
};

export default function LeadsPage() {
  const rows = Object.values(leads).sort((a, b) => b.scoreValue - a.scoreValue);

  return (
    <>
      <Topbar
        title="Lead"
        subtitle="Pelanggan yang sudah terhubung lintas kanal"
      />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="p-5 md:p-6">
          <TableShell>
            <Table>
              <TableHeader>
                <TableRow className="hover:bg-transparent">
                  <TableHead>Lead</TableHead>
                  <TableHead className="text-right">Skor</TableHead>
                  <TableHead className="text-right">Tahap</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((lead) => (
                  <TableRow key={lead.id}>
                    <TableCell className="align-top">
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                        <span className="font-semibold text-rc-fg">
                          {lead.name}
                        </span>
                        {lead.company ? (
                          <span className="text-sm text-rc-fg-muted">
                            {lead.company}
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-0.5 line-clamp-1 text-sm text-rc-fg-muted">
                        {lead.summary}
                      </p>
                      <div className="mt-1.5 flex flex-wrap items-center gap-1">
                        {lead.channels.map((c) => (
                          <span
                            key={c}
                            className="inline-flex items-center gap-1 rounded-md bg-rc-surface-hover/70 px-1.5 py-0.5 text-xs text-rc-fg-muted"
                          >
                            <ChannelIcon channel={c} />
                            {channelLabel[c]}
                          </span>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="align-top">
                      <div className="flex items-center justify-end gap-2">
                        <span className="text-sm font-semibold tabular-nums text-rc-fg">
                          {lead.scoreValue}
                        </span>
                        <ScoreBadge score={lead.score} />
                      </div>
                    </TableCell>
                    <TableCell className="text-right align-top">
                      <span className="rounded-md bg-rc-surface-hover/70 px-2 py-0.5 text-xs font-medium text-rc-fg-muted">
                        {stageLabel[lead.stage]}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableShell>
        </div>
      </ContentInset>
    </>
  );
}
