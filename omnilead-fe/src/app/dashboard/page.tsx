"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { ArrowRight } from "lucide-react";
import type { Channel } from "@/lib/types";
import { actorKind, isOpenHotLead, needsReply, outcomeMeta } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { Card, SectionTitle } from "@/components/dashboard/Card";
import { Badge, ChannelIcon, ScoreBadge } from "@/components/primitives";
import { Select } from "@/components/ui/select";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import { TimeAgo } from "@/components/TimeAgo";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { useAccount } from "@/components/dashboard/AccountProvider";

type Period = "today" | "7d" | "30d";

const PERIODS: { value: Period; label: string }[] = [
  { value: "today", label: "Hari ini" },
  { value: "7d", label: "7 hari terakhir" },
  { value: "30d", label: "30 hari terakhir" },
];

const CHANNELS: Channel[] = ["whatsapp", "instagram", "facebook", "email"];

const volumeConfig: ChartConfig = {
  whatsapp: { label: "WhatsApp", color: "#0144f5", icon: <ChannelIcon channel="whatsapp" /> },
  instagram: { label: "Instagram", color: "#3d6dff", icon: <ChannelIcon channel="instagram" /> },
  facebook: { label: "Facebook", color: "#7d9dff", icon: <ChannelIcon channel="facebook" /> },
  email: { label: "Email", color: "#bccdff", icon: <ChannelIcon channel="email" /> },
};

const trendConfig: ChartConfig = {
  leads: { label: "Lead baru", color: "#7d9dff" },
  closing: { label: "Closing", color: "#0144f5" },
};

const DAY = 86_400_000;

type Bucket = { key: string; label: string; title: string; start: number; end: number };

function buckets(period: Period, now: number): Bucket[] {
  const today = new Date(now);
  today.setHours(0, 0, 0, 0);
  if (period === "today") {
    return Array.from({ length: 12 }, (_, i) => {
      const start = today.getTime() + i * 2 * 3_600_000;
      const h = String(i * 2).padStart(2, "0");
      return { key: h, label: `${h}.00`, title: `${h}.00–${String(i * 2 + 2).padStart(2, "0")}.00`, start, end: start + 2 * 3_600_000 };
    });
  }
  const n = period === "7d" ? 7 : 30;
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(today.getTime() - (n - 1 - i) * DAY);
    const label =
      period === "7d"
        ? d.toLocaleDateString("id-ID", { weekday: "short" })
        : d.toLocaleDateString("id-ID", { day: "numeric", month: "short" });
    const title = d.toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long" });
    return { key: d.toISOString(), label, title, start: d.getTime(), end: d.getTime() + DAY };
  });
}

function within(iso: string | undefined, b: { start: number; end: number }) {
  if (!iso) return false;
  const t = new Date(iso).getTime();
  return t >= b.start && t < b.end;
}

export default function HomePage() {
  const { session } = useAccount();
  const { activities, leads, audit, loaded, error, refresh } = useDashboard();
  const [period, setPeriod] = useState<Period>("7d");
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    const t = setTimeout(() => setNow(Date.now()), 0);
    return () => clearTimeout(t);
  }, []);

  const range = useMemo(() => {
    if (now === null) return null;
    const b = buckets(period, now);
    return { list: b, start: b[0].start, end: b[b.length - 1].end };
  }, [period, now]);

  const volume = useMemo(
    () =>
      (range?.list ?? []).map((b) => {
        const row: Record<string, string | number> = { label: b.label, title: b.title };
        for (const c of CHANNELS) row[c] = activities.filter((a) => a.channel === c && within(a.receivedAt, b)).length;
        return row;
      }),
    [range, activities],
  );

  const trend = useMemo(
    () =>
      (range?.list ?? []).map((b) => ({
        label: b.label,
        title: b.title,
        leads: leads.filter((l) => within(l.createdAt, b)).length,
        closing: leads.filter((l) => l.stage === "deal" && within(l.updatedAt, b)).length,
      })),
    [range, leads],
  );

  // Same predicate as inbox `?status=Perlu dibalas` — KPI count and list share this queue.
  const replyQueue = useMemo(
    () => [...activities].filter(needsReply).sort((a, b) => b.scoreValue - a.scoreValue),
    [activities],
  );

  // Period-scoped (charts): messages + closing. Open queues: unreplied + hot leads.
  const messages = volume.reduce((s, row) => s + CHANNELS.reduce((n, c) => n + Number(row[c] || 0), 0), 0);
  const needReply = replyQueue.length;
  const toReply = replyQueue.slice(0, 5);
  const hot = leads.filter(isOpenHotLead).length;
  const newLeads = trend.reduce((s, t) => s + t.leads, 0);
  const closings = trend.reduce((s, t) => s + t.closing, 0);
  const rate = newLeads ? Math.round((closings / newLeads) * 100) : 0;
  const pipeline = leads.filter((l) => l.stage === "tertarik" || l.stage === "penawaran").length;

  const stats = [
    { label: "Pesan masuk", value: messages, href: "/dashboard/inbox" },
    { label: "Perlu dibalas", value: needReply, href: "/dashboard/inbox?status=Perlu%20dibalas" },
    { label: "Lead prioritas tinggi", value: hot, href: "/dashboard/leads?score=hot" },
    { label: "Closing", value: closings, href: "/dashboard/leads?stage=deal" },
  ];

  const agentLog = audit.filter((e) => actorKind(e.actor) !== "Pengguna").slice(0, 6);
  const periodLabel = PERIODS.find((p) => p.value === period)?.label.toLowerCase();

  return (
    <>
      <Topbar title="Beranda" />

      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-5 p-5 pb-10 md:p-7 md:pb-12">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold text-rc-fg">
                Halo{session.user?.name ? `, ${session.user.name.split(" ")[0]}` : ""}
              </h2>
              <p className="mt-1 text-sm text-rc-fg-muted">
                {error ? "Data belum bisa dimuat dari backend." : `Ringkasan ${periodLabel} dari semua kanal.`}
              </p>
            </div>
            <Select label="Periode" className="w-48" align="right" value={period} onChange={setPeriod} options={PERIODS} />
          </div>

          {error && (
            <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">
              Data belum bisa dimuat. {error}
              <button type="button" onClick={() => void refresh()} className="cursor-pointer font-medium underline">
                Coba lagi
              </button>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {stats.map((s) => (
              <Link
                key={s.label}
                href={s.href}
                className="group rounded-xl border border-rc-border bg-rc-surface p-5 transition-colors hover:border-rc-accent/40"
              >
                <span className="flex items-center justify-between text-sm font-medium text-rc-fg-muted">
                  {s.label}
                  <ArrowRight aria-hidden className="h-4 w-4 -translate-x-1 text-rc-accent opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
                </span>
                <span className="mt-3 block text-3xl font-semibold tracking-tight text-rc-fg tabular-nums">
                  {loaded ? s.value : "–"}
                </span>
              </Link>
            ))}
          </div>

          <Card>
            <SectionTitle action={<span className="text-sm text-rc-fg-muted">{messages} pesan</span>}>Volume pesan per kanal</SectionTitle>
            <ChartContainer config={volumeConfig} className="aspect-auto h-72 w-full">
              <BarChart data={volume} margin={{ left: -16, right: 4, top: 8 }}>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={10} minTickGap={16} />
                <YAxis tickLine={false} axisLine={false} allowDecimals={false} width={40} />
                <ChartTooltip cursor content={<ChartTooltipContent labelKey="title" />} />
                <ChartLegend content={<ChartLegendContent />} />
                {CHANNELS.map((c, i) => (
                  <Bar
                    key={c}
                    dataKey={c}
                    stackId="v"
                    fill={`var(--color-${c})`}
                    radius={i === CHANNELS.length - 1 ? [4, 4, 0, 0] : 0}
                    maxBarSize={44}
                  />
                ))}
              </BarChart>
            </ChartContainer>
          </Card>

          <Card>
            <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="text-base font-semibold text-rc-fg">Potensi closing</h3>
                <p className="text-sm text-rc-fg-muted">Lead baru dibanding lead yang berhasil closing.</p>
              </div>
              <dl className="flex gap-6 text-right">
                {[
                  ["Lead baru", newLeads],
                  ["Closing", closings],
                  ["Konversi", `${rate}%`],
                  ["Dalam proses", pipeline],
                ].map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-xs text-rc-fg-muted">{k}</dt>
                    <dd className="text-lg font-semibold text-rc-fg tabular-nums">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <ChartContainer config={trendConfig} className="aspect-auto h-64 w-full">
              <AreaChart data={trend} margin={{ left: -16, right: 4, top: 8 }}>
                <defs>
                  <linearGradient id="fill-leads" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-leads)" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="var(--color-leads)" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="fill-closing" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--color-closing)" stopOpacity={0.3} />
                    <stop offset="100%" stopColor="var(--color-closing)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={10} minTickGap={16} />
                <YAxis tickLine={false} axisLine={false} allowDecimals={false} width={40} />
                <ChartTooltip content={<ChartTooltipContent labelKey="title" hideTotal />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Area type="monotone" dataKey="leads" stroke="var(--color-leads)" strokeWidth={2} fill="url(#fill-leads)" dot={false} />
                <Area type="monotone" dataKey="closing" stroke="var(--color-closing)" strokeWidth={2.5} fill="url(#fill-closing)" dot={false} />
              </AreaChart>
            </ChartContainer>
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card pad={false}>
              <div className="px-5 pt-5">
                <SectionTitle
                  action={
                    <span className="flex items-center gap-3">
                      <span className="text-sm text-rc-fg-muted tabular-nums">{needReply}</span>
                      <Link href="/dashboard/inbox?status=Perlu%20dibalas" className="inline-flex items-center gap-1 text-sm font-medium text-rc-accent hover:underline">
                        Buka workspace <ArrowRight aria-hidden className="h-3.5 w-3.5" />
                      </Link>
                    </span>
                  }
                >
                  Perlu dibalas
                </SectionTitle>
              </div>
              <div className="px-2 pb-2">
                {toReply.length === 0 ? (
                  <p className="px-3 pb-4 text-sm text-rc-fg-muted">Belum ada percakapan yang membutuhkan tindak lanjut.</p>
                ) : (
                  toReply.map((a) => (
                    <Link
                      key={a.id}
                      href={`/dashboard/inbox?id=${a.id}`}
                      className="flex items-start gap-3 rounded-lg px-3 py-3 transition-colors hover:bg-rc-surface-hover"
                    >
                      <ChannelIcon channel={a.channel} size="md" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-sm font-semibold text-rc-fg">{a.authorName}</span>
                          <ScoreBadge score={a.score} />
                          <span className="ml-auto shrink-0 text-xs text-rc-fg-subtle">
                            <TimeAgo iso={a.receivedAt} />
                          </span>
                        </div>
                        <p className="mt-0.5 line-clamp-1 text-sm text-rc-fg-muted">{a.text}</p>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </Card>

            <Card pad={false}>
              <div className="px-5 pt-5">
                <SectionTitle
                  action={
                    <Link href="/dashboard/audit" className="inline-flex items-center gap-1 text-sm font-medium text-rc-accent hover:underline">
                      Semua log <ArrowRight aria-hidden className="h-3.5 w-3.5" />
                    </Link>
                  }
                >
                  Hasil kerja agen
                </SectionTitle>
              </div>
              <div className="px-2 pb-2">
                {agentLog.length === 0 ? (
                  <p className="px-3 pb-4 text-sm text-rc-fg-muted">Belum ada aktivitas agen.</p>
                ) : (
                  agentLog.map((e) => {
                    const o = outcomeMeta[e.outcome];
                    return (
                      <Link
                        key={e.id}
                        href={e.leadId ? `/dashboard/leads/${e.leadId}` : "/dashboard/audit"}
                        className="flex items-start gap-3 rounded-lg px-3 py-3 transition-colors hover:bg-rc-surface-hover"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="truncate text-sm font-semibold text-rc-fg">{e.event}</span>
                            <Badge tone={o.tone}>{o.label}</Badge>
                          </div>
                          <p className="mt-0.5 line-clamp-1 text-sm text-rc-fg-muted">{e.detail}</p>
                        </div>
                        <span className="shrink-0 text-xs text-rc-fg-subtle">
                          <TimeAgo iso={e.ts} />
                        </span>
                      </Link>
                    );
                  })
                )}
              </div>
            </Card>
          </div>
        </div>
      </ContentInset>
    </>
  );
}
