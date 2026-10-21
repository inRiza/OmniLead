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
              <div className="text-sm text-rc-fg-muted">
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
          <p className="mt-1 text-sm text-rc-fg-subtle">
            {activity.postContext}
          </p>
        ) : null}
        {activity.reason ? (
          <p className="mt-2 text-sm text-rc-fg-muted">{activity.reason}</p>
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
        <p className="mt-0.5 text-sm text-rc-fg-muted">
          {scoreLabel[lead.score]} · tahap {lead.stage}
        </p>
        <p className="mt-2 text-sm leading-relaxed text-rc-fg-muted">
          {lead.summary}
        </p>
      </div>

      {trace ? (
        <details open className="rounded-lg border border-rc-border bg-rc-surface p-6">
          <summary className="cursor-pointer text-sm font-medium text-rc-fg">
            Langkah agen
            <span className="ml-2 font-normal text-rc-fg-muted">
              {trace.goal}
            </span>
          </summary>
          <div className="mt-3 space-y-2 border-t border-rc-border pt-3 text-sm">
            {trace.plan.length > 0 ? (
              <div className="text-rc-fg-muted">
                <span className="font-semibold text-rc-fg">Rencana</span>
                <ol className="mt-1 list-decimal pl-5">
                  {trace.plan.map((p, i) => (
                    <li key={i}>{p}</li>
                  ))}
                </ol>
              </div>
            ) : null}
            {trace.steps.map((s, i) => (
              <div key={i} className="text-rc-fg-muted">
                <span className="text-rc-fg-subtle">
                  {String(i + 1).padStart(2, "0")}{" "}
                </span>
                <span className="font-semibold text-rc-fg">{s.tool}</span>{" "}
                {s.input ? (
                  <span className="text-rc-fg-subtle">({s.input})</span>
                ) : null}
                <div className="mt-0.5 pl-5 text-rc-fg-muted">{s.output}</div>
              </div>
            ))}
            {trace.guard.length > 0 ? (
              <div className="border-t border-rc-border pt-2">
                <span className="font-semibold text-rc-fg">Guard</span>
                {trace.guardSummary ? (
                  <span className="ml-2 text-rc-fg-muted">{trace.guardSummary}</span>
                ) : null}
                <ul className="mt-1 space-y-0.5">
                  {trace.guard.map((g, i) => (
                    <li
                      key={i}
                      className={g.passed ? "text-rc-fg-muted" : "font-medium text-rc-danger"}
                    >
                      {g.passed ? "Lolos" : "Ditahan"}: {g.label}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {trace.status ? (
              <p className="border-t border-rc-border pt-2 text-rc-fg-muted">
                Status: {trace.status}
              </p>
            ) : null}
          </div>
        </details>
      ) : (
        <p className="text-sm text-rc-fg-muted">
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
