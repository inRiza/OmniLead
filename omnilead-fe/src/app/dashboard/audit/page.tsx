import { auditLog } from "@/lib/mock";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { TimeAgo } from "@/components/TimeAgo";

export default function AuditPage() {
  return (
    <>
      <Topbar title="Audit" subtitle="Log keputusan agen dan Anda" />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl p-4 md:p-6">
          <div className="divide-y divide-rc-border">
            {auditLog.map((e) => (
              <article key={e.id} className="py-4 first:pt-0 last:pb-0">
                <div className="flex items-baseline justify-between gap-3">
                  <h3 className="text-sm font-semibold text-rc-fg">{e.event}</h3>
                  <time className="shrink-0 text-xs tabular-nums text-rc-fg-subtle">
                    <TimeAgo iso={e.ts} />
                  </time>
                </div>
                <p className="mt-1 text-sm text-rc-fg-muted">{e.detail}</p>
              </article>
            ))}
          </div>
        </div>
      </ContentInset>
    </>
  );
}
