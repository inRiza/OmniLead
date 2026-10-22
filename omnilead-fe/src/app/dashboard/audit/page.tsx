"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Bot, Cog, Search, UserRound } from "lucide-react";
import type { AuditEntry, Channel } from "@/lib/types";
import { actorKind, cap, channelLabel, outcomeMeta, toneClass, type Tone } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { Badge, ChannelIcon } from "@/components/primitives";
import { Select } from "@/components/ui/select";
import { useDashboard } from "@/components/dashboard/DashboardContext";

type Actor = ReturnType<typeof actorKind>;
const ACTOR_TONE: Record<Actor, Tone> = { AI: "blue", Pengguna: "amber", Sistem: "gray" };
const ACTOR_ICON: Record<Actor, typeof Bot> = { AI: Bot, Pengguna: UserRound, Sistem: Cog };
const CHANNELS: Channel[] = ["whatsapp", "instagram", "facebook", "email"];

function clock(iso: string) {
  return new Date(iso).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
}

function dayKey(iso: string) {
  return new Date(iso).toLocaleDateString("id-ID", { weekday: "long", day: "numeric", month: "long" });
}

export default function AuditPage() {
  const { audit, loaded, leadsById, error, refresh } = useDashboard();
  const [query, setQuery] = useState("");
  const [actor, setActor] = useState<Actor | "all">("all");
  const [outcome, setOutcome] = useState<AuditEntry["outcome"] | "all">("all");
  const [channel, setChannel] = useState<Channel | "all">("all");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return audit.filter(
      (e) =>
        (actor === "all" || actorKind(e.actor) === actor) &&
        (outcome === "all" || e.outcome === outcome) &&
        (channel === "all" || e.channel === channel) &&
        (!q || `${e.event} ${e.detail} ${e.actor} ${e.leadId ? (leadsById[e.leadId]?.name ?? "") : ""}`.toLowerCase().includes(q)),
    );
  }, [audit, query, actor, outcome, channel, leadsById]);

  const groups = useMemo(() => {
    const out: { day: string; items: AuditEntry[] }[] = [];
    for (const e of rows) {
      const day = dayKey(e.ts);
      const last = out[out.length - 1];
      if (last?.day === day) last.items.push(e);
      else out.push({ day, items: [e] });
    }
    return out;
  }, [rows]);

  const filtered = actor !== "all" || outcome !== "all" || channel !== "all" || query.trim() !== "";

  return (
    <>
      <Topbar title="Audit" subtitle="Jejak semua tindakan agen, sistem, dan tim Anda" />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-3 p-5 md:p-6">
          <div className="flex flex-wrap items-center gap-2">
            <label className="relative min-w-56 flex-1">
              <span className="sr-only">Cari log</span>
              <Search aria-hidden className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-rc-fg-subtle" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Cari tindakan, detail, atau nama lead"
                className="min-h-10 w-full rounded-md border border-rc-border bg-rc-surface pr-3 pl-9 text-sm text-rc-fg outline-none placeholder:text-rc-fg-subtle focus:border-rc-accent focus:ring-2 focus:ring-rc-accent/15"
              />
            </label>
            <Select
              label="Pelaku"
              className="w-40"
              value={actor}
              onChange={setActor}
              options={[{ value: "all", label: "Semua pelaku" }, ...(["AI", "Pengguna", "Sistem"] as Actor[]).map((a) => ({ value: a, label: a }))]}
            />
            <Select
              label="Hasil"
              className="w-48"
              value={outcome}
              onChange={setOutcome}
              options={[
                { value: "all", label: "Semua hasil" },
                ...(Object.keys(outcomeMeta) as AuditEntry["outcome"][]).map((o) => ({ value: o, label: outcomeMeta[o].label })),
              ]}
            />
            <Select
              label="Kanal"
              className="w-40"
              align="right"
              value={channel}
              onChange={setChannel}
              options={[
                { value: "all", label: "Semua kanal" },
                ...CHANNELS.map((c) => ({ value: c, label: channelLabel[c], icon: <ChannelIcon channel={c} /> })),
              ]}
            />
          </div>

          {error && (
            <div role="alert" className="flex items-center justify-between gap-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              Log belum bisa dimuat.
              <button type="button" onClick={() => void refresh()} className="cursor-pointer font-medium underline">
                Coba lagi
              </button>
            </div>
          )}

          <p className="text-sm text-rc-fg-muted">
            {rows.length} catatan{filtered ? " sesuai filter" : ""}
          </p>

          {loaded && rows.length === 0 ? (
            <p className="rounded-xl border border-dashed border-rc-border-strong bg-rc-surface px-4 py-12 text-center text-sm text-rc-fg-muted">
              {filtered ? "Tidak ada catatan yang cocok dengan filter ini." : "Belum ada aktivitas pada rentang waktu ini."}
            </p>
          ) : (
            groups.map((g) => (
              <section key={g.day} className="overflow-hidden rounded-xl border border-rc-border bg-rc-surface">
                <h2 className="bg-rc-bg px-5 py-2.5 text-xs font-semibold tracking-wide text-rc-fg-muted uppercase">{g.day}</h2>
                <ul className="divide-y divide-rc-border">
                  {g.items.map((e) => {
                    const who = actorKind(e.actor);
                    const o = outcomeMeta[e.outcome];
                    const lead = e.leadId ? leadsById[e.leadId] : undefined;
                    const ActorIcon = ACTOR_ICON[who];
                    return (
                      <li key={e.id} className="flex gap-3.5 px-5 py-4">
                        <span className={`mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${toneClass[ACTOR_TONE[who]]}`}>
                          <ActorIcon className="h-4 w-4" aria-hidden />
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-semibold text-rc-fg">{cap(e.event)}</p>
                            <time dateTime={e.ts} title={new Date(e.ts).toLocaleString("id-ID")} className="shrink-0 text-xs text-rc-fg-subtle tabular-nums">
                              {clock(e.ts)}
                            </time>
                          </div>
                          {e.detail ? <p className="mt-0.5 text-sm text-rc-fg-muted">{cap(e.detail)}</p> : null}
                          <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                            <Badge tone={o.tone} dot>
                              {o.label}
                            </Badge>
                            <Badge>Pelaku: {who === "Pengguna" ? e.actor : who}</Badge>
                            {e.channel && CHANNELS.includes(e.channel as Channel) ? <Badge>Kanal: {channelLabel[e.channel as Channel]}</Badge> : null}
                            {lead ? (
                              <Link href={`/dashboard/leads/${lead.id}`} className="inline-flex items-center gap-1 rounded-md bg-rc-accent-soft px-2 py-0.5 text-xs font-medium text-rc-accent hover:underline">
                                Lead: {lead.name}
                              </Link>
                            ) : null}
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))
          )}
        </div>
      </ContentInset>
    </>
  );
}
