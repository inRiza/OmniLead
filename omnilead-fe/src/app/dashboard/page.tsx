"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { channelLabel } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { Card, SectionTitle } from "@/components/dashboard/Card";
import { BarChart, type Bar } from "@/components/dashboard/BarChart";
import { ChannelIcon, Dot, ScoreBadge } from "@/components/primitives";
import { ArrowIcon } from "@/components/dashboard/icons";
import { TimeAgo } from "@/components/TimeAgo";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { useAccount } from "@/components/dashboard/AccountProvider";

const DAYS = ["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"];

/** Jumlah pesan masuk per hari untuk 7 hari terakhir (hari ini paling kanan). */
function weeklyVolume(receivedAt: string[], now: number): Bar[] {
  const today = new Date(now);
  today.setHours(0, 0, 0, 0);
  const bars: Bar[] = [];
  for (let back = 6; back >= 0; back--) {
    const day = new Date(today);
    day.setDate(today.getDate() - back);
    const next = new Date(day);
    next.setDate(day.getDate() + 1);
    const value = receivedAt.filter((iso) => {
      const t = new Date(iso).getTime();
      return t >= day.getTime() && t < next.getTime();
    }).length;
    bars.push({ label: DAYS[day.getDay()], value });
  }
  return bars;
}

export default function HomePage() {
  const { session } = useAccount();
  const {
    activities,
    channels: channelStatuses,
    audit,
    summary,
    pendingCount: pending,
    error,
  } = useDashboard();
  const needReply = activities.filter((a) => a.status !== "selesai").length;
  const hot = activities.filter((a) => a.score === "hot").length;
  // Waktu dibaca setelah mount (bukan saat prerender) agar hasilnya tidak beku.
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    const t = setTimeout(() => setNow(Date.now()), 0);
    return () => clearTimeout(t);
  }, []);
  const weekly = useMemo<Bar[]>(
    () =>
      now === null
        ? DAYS.map((label) => ({ label, value: 0 }))
        : weeklyVolume(activities.map((a) => a.receivedAt), now),
    [activities, now],
  );

  const top = [...activities]
    .filter((a) => a.score !== "cold" && a.status !== "selesai")
    .sort((a, b) => b.scoreValue - a.scoreValue)
    .slice(0, 3);

  const stats = [
    { label: "Pesan masuk", value: activities.length, hint: "tercatat" },
    { label: "Perlu balasan", value: needReply, hint: "aktif" },
    { label: "Menunggu Anda", value: pending, hint: "di workspace" },
    { label: "Lead panas", value: hot, hint: "prioritas" },
  ];

  return (
    <>
      <Topbar
        title="Beranda"
        subtitle="Ringkas, fokus ke pesanan dan follow-up"
      />

      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-6 p-5 pb-10 md:p-7 md:pb-12">
          <div>
            <h2 className="text-xl font-medium text-rc-fg-muted">
              Halo{session.user?.name ? <>, <span className="font-semibold text-rc-fg [overflow-wrap:anywhere]">{session.user.name}</span></> : "!"}
            </h2>
            <p className="mt-1 text-sm text-rc-fg-muted">
              {error
                ? "Data belum bisa dimuat dari backend."
                : `Ada ${pending} aksi yang sudah disiapkan agen, tinggal Anda putuskan.`}
            </p>
          </div>

          <Card>
            <SectionTitle>Perlu ditangani hari ini</SectionTitle>
            {summary.length === 0 ? (
              <p className="text-sm text-rc-fg-muted">
                Tidak ada yang mendesak. Semua aman.
              </p>
            ) : (
              <ol className="divide-y divide-rc-border">
                {summary.map((s, i) => (
                  <li key={i} className="flex items-start gap-3 py-2.5 first:pt-0 last:pb-0">
                    <span className="mt-0.5 w-5 shrink-0 text-sm font-semibold tabular-nums text-rc-fg-subtle">
                      {i + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      {s.leadId ? (
                        <Link
                          href={`/dashboard/leads/${s.leadId}`}
                          className="text-sm font-semibold text-rc-fg hover:underline"
                        >
                          {s.title}
                        </Link>
                      ) : (
                        <span className="text-sm font-semibold text-rc-fg">{s.title}</span>
                      )}
                      <p className="line-clamp-2 text-sm text-rc-fg-muted">{s.detail}</p>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </Card>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {stats.map((s) => (
              <Card key={s.label}>
                <div className="text-sm font-medium text-rc-fg-muted">
                  {s.label}
                </div>
                <div className="mt-2 flex items-end justify-between">
                  <span className="text-2xl font-semibold tabular-nums leading-none tracking-tight text-rc-fg">
                    {s.value}
                  </span>
                  <span className="rounded-md bg-rc-surface-hover/70 px-2 py-0.5 text-sm font-medium text-rc-fg-muted">
                    {s.hint}
                  </span>
                </div>
              </Card>
            ))}
          </div>

          <div className="grid gap-3 lg:grid-cols-5">
            <Card className="lg:col-span-3">
              <SectionTitle
                action={
                  <span className="text-sm text-rc-fg-muted">7 hari</span>
                }
              >
                Volume pesan
              </SectionTitle>
              <BarChart data={weekly} unit=" pesan" />
            </Card>

            <Card className="lg:col-span-2">
              <SectionTitle>Kanal</SectionTitle>
              <div className="divide-y divide-rc-border">
                {channelStatuses.map((c) => (
                  <div
                    key={c.channel}
                    className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0"
                  >
                    <ChannelIcon channel={c.channel} size="md" />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-semibold text-rc-fg">
                        {channelLabel[c.channel]}
                      </div>
                      <div className="truncate text-sm text-rc-fg-muted">
                        {c.detail}
                      </div>
                    </div>
                    <Dot ok={c.connected} />
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="grid gap-3 lg:grid-cols-5">
            <Card className="lg:col-span-3" pad={false}>
              <div className="px-4 pt-4">
                <SectionTitle
                  action={
                    <Link
                      href="/dashboard/inbox"
                      className="inline-flex items-center gap-1 text-sm font-medium text-rc-fg-muted transition-colors hover:text-rc-fg"
                    >
                      Buka workspace
                      <ArrowIcon className="h-3.5 w-3.5" width={14} height={14} />
                    </Link>
                  }
                >
                  Yang perlu dibalas
                </SectionTitle>
              </div>
              <div className="divide-y divide-rc-border px-2 pb-2">
                {top.length === 0 ? (
                  <p className="px-2 py-3 text-sm text-rc-fg-muted">
                    Belum ada aktivitas. Hubungkan kanal komunikasi atau media
                    sosial untuk mulai.
                  </p>
                ) : null}
                {top.map((a) => (
                  <Link
                    key={a.id}
                    href="/dashboard/inbox"
                    className="flex items-start gap-3 rounded-md px-2 py-3 transition-colors hover:bg-rc-surface-hover/50"
                  >
                    <ChannelIcon channel={a.channel} size="md" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-semibold text-rc-fg">
                          {a.authorName}
                        </span>
                        <ScoreBadge score={a.score} />
                        <span className="ml-auto shrink-0 text-sm text-rc-fg-subtle">
                          <TimeAgo iso={a.receivedAt} />
                        </span>
                      </div>
                      <p className="mt-1 line-clamp-1 text-sm text-rc-fg-muted">
                        {a.text}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </Card>

            <Card className="lg:col-span-2" pad={false}>
              <div className="px-4 pt-4">
                <SectionTitle
                  action={
                    <Link
                      href="/dashboard/audit"
                      className="inline-flex items-center gap-1 text-sm font-medium text-rc-fg-muted transition-colors hover:text-rc-fg"
                    >
                      Semua log
                      <ArrowIcon className="h-3.5 w-3.5" width={14} height={14} />
                    </Link>
                  }
                >
                  Agen tadi
                </SectionTitle>
              </div>
              <div className="divide-y divide-rc-border px-3 pb-3">
                {audit.slice(0, 5).map((e) => (
                  <div key={e.id} className="px-1 py-2.5">
                    <span className="text-sm font-medium text-rc-fg">
                      {e.event}
                    </span>
                    <p className="line-clamp-2 text-sm text-rc-fg-muted">
                      {e.detail}
                    </p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      </ContentInset>
    </>
  );
}
