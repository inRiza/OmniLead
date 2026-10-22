"use client";

import Link from "next/link";
import {
  ArrowRight,
  CircleAlert,
  CircleCheck,
  CircleX,
  Info,
  ListChecks,
  Route,
  ShieldCheck,
  Target,
  Wrench,
} from "lucide-react";
import type { Activity, AgentTrace, LeadProfile } from "@/lib/types";
import {
  activityStatus,
  cap,
  channelLabel,
  kindLabel,
  sentimentTone,
  stageLabel,
  stageTone,
  urgencyTone,
} from "@/lib/ui";
import { Badge, ChannelIcon, ScoreBadge } from "@/components/primitives";
import { TimeAgo } from "@/components/TimeAgo";

const card = "rounded-xl border border-rc-border bg-rc-surface";

const TOOL_LABEL: Record<string, string> = {
  cari_katalog: "Cari katalog",
  cek_kebijakan: "Cek kebijakan",
  cek_riwayat: "Cek riwayat pelanggan",
  cek_stok: "Cek ketersediaan",
  hitung_harga: "Hitung harga",
  identifikasi: "Kenali pelanggan",
  klasifikasi: "Klasifikasi pesan",
  susun_draf: "Susun balasan",
};

function toolLabel(tool: string) {
  return TOOL_LABEL[tool] ?? cap(tool.replace(/_/g, " "));
}

function Meta({ label, value, tone = "gray" }: { label: string; value: string; tone?: Parameters<typeof Badge>[0]["tone"] }) {
  return (
    <Badge tone={tone}>
      <span className="opacity-70">{label}:</span> {value}
    </Badge>
  );
}

export function ActivityDetail({
  activity,
  lead,
  trace,
}: {
  activity: Activity;
  lead: LeadProfile | null;
  trace?: AgentTrace;
}) {
  const status = activityStatus(activity);
  return (
    <div className="flex flex-col gap-4">
      <section className={card}>
        <div className="flex items-start justify-between gap-3 p-5 pb-4">
          <div className="flex min-w-0 items-center gap-3">
            <ChannelIcon channel={activity.channel} size="md" />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-rc-fg">{activity.authorName}</p>
              <p className="truncate text-xs text-rc-fg-muted">
                {activity.authorHandle || channelLabel[activity.channel]}
                <span className="mx-1.5 text-rc-fg-subtle">/</span>
                <TimeAgo iso={activity.receivedAt} />
              </p>
            </div>
          </div>
          <Badge tone={status.tone} dot>
            {status.label}
          </Badge>
        </div>
        <div className="px-5">
          <p className="rounded-lg rounded-tl-none bg-rc-bg px-4 py-3 text-sm leading-relaxed text-rc-fg">{activity.text}</p>
          {activity.postContext ? <p className="mt-2 text-xs text-rc-fg-subtle">{activity.postContext}</p> : null}
        </div>
        <div className="flex flex-wrap gap-1.5 px-5 pt-4">
          <Meta label="Kanal" value={channelLabel[activity.channel]} />
          <Meta label="Asal" value={kindLabel[activity.kind]} />
          <Meta label="Urgensi" value={cap(activity.urgency)} tone={urgencyTone[activity.urgency]} />
          {activity.sentiment ? <Meta label="Sentimen" value={cap(activity.sentiment)} tone={sentimentTone[activity.sentiment]} /> : null}
        </div>
        {activity.reason ? (
          <div className="mx-5 mt-4 flex gap-2.5 border-t border-rc-border pt-4 text-sm text-rc-fg-muted">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-rc-accent" aria-hidden />
            <p>{activity.reason}</p>
          </div>
        ) : null}
        <div className="h-5" />
      </section>

      {lead ? (
        <section className={`${card} p-5`}>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-medium text-rc-fg-muted">Lead</p>
              <Link href={`/dashboard/leads/${lead.id}`} className="mt-0.5 block truncate text-sm font-semibold text-rc-fg hover:text-rc-accent">
                {lead.name}
              </Link>
              {lead.company ? <p className="truncate text-xs text-rc-fg-muted">{lead.company}</p> : null}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold text-rc-fg tabular-nums">{lead.scoreValue}</span>
              <ScoreBadge score={lead.score} />
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            <Meta label="Tahap" value={stageLabel[lead.stage]} tone={stageTone[lead.stage]} />
            {lead.channels.map((c) => (
              <Meta key={c} label="Kanal" value={channelLabel[c]} />
            ))}
          </div>
          {lead.summary ? <p className="mt-3 text-sm leading-relaxed text-rc-fg-muted">{lead.summary}</p> : null}
          <Link href={`/dashboard/leads/${lead.id}`} className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-rc-accent hover:underline">
            Buka profil lead
            <ArrowRight aria-hidden className="h-3.5 w-3.5" />
          </Link>
        </section>
      ) : (
        <p className="rounded-xl border border-dashed border-rc-border-strong px-5 py-4 text-sm text-rc-fg-muted">
          Pesan ini belum terhubung ke lead mana pun.
        </p>
      )}

      {trace ? (
        <TraceLog trace={trace} />
      ) : (
        <p className="flex items-start gap-2.5 rounded-xl bg-rc-bg px-5 py-4 text-sm text-rc-fg-muted">
          <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          {activity.eventStatus === "review"
            ? "Pesan ini dicurigai berisi instruksi manipulatif dan perlu ditinjau manual."
            : activity.eventStatus === "held"
              ? "Agen dijeda. Pesan ini akan dianalisis setelah agen dilanjutkan."
              : activity.eventStatus === "agent_error"
                ? "Service agen tidak tersedia. Pesan belum dianalisis."
                : "Belum ada jejak agen untuk pesan ini."}
        </p>
      )}
    </div>
  );
}

function TraceLog({ trace }: { trace: AgentTrace }) {
  const passed = trace.guard.filter((g) => g.passed).length;
  return (
    <details className={`${card} group`}>
      <summary className="flex cursor-pointer list-none items-center gap-3 p-5 [&::-webkit-details-marker]:hidden">
        <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-rc-accent-soft text-rc-accent">
          <Route className="h-4 w-4" aria-hidden />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-rc-fg">Langkah agen</span>
          <span className="block truncate text-xs text-rc-fg-muted">
            {trace.steps.length} langkah{trace.guard.length ? `, ${passed} dari ${trace.guard.length} pengecekan lolos` : ""}
          </span>
        </span>
        <ArrowRight aria-hidden className="h-4 w-4 text-rc-fg-muted transition-transform group-open:rotate-90" />
      </summary>

      <div className="flex flex-col gap-5 border-t border-rc-border p-5">
        {trace.goal ? (
          <div className="flex gap-2.5">
            <Target className="mt-0.5 h-4 w-4 shrink-0 text-rc-fg-muted" aria-hidden />
            <div>
              <p className="text-xs font-medium text-rc-fg-muted">Tujuan</p>
              <p className="mt-0.5 text-sm text-rc-fg">{trace.goal}</p>
            </div>
          </div>
        ) : null}

        {trace.plan.length > 0 ? (
          <div className="flex gap-2.5">
            <ListChecks className="mt-0.5 h-4 w-4 shrink-0 text-rc-fg-muted" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-rc-fg-muted">Rencana</p>
              <ol className="mt-1.5 flex flex-col gap-1.5">
                {trace.plan.map((p, i) => (
                  <li key={i} className="flex gap-2 text-sm text-rc-fg">
                    <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-rc-bg text-xs font-medium text-rc-fg-muted tabular-nums">
                      {i + 1}
                    </span>
                    {cap(p)}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        ) : null}

        {trace.steps.length > 0 ? (
          <div className="flex gap-2.5">
            <Wrench className="mt-0.5 h-4 w-4 shrink-0 text-rc-fg-muted" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-rc-fg-muted">Log eksekusi</p>
              <ol className="relative mt-2 flex flex-col gap-3 pl-4">
                <span aria-hidden className="absolute top-1.5 bottom-1.5 left-[3px] w-px bg-rc-border" />
                {trace.steps.map((s, i) => (
                  <li key={i} className="relative">
                    <span aria-hidden className="absolute top-1.5 -left-4 h-[7px] w-[7px] rounded-full bg-rc-accent" />
                    <p className="text-sm font-medium text-rc-fg">{toolLabel(s.tool)}</p>
                    {s.input ? <p className="mt-0.5 font-mono text-xs break-words text-rc-fg-subtle">{s.input}</p> : null}
                    {s.output ? <p className="mt-1 rounded-md bg-rc-bg px-3 py-2 text-sm text-rc-fg-muted">{cap(s.output)}</p> : null}
                  </li>
                ))}
              </ol>
            </div>
          </div>
        ) : null}

        {trace.guard.length > 0 ? (
          <div className="flex gap-2.5">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-rc-fg-muted" aria-hidden />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-rc-fg-muted">Pengecekan keamanan</p>
              {trace.guardSummary ? <p className="mt-0.5 text-sm text-rc-fg-muted">{cap(trace.guardSummary)}</p> : null}
              <ul className="mt-2 flex flex-col gap-1.5">
                {trace.guard.map((g, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    {g.passed ? (
                      <CircleCheck className="h-4 w-4 shrink-0 text-emerald-600" aria-hidden />
                    ) : (
                      <CircleX className="h-4 w-4 shrink-0 text-red-600" aria-hidden />
                    )}
                    <span className={g.passed ? "text-rc-fg" : "font-medium text-red-700"}>{cap(g.label)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}
      </div>
    </details>
  );
}
