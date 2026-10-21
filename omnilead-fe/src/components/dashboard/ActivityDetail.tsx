"use client";

import type { Activity, AgentTrace, LeadProfile } from "@/lib/types";
import { channelLabel, scoreLabel } from "@/lib/ui";
import { ChannelIcon, ScoreBadge } from "@/components/primitives";
import { TimeAgo } from "@/components/TimeAgo";

export function ActivityDetail({
  activity,
  lead,
  trace,
}: {
  activity: Activity;
  lead: LeadProfile;
  trace?: AgentTrace;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-rc-border bg-rc-surface p-6">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <ChannelIcon channel={activity.channel} size="md" />
            <div>
              <div className="text-sm font-semibold text-rc-fg">
                {activity.authorName}
              </div>
              <div className="text-xs text-rc-fg-muted">
                {channelLabel[activity.channel]} · {activity.authorHandle} ·{" "}
                <TimeAgo iso={activity.receivedAt} />
              </div>
            </div>
          </div>
          <ScoreBadge score={activity.score} />
        </div>
        <p className="mt-3 text-sm leading-relaxed text-rc-fg">
          {activity.text}
        </p>
        {activity.postContext ? (
          <p className="mt-1 text-xs text-rc-fg-subtle">
            {activity.postContext}
          </p>
        ) : null}
        {activity.reason ? (
          <p className="mt-2 text-xs text-rc-fg-muted">{activity.reason}</p>
        ) : null}
      </div>

      <div className="rounded-lg border border-rc-border bg-rc-surface p-6">
        <div className="flex items-center justify-between gap-2">
          <span className="text-sm font-semibold text-rc-fg">
            {lead.name}
            {lead.company ? (
              <span className="font-normal text-rc-fg-muted">
                {" "}
                · {lead.company}
              </span>
            ) : null}
          </span>
          <span className="text-sm font-semibold tabular-nums text-rc-fg">
            {lead.scoreValue}
          </span>
        </div>
        <p className="mt-0.5 text-xs text-rc-fg-muted">
          {scoreLabel[lead.score]} · tahap {lead.stage}
        </p>
        <p className="mt-2 text-sm leading-relaxed text-rc-fg-muted">
          {lead.summary}
        </p>
      </div>

      {trace ? (
        <details className="rounded-lg border border-rc-border bg-rc-surface p-6">
          <summary className="cursor-pointer text-sm font-medium text-rc-fg">
            Langkah agen
            <span className="ml-2 font-normal text-rc-fg-muted">
              {trace.goal}
            </span>
          </summary>
          <div className="mt-3 space-y-2 border-t border-rc-border pt-3 text-xs">
            {trace.steps.map((s, i) => (
              <div key={i} className="text-rc-fg-muted">
                <span className="text-rc-fg-subtle">
                  {String(i + 1).padStart(2, "0")}{" "}
                </span>
                <span className="font-semibold text-rc-fg">{s.tool}</span>{" "}
                <span className="text-rc-fg-subtle">({s.input})</span>
                <div className="mt-0.5 pl-5 text-rc-fg-muted">{s.output}</div>
              </div>
            ))}
          </div>
        </details>
      ) : (
        <p className="text-sm text-rc-fg-muted">
          Belum ada draf balasan. Tinjau manual dulu.
        </p>
      )}
    </div>
  );
}
