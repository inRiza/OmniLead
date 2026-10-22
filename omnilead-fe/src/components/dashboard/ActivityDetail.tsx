"use client";

import Link from "next/link";
import { ArrowRight, Info } from "lucide-react";
import type { Activity, LeadProfile } from "@/lib/types";
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
import { Badge, ChannelIcon } from "@/components/primitives";
import { LeadInsights } from "@/components/dashboard/LeadInsights";
import { TimeAgo } from "@/components/TimeAgo";

const card = "rounded-xl border border-rc-border bg-rc-surface";

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
}: {
  activity: Activity;
  lead: LeadProfile | null;
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
          {activity.folder ? <Meta label="Folder" value={activity.folder} /> : null}
        </div>
        {activity.source === "openclaw" ? (
          <p className="mx-5 mt-4 rounded-lg bg-amber-50 px-3.5 py-2.5 text-sm text-amber-800">
            Pesan ini dibaca dari layar Instagram lewat OpenClaw, bukan dari Meta. Nama bisa berupa nama tampilan, isi hanya pratinjau terakhir, dan balasan harus dikirim manual. Hubungkan Meta API untuk data resmi.
          </p>
        ) : null}
        {activity.reason ? (
          <div className="mx-5 mt-4 flex gap-2.5 border-t border-rc-border pt-4 text-sm text-rc-fg-muted">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-rc-accent" aria-hidden />
            <p>{activity.reason}</p>
          </div>
        ) : null}
        <div className="h-5" />
      </section>

      {lead ? (
        <>
          <LeadInsights
            summary={lead.summary}
            score={lead.score}
            scoreValue={lead.scoreValue}
            reasons={lead.scoreReasons}
            needs={{ ...lead.needs, ...Object.fromEntries(Object.entries(activity.needs).filter(([, v]) => v !== undefined)) }}
            estimatedValue={lead.estimatedValue}
            nextStep={lead.nextStep}
            scoredAt={lead.scoredAt}
          />
          <section className={`${card} flex flex-wrap items-center justify-between gap-3 px-5 py-4`}>
            <div className="min-w-0">
              <p className="text-xs font-medium text-rc-fg-muted">Lead</p>
              <Link href={`/dashboard/leads/${lead.id}`} className="mt-0.5 block truncate text-sm font-semibold text-rc-fg hover:text-rc-accent">
                {lead.name}
              </Link>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Meta label="Tahap" value={stageLabel[lead.stage]} tone={stageTone[lead.stage]} />
                {lead.channels.map((c) => (
                  <Meta key={c} label="Kanal" value={channelLabel[c]} />
                ))}
              </div>
            </div>
            <Link href={`/dashboard/leads/${lead.id}`} className="inline-flex items-center gap-1 text-sm font-medium text-rc-accent hover:underline">
              Buka profil lead
              <ArrowRight aria-hidden className="h-3.5 w-3.5" />
            </Link>
          </section>
        </>
      ) : (
        <p className="rounded-xl border border-dashed border-rc-border-strong px-5 py-4 text-sm text-rc-fg-muted">
          Pesan ini belum terhubung ke lead mana pun.
        </p>
      )}

    </div>
  );
}
