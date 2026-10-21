"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { adaptLeadDetail } from "@/lib/adapt";
import { api } from "@/lib/api";
import type { LeadDetail } from "@/lib/types";
import { channelLabel, cn } from "@/lib/ui";
import { Button } from "@/components/action/button";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { ChannelIcon, ScoreBadge } from "@/components/primitives";
import { TimeAgo } from "@/components/TimeAgo";

const stageLabel: Record<string, string> = {
  baru: "Baru",
  tertarik: "Tertarik",
  penawaran: "Penawaran",
  deal: "Deal",
  batal: "Batal",
};

export default function LeadProfilePage() {
  return (
    <Suspense fallback={<p className="p-6 text-sm text-rc-fg-muted">Memuat profil…</p>}>
      <LeadProfile />
    </Suspense>
  );
}

function LeadProfile() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<LeadDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setDetail(adaptLeadDetail(await api.leadDetail(id)));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal memuat profil");
    }
  }, [id]);

  useEffect(() => {
    const first = setTimeout(() => void load(), 0);
    const t = setInterval(() => void load(), 5000);
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [load]);

  const lead = detail?.lead;
  const [splitting, setSplitting] = useState<string | null>(null);

  async function split(actionId: string) {
    setSplitting(actionId);
    try {
      await api.undoMerge(actionId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal memisahkan profil");
    } finally {
      setSplitting(null);
    }
  }

  return (
    <>
      <Topbar
        title={lead ? lead.name : "Profil lead"}
        subtitle={lead?.company ?? "Riwayat lintas kanal"}
      />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="flex w-full mx-auto w-full max-w-6xl flex-col gap-4 pt-1 pb-10">
          <Link
            href="/dashboard/leads"
            className="text-sm font-medium text-rc-fg-muted transition-colors hover:text-rc-fg"
          >
            ← Semua lead
          </Link>

          {error ? (
            <p role="alert" className="text-sm font-medium text-rc-danger">
              {error}
            </p>
          ) : null}

          {lead ? (
            <>
              <section className="rounded-lg border border-rc-border bg-rc-surface p-6">
                <div className="flex flex-wrap items-center gap-3">
                  <ScoreBadge score={lead.score} />
                  <span className="text-lg font-semibold tabular-nums text-rc-fg">
                    {lead.scoreValue}
                  </span>
                  <span className="rounded-md bg-rc-surface-hover/70 px-2 py-0.5 text-sm font-medium text-rc-fg-muted">
                    Tahap {stageLabel[lead.stage]}
                  </span>
                  <div className="ml-auto flex flex-wrap gap-1">
                    {lead.channels.map((c) => (
                      <span
                        key={c}
                        className="inline-flex items-center gap-1 rounded-md bg-rc-surface-hover/70 px-1.5 py-0.5 text-sm text-rc-fg-muted"
                      >
                        <ChannelIcon channel={c} />
                        {channelLabel[c]}
                      </span>
                    ))}
                  </div>
                </div>
                {lead.summary ? (
                  <p className="mt-3 text-sm leading-relaxed text-rc-fg">{lead.summary}</p>
                ) : null}
                {lead.scoreReason ? (
                  <p className="mt-2 text-sm text-rc-fg-muted">
                    <span className="font-medium text-rc-fg">Alasan skor: </span>
                    {lead.scoreReason}
                  </p>
                ) : null}
                <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm text-rc-fg-muted sm:grid-cols-3">
                  <div>
                    <dt className="font-medium text-rc-fg-subtle">Nomor HP</dt>
                    <dd>{lead.phones.join(", ") || "-"}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-rc-fg-subtle">Email</dt>
                    <dd className="break-all">{lead.emails.join(", ") || "-"}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-rc-fg-subtle">Handle</dt>
                    <dd className="break-all">
                      {lead.handles.map((h) => h.replace(":", " · ")).join(", ") || "-"}
                    </dd>
                  </div>
                </dl>
              </section>

              {detail.undoableMerges.length > 0 ? (
                <section className="rounded-lg border border-rc-border bg-rc-surface p-6">
                  <h2 className="text-sm font-semibold text-rc-fg">Profil yang pernah digabung</h2>
                  <p className="mt-1 text-sm text-rc-fg-muted">
                    Salah gabung? Pisahkan kembali; riwayat dan identitas dikembalikan ke profil asalnya.
                  </p>
                  <ul className="mt-3 space-y-3">
                    {detail.undoableMerges.map((m) => (
                      <li key={m.actionId} className="flex flex-wrap items-center gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-rc-fg">{m.sourceName}</p>
                          <p className="text-sm text-rc-fg-muted">{m.evidence.join("; ")}</p>
                        </div>
                        <Button
                          purpose="action"
                          style="secondary"
                          disabled={splitting === m.actionId}
                          onClick={() => split(m.actionId)}
                        >
                          {splitting === m.actionId ? "Memisahkan…" : "Pisahkan"}
                        </Button>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {detail.mergeEvidence.length > 0 ? (
                <section className="rounded-lg border border-rc-border bg-rc-surface p-6">
                  <h2 className="text-sm font-semibold text-rc-fg">Bukti penggabungan identitas</h2>
                  <ul className="mt-2 space-y-1.5 text-sm text-rc-fg-muted">
                    {detail.mergeEvidence.map((e) => (
                      <li key={e.id}>
                        {e.detail}{" "}
                        <span className="text-rc-fg-subtle">
                          (<TimeAgo iso={e.ts} />)
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              <section className="rounded-lg border border-rc-border bg-rc-surface p-6">
                <h2 className="text-sm font-semibold text-rc-fg">Riwayat lintas kanal</h2>
                {detail.timeline.length === 0 ? (
                  <p className="mt-2 text-sm text-rc-fg-muted">Belum ada riwayat.</p>
                ) : (
                  <ol className="mt-3 space-y-3">
                    {detail.timeline.map((t, i) => (
                      <li key={i} className="flex gap-3">
                        <ChannelIcon channel={t.channel} />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 text-sm">
                            <span
                              className={cn(
                                "rounded-md px-1.5 py-0.5 font-medium",
                                t.direction === "in"
                                  ? "bg-rc-surface-hover text-rc-fg"
                                  : "bg-rc-accent-soft text-rc-accent",
                              )}
                            >
                              {t.direction === "in" ? "Masuk" : "Terkirim"}
                            </span>
                            <span className="text-rc-fg-muted">{channelLabel[t.channel]}</span>
                            {t.ts ? (
                              <span className="ml-auto text-rc-fg-subtle">
                                <TimeAgo iso={t.ts} />
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-1 whitespace-pre-line text-sm leading-relaxed text-rc-fg">
                            {t.text}
                          </p>
                        </div>
                      </li>
                    ))}
                  </ol>
                )}
              </section>
            </>
          ) : !error ? (
            <p className="text-sm text-rc-fg-muted">Memuat profil…</p>
          ) : null}
        </div>
      </ContentInset>
    </>
  );
}
