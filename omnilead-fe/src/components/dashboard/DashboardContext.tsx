"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  api,
  ApiError,
  type BeAction,
  type BeAgentHealth,
  type BeAudit,
  type BeChannel,
  type BeEvent,
  type BeLead,
  type BeSettings,
  type BeSummaryItem,
} from "@/lib/api";
import {
  adaptAction,
  adaptAudit,
  adaptChannel,
  adaptEvent,
  adaptLead,
  adaptSummary,
  adaptTrace,
} from "@/lib/adapt";
import type {
  Activity,
  AgentTrace,
  AuditEntry,
  ChannelStatus,
  LeadProfile,
  ProposedAction,
  SummaryItem,
} from "@/lib/types";

const POLL_MS = 3000;

interface Raw {
  events: BeEvent[];
  actions: BeAction[];
  leads: BeLead[];
  channels: BeChannel[];
  audit: BeAudit[];
  settings: BeSettings | null;
  agent: BeAgentHealth | null;
  summary: BeSummaryItem[];
}

const EMPTY: Raw = {
  events: [],
  actions: [],
  leads: [],
  channels: [],
  audit: [],
  settings: null,
  agent: null,
  summary: [],
};

interface DashboardState {
  /** true setelah fetch pertama selesai (berhasil atau gagal) */
  loaded: boolean;
  /** pesan error jika BE tidak terjangkau; null jika sehat */
  error: string | null;
  paused: boolean;
  dryRun: boolean;
  disabledChannels: string[];
  agent: BeAgentHealth | null;
  activities: Activity[];
  actions: ProposedAction[];
  traces: Record<string, AgentTrace>;
  leads: LeadProfile[];
  leadsById: Record<string, LeadProfile>;
  channels: ChannelStatus[];
  audit: AuditEntry[];
  summary: SummaryItem[];
  /** aksi yang menunggu keputusan atau tindakan manual pengguna */
  pendingCount: number;
  refresh: () => Promise<void>;
  togglePause: () => Promise<void>;
  setChannelEnabled: (channel: string, enabled: boolean) => Promise<void>;
  setDryRun: (value: boolean) => Promise<void>;
  approve: (id: string, editedText?: string) => Promise<void>;
  reject: (id: string, reason: string) => Promise<void>;
  retry: (id: string) => Promise<void>;
  markSent: (id: string) => Promise<void>;
}

const Ctx = createContext<DashboardState | null>(null);

const ACTIONABLE = new Set(["pending", "awaiting_manual_send", "failed"]);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [raw, setRaw] = useState<Raw>(EMPTY);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inflight = useRef(false);

  const refresh = useCallback(async () => {
    if (inflight.current) return;
    inflight.current = true;
    try {
      const [events, actions, leads, channels, audit, settings, agent, summary] =
        await Promise.all([
          api.events(),
          api.actions(),
          api.leads(),
          api.channels(),
          api.audit(),
          api.settings(),
          api.agentHealth(),
          api.summary(),
        ]);
      setRaw({ events, actions, leads, channels, audit, settings, agent, summary });
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409 && e.message.includes("Bisnis aktif berubah")) {
        setRaw(EMPTY);
        window.location.reload();
      }
      if (e instanceof ApiError && e.status === 401) {
        setRaw(EMPTY);
        window.location.replace("/login");
      }
      setError(e instanceof Error ? e.message : "Gagal memuat data");
    } finally {
      inflight.current = false;
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    // Fetch pertama dijadwalkan (bukan sinkron di body effect), lalu polling berkala.
    const first = setTimeout(() => void refresh(), 0);
    const t = setInterval(() => {
      if (document.visibilityState === "visible") void refresh();
    }, POLL_MS);
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [refresh]);

  const derived = useMemo(() => {
    const leadsRaw = new Map(raw.leads.map((l) => [l.id, l]));
    const pendingByEvent = new Map<string, number>();
    const actionsByEvent = new Map<string, BeAction[]>();
    for (const a of raw.actions) {
      if (!a.event_id) continue;
      actionsByEvent.set(a.event_id, [...(actionsByEvent.get(a.event_id) ?? []), a]);
      if (ACTIONABLE.has(a.status)) {
        pendingByEvent.set(a.event_id, (pendingByEvent.get(a.event_id) ?? 0) + 1);
      }
    }

    const traces: Record<string, AgentTrace> = {};
    for (const e of raw.events) {
      const t = adaptTrace(e.trace, actionsByEvent.get(e.id) ?? [], e);
      if (t) traces[e.id] = t;
    }

    const leads = raw.leads.map(adaptLead);
    return {
      activities: raw.events.map((e) =>
        adaptEvent(e, e.lead_id ? leadsRaw.get(e.lead_id) : undefined, pendingByEvent.get(e.id) ?? 0),
      ),
      actions: raw.actions.map((a) => adaptAction(a, raw.channels)),
      traces,
      leads,
      leadsById: Object.fromEntries(leads.map((l) => [l.id, l])),
      channels: raw.channels.map(adaptChannel),
      audit: raw.audit.map(adaptAudit),
      summary: raw.summary.map(adaptSummary),
      pendingCount: raw.actions.filter((a) => ACTIONABLE.has(a.status)).length,
    };
  }, [raw]);

  // Mutasi: panggil BE, lalu muat ulang. Error dilempar agar pemanggil bisa menampilkannya.
  const mutate = useCallback(
    async (fn: () => Promise<unknown>) => {
      try {
        await fn();
      } finally {
        await refresh();
      }
    },
    [refresh],
  );

  const value: DashboardState = {
    loaded,
    error,
    paused: raw.settings?.paused ?? false,
    dryRun: raw.settings?.dry_run ?? false,
    disabledChannels: raw.settings?.disabled_channels ?? [],
    agent: raw.agent,
    ...derived,
    refresh,
    togglePause: () => mutate(() => api.setPause(!(raw.settings?.paused ?? false))),
    setChannelEnabled: (channel, enabled) =>
      mutate(() => api.setChannelEnabled(channel, enabled)),
    setDryRun: (v) => mutate(() => api.patchSettings({ dry_run: v })),
    approve: (id, text) => mutate(() => api.approve(id, text)),
    reject: (id, reason) => mutate(() => api.reject(id, reason)),
    retry: (id) => mutate(() => api.retry(id)),
    markSent: (id) => mutate(() => api.markSent(id)),
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useDashboard(): DashboardState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useDashboard harus di dalam DashboardProvider");
  return ctx;
}
