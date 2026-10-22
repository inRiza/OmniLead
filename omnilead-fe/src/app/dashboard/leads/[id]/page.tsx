"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { adaptLeadDetail } from "@/lib/adapt";
import { api } from "@/lib/api";
import type { Channel, LeadDetail } from "@/lib/types";
import { cap, channelLabel, cn, stageLabel, stageTone } from "@/lib/ui";
import { ArrowLeft, AtSign, CheckCheck, CircleCheck, Mail, Merge, Phone, Split } from "lucide-react";
import { LogoMark } from "@/components/brand/Logo";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/action/button";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { Badge, ChannelIcon } from "@/components/primitives";
import { LeadInsights } from "@/components/dashboard/LeadInsights";

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
  const [filter, setFilter] = useState<Channel | "all">("all");

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

  const channels = lead ? [...new Set(detail.timeline.map((t) => t.channel))] : [];
  const messages = (detail?.timeline ?? [])
    .filter((t) => filter === "all" || t.channel === filter)
    .slice()
    .sort((x, y) => (x.ts ?? "").localeCompare(y.ts ?? ""));
  const days: { day: string; items: typeof messages }[] = [];
  for (const m of messages) {
    const day = m.ts ? new Date(m.ts).toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long" }) : "Tanpa tanggal";
    const last = days[days.length - 1];
    if (last?.day === day) last.items.push(m);
    else days.push({ day, items: [m] });
  }

  return (
    <>
      <Topbar title={lead ? lead.name : "Profil lead"} subtitle={lead?.company ?? "Riwayat lintas kanal"} />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 p-5 pb-10 md:p-6">
          <Link href="/dashboard/leads" className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-rc-fg-muted transition-colors hover:text-rc-fg">
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Semua lead
          </Link>

          {error ? (
            <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </p>
          ) : null}

          {lead ? (
            <>
              <aside className="flex flex-col gap-4">
                <section className="rounded-xl border border-rc-border bg-rc-surface p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-rc-accent text-base font-semibold text-white">
                        {lead.name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase()}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-base font-semibold text-rc-fg">{lead.name}</p>
                        <p className="truncate text-sm text-rc-fg-muted">{lead.company || "Perorangan"}</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex items-center rounded-md bg-rc-surface-hover px-2 py-0.5 text-sm font-semibold text-rc-fg tabular-nums">
                        {lead.scoreValue}
                      </span>
                      <Badge tone={stageTone[lead.stage]} dot>
                        {stageLabel[lead.stage]}
                      </Badge>
                    </div>
                  </div>

                  <dl className="mt-5 flex flex-col gap-3 border-t border-rc-border pt-5 text-sm">
                    {[
                      { icon: Phone, label: "Nomor HP", value: lead.phones.join(", ") },
                      { icon: Mail, label: "Email", value: lead.emails.join(", ") },
                      { icon: AtSign, label: "Akun sosial", value: lead.handles.map((h) => `${cap(h.split(":")[0])} @${h.split(":").slice(1).join(":").replace(/^@/, "")}`).join(", ") },
                    ].map(({ icon: Icon, label, value }) => (
                      <div key={label} className="flex gap-3">
                        <Icon className="mt-0.5 h-4 w-4 shrink-0 text-rc-fg-subtle" aria-hidden />
                        <div className="min-w-0">
                          <dt className="text-xs text-rc-fg-muted">{label}</dt>
                          <dd className={value ? "break-all text-rc-fg" : "text-rc-fg-subtle"}>{value || "Belum diketahui"}</dd>
                        </div>
                      </div>
                    ))}
                  </dl>

                  <div className="mt-5 flex flex-wrap gap-1.5 border-t border-rc-border pt-5">
                    {lead.channels.map((c) => (
                      <Badge key={c}>Kanal: {channelLabel[c]}</Badge>
                    ))}
                  </div>
                </section>

                <LeadInsights
                  summary={lead.summary}
                  score={lead.score}
                  scoreValue={lead.scoreValue}
                  reasons={lead.scoreReasons}
                  analysis={lead.scoreAnalysis}
                  needs={lead.needs}
                  estimatedValue={lead.estimatedValue}
                  nextStep={lead.nextStep}
                  scoredAt={lead.scoredAt}
                />

                {detail.undoableMerges.length > 0 || detail.mergeEvidence.length > 0 ? (
                  <section className="rounded-xl border border-rc-border bg-rc-surface p-5">
                    <p className="flex items-center gap-1.5 text-sm font-semibold text-rc-fg">
                      <Merge className="h-4 w-4 text-rc-fg-muted" aria-hidden />
                      Profil yang digabung
                    </p>
                    <p className="mt-1 text-xs text-rc-fg-muted">Salah gabung? Pisahkan kembali, riwayatnya ikut dikembalikan.</p>
                    <ul className="mt-3 flex flex-col gap-3">
                      {detail.undoableMerges.map((m) => (
                        <li key={m.actionId} className="rounded-lg bg-rc-bg p-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="truncate text-sm font-medium text-rc-fg">{m.sourceName}</p>
                            <Button purpose="action" className="shrink-0 gap-1.5" disabled={splitting === m.actionId} onClick={() => split(m.actionId)}>
                              <Split className="h-4 w-4" aria-hidden />
                              {splitting === m.actionId ? "Memisahkan…" : "Pisahkan"}
                            </Button>
                          </div>
                          {m.evidence.length ? (
                            <ul className="mt-2 flex flex-col gap-1">
                              {m.evidence.map((ev) => (
                                <li key={ev} className="flex gap-1.5 text-xs text-rc-fg-muted">
                                  <CircleCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden />
                                  {ev}
                                </li>
                              ))}
                            </ul>
                          ) : null}
                        </li>
                      ))}
                      {detail.undoableMerges.length === 0 &&
                        detail.mergeEvidence.map((e) => (
                          <li key={e.id} className="flex gap-1.5 text-xs text-rc-fg-muted">
                            <CircleCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" aria-hidden />
                            {e.detail}
                          </li>
                        ))}
                    </ul>
                  </section>
                ) : null}
              </aside>

              <section className="flex min-h-[32rem] w-full flex-col overflow-hidden rounded-xl border border-rc-border bg-rc-surface">
                <header className="flex flex-wrap items-center justify-between gap-3 border-b border-rc-border px-5 py-3.5">
                  <div>
                    <h2 className="text-sm font-semibold text-rc-fg">Riwayat percakapan</h2>
                    <p className="text-xs text-rc-fg-muted">{messages.length} pesan lintas kanal</p>
                  </div>
                  {channels.length > 1 ? (
                    <Select
                      label="Filter kanal"
                      size="sm"
                      align="right"
                      className="w-44"
                      value={filter}
                      onChange={setFilter}
                      options={[
                        { value: "all", label: "Semua kanal" },
                        ...channels.map((c) => ({ value: c, label: channelLabel[c], icon: <ChannelIcon channel={c} /> })),
                      ]}
                    />
                  ) : null}
                </header>
                <div className="flex-1 bg-rc-bg px-4 py-5 sm:px-6">
                  {messages.length === 0 ? (
                    <p className="py-16 text-center text-sm text-rc-fg-muted">Belum ada riwayat percakapan.</p>
                  ) : (
                    days.map((g) => (
                      <div key={g.day} className="mb-6 last:mb-0">
                        <p className="mx-auto mb-4 w-fit rounded-md bg-rc-surface px-3 py-1 text-xs font-medium text-rc-fg-muted">{g.day}</p>
                        <ol className="flex flex-col gap-3">
                          {g.items.map((t, i) => {
                            const out = t.direction === "out";
                            return (
                              <li key={i} className={cn("flex items-end gap-2", out ? "flex-row-reverse" : "")}>
                                {out ? <LogoMark size={28} /> : <ChannelIcon channel={t.channel} size="md" />}
                                <div className={cn("max-w-[80%] rounded-xl px-4 py-2.5", out ? "rounded-br-sm bg-rc-accent text-white" : "rounded-bl-sm bg-rc-surface text-rc-fg")}>
                                  <p className="text-sm leading-relaxed whitespace-pre-line">{t.text}</p>
                                  <p className={cn("mt-1.5 flex items-center gap-1.5 text-[11px]", out ? "justify-end text-white/75" : "text-rc-fg-subtle")}>
                                    {channelLabel[t.channel]}
                                    {t.ts ? (
                                      <span>
                                        {new Date(t.ts).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" })}
                                      </span>
                                    ) : null}
                                    {out ? <CheckCheck className="h-3.5 w-3.5" aria-hidden /> : null}
                                  </p>
                                </div>
                              </li>
                            );
                          })}
                        </ol>
                      </div>
                    ))
                  )}
                </div>
              </section>
            </>
          ) : !error ? (
            <>
              <div className="h-48 animate-pulse rounded-xl bg-rc-surface-hover" />
              <div className="h-[32rem] animate-pulse rounded-xl bg-rc-surface-hover" />
            </>
          ) : null}
        </div>
      </ContentInset>
    </>
  );
}
