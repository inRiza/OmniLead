"use client";

import Link from "next/link";
import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Columns3, Rows3, Search } from "lucide-react";
import type { LeadProfile, LeadScore } from "@/lib/types";
import { cn, scoreLabel, stageLabel, stageTone } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { Badge, ChannelIcon, ScoreBadge } from "@/components/primitives";
import { Select } from "@/components/ui/select";
import { TimeAgo } from "@/components/TimeAgo";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow, TableShell } from "@/components/ui/table";

type Stage = LeadProfile["stage"];
const STAGES: Stage[] = ["baru", "tertarik", "penawaran", "deal", "batal"];
const SCORES: LeadScore[] = ["hot", "warm", "cold"];

function date(iso?: string) {
  if (!iso) return "Belum diketahui";
  return new Date(iso).toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}

export default function LeadsPage() {
  return (
    <Suspense>
      <LeadsView />
    </Suspense>
  );
}

function LeadsView() {
  const { leads, loaded } = useDashboard();
  const params = useSearchParams();
  const [query, setQuery] = useState("");
  const [stage, setStage] = useState<Stage | "all">((params.get("stage") as Stage | null) ?? "all");
  const [score, setScore] = useState<LeadScore | "all">((params.get("score") as LeadScore | null) ?? "all");
  const [view, setView] = useState<"table" | "pipeline">("table");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return leads
      .filter(
        (l) =>
          (stage === "all" || l.stage === stage) &&
          (score === "all" || l.score === score) &&
          (!q || `${l.name} ${l.company ?? ""} ${l.summary}`.toLowerCase().includes(q)),
      )
      .sort((a, b) => b.scoreValue - a.scoreValue || (a.createdAt ?? "").localeCompare(b.createdAt ?? ""));
  }, [leads, query, stage, score]);

  const filtered = stage !== "all" || score !== "all" || query.trim() !== "";

  return (
    <>
      <Topbar title="Lead" subtitle="Pelanggan yang dikenali lintas kanal, diurutkan menurut prioritas" />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="flex flex-col gap-3 p-5 md:p-6">
          <div className="flex flex-wrap items-center gap-2">
            <label className="relative min-w-56 flex-1">
              <span className="sr-only">Cari lead</span>
              <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-rc-fg-subtle" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Cari nama, perusahaan, atau ringkasan"
                className="min-h-10 w-full rounded-md border border-rc-border bg-rc-surface pr-3 pl-9 text-sm text-rc-fg outline-none placeholder:text-rc-fg-subtle focus:border-rc-accent focus:ring-2 focus:ring-rc-accent/15"
              />
            </label>
            <Select
              label="Tahap"
              className="w-40"
              value={stage}
              onChange={setStage}
              options={[{ value: "all", label: "Semua tahap" }, ...STAGES.map((s) => ({ value: s, label: stageLabel[s] }))]}
            />
            <Select
              label="Skor"
              className="w-36"
              value={score}
              onChange={setScore}
              options={[{ value: "all", label: "Semua skor" }, ...SCORES.map((s) => ({ value: s, label: scoreLabel[s] }))]}
            />
            <div role="group" aria-label="Tampilan" className="flex rounded-md border border-rc-border bg-rc-surface p-0.5">
              {(
                [
                  ["table", "Tabel", Rows3],
                  ["pipeline", "Pipeline", Columns3],
                ] as const
              ).map(([v, label, Icon]) => (
                <button
                  key={v}
                  type="button"
                  aria-pressed={view === v}
                  onClick={() => setView(v)}
                  className={cn(
                    "inline-flex min-h-8 cursor-pointer items-center gap-1.5 rounded px-3 text-sm transition-colors",
                    view === v ? "bg-rc-accent-soft font-medium text-rc-accent" : "text-rc-fg-muted hover:text-rc-fg",
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden />
                  {label}
                </button>
              ))}
            </div>
          </div>

          <p className="text-sm text-rc-fg-muted">
            {rows.length} lead{filtered ? " sesuai filter" : ""}
          </p>

          {loaded && rows.length === 0 ? (
            <p className="rounded-xl border border-dashed border-rc-border-strong bg-rc-surface px-4 py-12 text-center text-sm text-rc-fg-muted">
              {filtered
                ? "Tidak ada lead yang cocok dengan filter ini."
                : "Lead akan muncul setelah ada pelanggan atau percakapan yang berhasil diidentifikasi."}
            </p>
          ) : view === "pipeline" ? (
            <Pipeline leads={rows} />
          ) : (
            <TableShell>
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead>Lead</TableHead>
                    <TableHead>Skor</TableHead>
                    <TableHead>Tahap</TableHead>
                    <TableHead className="hidden xl:table-cell">Alasan prioritas</TableHead>
                    <TableHead className="hidden lg:table-cell">Kontak pertama</TableHead>
                    <TableHead className="text-right">Interaksi terakhir</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((lead) => (
                    <TableRow key={lead.id}>
                      <TableCell>
                        <Link href={`/dashboard/leads/${lead.id}`} className="font-semibold text-rc-fg hover:text-rc-accent">
                          {lead.name}
                        </Link>
                        <div className="mt-1 flex items-center gap-1.5">
                          {lead.channels.map((c) => (
                            <ChannelIcon key={c} channel={c} />
                          ))}
                          {lead.company ? <span className="ml-1 truncate text-xs text-rc-fg-muted">{lead.company}</span> : null}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2.5">
                          <span className="h-1.5 w-14 overflow-hidden rounded-full bg-rc-surface-hover">
                            <span className="block h-full rounded-full bg-rc-accent" style={{ width: `${lead.scoreValue}%` }} />
                          </span>
                          <span className="w-6 text-sm font-semibold text-rc-fg tabular-nums">{lead.scoreValue}</span>
                          <ScoreBadge score={lead.score} />
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge tone={stageTone[lead.stage]}>{stageLabel[lead.stage]}</Badge>
                      </TableCell>
                      <TableCell className="hidden max-w-sm xl:table-cell">
                        <p className="line-clamp-2 text-sm text-rc-fg-muted">{lead.scoreReason || lead.summary || "Belum diketahui"}</p>
                      </TableCell>
                      <TableCell className="hidden text-sm whitespace-nowrap text-rc-fg-muted lg:table-cell">{date(lead.createdAt)}</TableCell>
                      <TableCell className="text-right text-xs whitespace-nowrap text-rc-fg-subtle">
                        {lead.updatedAt ? <TimeAgo iso={lead.updatedAt} /> : "Belum diketahui"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableShell>
          )}
        </div>
      </ContentInset>
    </>
  );
}

function Pipeline({ leads }: { leads: LeadProfile[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
      {STAGES.map((s) => {
        const items = leads.filter((l) => l.stage === s);
        return (
          <section key={s} className="flex min-h-40 flex-col rounded-xl bg-rc-surface-hover/60 p-2">
            <header className="flex items-center justify-between px-2 pt-1 pb-2.5">
              <Badge tone={stageTone[s]} dot>
                {stageLabel[s]}
              </Badge>
              <span className="text-xs font-medium text-rc-fg-muted tabular-nums">{items.length}</span>
            </header>
            <div className="flex flex-col gap-2">
              {items.map((l) => (
                <Link
                  key={l.id}
                  href={`/dashboard/leads/${l.id}`}
                  className="rounded-lg border border-rc-border bg-rc-surface p-3 transition-colors hover:border-rc-accent/40"
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="min-w-0 truncate text-sm font-semibold text-rc-fg">{l.name}</span>
                    <ScoreBadge score={l.score} />
                  </div>
                  {l.company ? <p className="mt-0.5 truncate text-xs text-rc-fg-muted">{l.company}</p> : null}
                  <div className="mt-2.5 flex items-center justify-between">
                    <span className="flex gap-1">
                      {l.channels.map((c) => (
                        <ChannelIcon key={c} channel={c} />
                      ))}
                    </span>
                    <span className="text-xs font-semibold text-rc-fg-muted tabular-nums">{l.scoreValue}</span>
                  </div>
                </Link>
              ))}
              {items.length === 0 && <p className="px-2 py-4 text-center text-xs text-rc-fg-subtle">Kosong</p>}
            </div>
          </section>
        );
      })}
    </div>
  );
}
