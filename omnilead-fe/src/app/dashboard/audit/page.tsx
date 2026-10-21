"use client";

import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { TimeAgo } from "@/components/TimeAgo";
import { useDashboard } from "@/components/dashboard/DashboardContext";

export default function AuditPage() {
  const { audit: auditLog, loaded } = useDashboard();
  return (
    <>
      <Topbar title="Audit" subtitle="Log keputusan agen dan Anda" />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl p-4 md:p-6">
          {loaded && auditLog.length === 0 ? (
            <p className="text-sm text-rc-fg-muted">Belum ada catatan.</p>
          ) : null}
          <div className="divide-y divide-rc-border">
            {auditLog.map((e) => (
              <article key={e.id} className="py-4 first:pt-0 last:pb-0">
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="text-sm font-semibold text-rc-fg">{e.event}</h3>
                  <time className="shrink-0 text-sm tabular-nums text-rc-fg-subtle">
                    <TimeAgo iso={e.ts} />
                  </time>
                </div>
                <p className="mt-1 text-sm text-rc-fg-muted">{e.detail}</p>
                <p className="mt-0.5 text-sm text-rc-fg-subtle">
                  oleh {e.actor}
                  {e.channel ? ` · ${e.channel}` : ""}
                </p>
              </article>
            ))}
          </div>
        </div>
      </ContentInset>
    </>
  );
}
