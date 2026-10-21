"use client";

import type { Activity, AgentTrace, ProposedAction } from "@/lib/types";
import { TimeAgo } from "@/components/TimeAgo";

const TOOL_LABEL: Record<string, string> = {
  get_timeline: "Membaca riwayat pelanggan",
  search_catalog_faq: "Mencari pengetahuan dan katalog bisnis",
  check_channel_window: "Memeriksa izin waktu balasan",
  score_lead: "Menghitung prioritas pelanggan",
  propose_reply: "Mengusulkan balasan",
  propose_private_reply: "Mengusulkan balasan pribadi",
  propose_crm_update: "Mengusulkan pembaruan CRM",
  propose_followup: "Mengusulkan tindak lanjut",
};

export function agentStatus(activity: Activity, actions: ProposedAction[]) {
  if (activity.eventStatus === "processing") return "Sedang bekerja";
  if (activity.eventStatus === "new") return "Menunggu diproses";
  if (activity.eventStatus === "held") return "Ditahan · agen dijeda";
  if (activity.eventStatus === "agent_error") return "Analisis gagal";
  if (activity.eventStatus === "review") return "Perlu ditinjau";
  if (actions.some((a) => a.status === "failed")) return "Pengiriman gagal";
  if (actions.some((a) => a.status === "pending")) return "Menunggu persetujuan";
  if (actions.some((a) => a.status === "awaiting_manual_send")) return "Menunggu kirim manual";
  if (actions.some((a) => a.status === "executing" || a.status === "approved" || a.status === "edited")) return "Menjalankan aksi yang disetujui";
  return "Analisis selesai";
}

const NEXT: Record<string, string> = {
  triage: "Baca konteks bisnis dan siapkan rencana penanganan.",
  triage_done: "Siapkan rencana dan usulan tindakan.",
  plan: "Jalankan tool yang diperlukan untuk menyusun usulan.",
  drafting: "Tunggu tool atau usulan dari model, lalu periksa hasilnya.",
  tool: "Lanjutkan penyusunan usulan berdasarkan hasil tool.",
  proposal: "Periksa usulan sebelum meminta persetujuan Anda.",
  guard: "Selesaikan pemeriksaan; revisi jika diperlukan.",
  revision: "Periksa kembali usulan yang diperbaiki.",
  fallback: "Susun draf dengan templat, lalu jalankan pemeriksaan.",
};

export function AgentActivity({ activity, trace, actions = [] }: {
  activity: Activity; trace?: AgentTrace; actions?: ProposedAction[];
}) {
  const records = trace?.activity ?? [];
  const last = records.at(-1);
  const working = activity.eventStatus === "processing";
  const status = agentStatus(activity, actions);
  const previews = working ? records.filter((item) => item.phase === "proposal" && item.text).slice(-3) : [];
  const next = working ? NEXT[last?.phase ?? ""] ?? "Selesaikan analisis dan simpan usulan ke antrean persetujuan."
    : activity.eventStatus === "held" ? "Lanjutkan agen untuk memproses pesan ini."
    : activity.eventStatus === "agent_error" ? "Proses ulang pesan setelah koneksi agen tersedia."
    : activity.eventStatus === "new" ? "Mulai mengenali maksud pesan."
    : actions.some((a) => a.status === "pending") ? "Tinjau draf di bawah, lalu setujui, ubah, atau tolak."
    : activity.eventStatus === "review" ? "Tinjau hasil pemeriksaan sebelum melanjutkan."
    : "Lihat hasil tindakan dan riwayat percakapan.";

  return (
    <section className="min-w-0 rounded-lg border border-rc-border bg-rc-surface p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-rc-fg">Aktivitas agen</h2>
        <span role="status" className="inline-flex items-center gap-2 rounded-full bg-rc-surface-hover px-3 py-1 text-xs font-medium text-rc-fg">
          <span className={`h-1.5 w-1.5 rounded-full bg-current ${working ? "motion-safe:animate-pulse" : ""}`} />
          {status}
        </span>
      </div>
      <p className="mt-2 text-sm text-rc-fg-muted">{trace?.goal || "Menyiapkan tanggapan untuk pesan pelanggan."}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-md bg-rc-surface-hover/60 p-3">
          <h3 className="text-xs font-medium text-rc-fg-subtle">{working ? "Sedang dikerjakan" : "Status terakhir"}</h3>
          <p className="mt-1 text-sm text-rc-fg">{working ? trace?.status || status : status}</p>
          {last && <p className="mt-1 text-xs text-rc-fg-muted">Pembaruan <TimeAgo iso={last.at} /> · {(last.elapsed_ms / 1000).toFixed(1)} dtk sejak mulai</p>}
        </div>
        <div className="rounded-md border border-rc-border p-3">
          <h3 className="text-xs font-medium text-rc-fg-subtle">Langkah berikutnya</h3>
          <p className="mt-1 text-sm text-rc-fg">{next}</p>
        </div>
      </div>

      {activity.reason && <div className="mt-4 text-sm"><h3 className="font-medium text-rc-fg">Ringkasan penilaian</h3><p className="mt-1 text-rc-fg-muted">{activity.reason}</p></div>}
      {trace?.plan.length ? <details className="mt-4 rounded-md border border-rc-border px-3 py-2">
        <summary className="cursor-pointer text-sm font-medium text-rc-fg">Rencana penanganan · {trace.plan.length} langkah</summary>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-rc-fg-muted">{trace.plan.map((step, i) => <li key={i}>{step}</li>)}</ol>
      </details> : null}

      <div className="mt-5">
        <h3 className="text-sm font-semibold text-rc-fg">Jejak pelaksanaan</h3>
        <p className="mt-1 text-xs text-rc-fg-muted">Tahap, hasil tool, dan alasan usulan yang tercatat selama proses.</p>
        <ol className="mt-3 space-y-3">
          {records.map((item, i) => <li key={`${item.sequence}-${i}`} className="relative border-l border-rc-border pl-4">
            <span className="absolute -left-1 top-1.5 h-2 w-2 rounded-full bg-rc-fg-subtle" />
            <div className="flex flex-wrap items-baseline justify-between gap-x-3">
              <p className="text-sm font-medium text-rc-fg">{item.tool ? TOOL_LABEL[item.tool] ?? item.tool : item.label}</p>
              <span className="text-xs tabular-nums text-rc-fg-subtle">+{(item.elapsed_ms / 1000).toFixed(1)} dtk</span>
            </div>
            {item.intents?.length ? <p className="mt-1 text-sm text-rc-fg-muted">Maksud: {item.intents.join(", ")}</p> : null}
            {item.result && <p className="mt-1 whitespace-pre-wrap break-words text-sm text-rc-fg-muted">{item.result}</p>}
            {item.reason && <p className="mt-1 whitespace-pre-wrap break-words text-sm text-rc-fg-muted">Alasan: {item.reason}</p>}
            {item.guard_summary && <p className="mt-1 text-sm text-rc-fg-muted">{item.guard_summary}</p>}
            {item.engine && <p className="mt-1 text-xs text-rc-fg-muted">Engine: {item.engine}</p>}
            {item.tool && <details className="mt-1 text-xs text-rc-fg-subtle"><summary className="cursor-pointer">Tool call · {item.tool}</summary><pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap break-all rounded bg-rc-surface-hover p-2">{JSON.stringify(item.input ?? {}, null, 2)}</pre></details>}
          </li>)}
          {!records.length && trace?.steps.map((step, i) => <li key={i} className="border-l border-rc-border pl-4">
            <p className="text-sm font-medium text-rc-fg">{TOOL_LABEL[step.tool] ?? step.tool}</p>
            <p className="mt-1 break-words text-sm text-rc-fg-muted">{step.output}</p>
            <details className="mt-1 text-xs text-rc-fg-subtle"><summary className="cursor-pointer">Tool call · {step.tool}</summary><p className="mt-1 break-all">{step.input || "Tanpa parameter"}</p></details>
          </li>)}
        </ol>
        {!records.length && !trace?.steps.length && <p className="mt-3 text-sm text-rc-fg-muted">{working ? "Menunggu pembaruan pertama dari agen. Tahap baru muncul setelah benar-benar dijalankan." : "Belum ada langkah yang tercatat untuk pesan ini."}</p>}
      </div>

      {previews.map((item) => <div key={item.sequence} className="mt-4 rounded-md border border-dashed border-rc-border p-3"><h3 className="text-xs font-medium text-rc-fg-subtle">Usulan sementara · belum selesai diperiksa</h3><p className="mt-2 whitespace-pre-wrap break-words text-sm text-rc-fg">{item.text}</p>{item.reason && <p className="mt-2 text-xs text-rc-fg-muted">Alasan: {item.reason}</p>}</div>)}

      {trace?.guardSummary && <p className="mt-4 border-t border-rc-border pt-3 text-sm font-medium text-rc-fg">Pemeriksaan: {trace.guardSummary}</p>}
      {!!trace?.guard.length && <ul className="mt-2 space-y-1 text-sm">{trace.guard.map((check, i) => <li key={i} className={check.passed ? "text-rc-fg-muted" : "text-rc-danger"}>{check.passed ? "Lolos" : "Perlu ditinjau"}: {check.label}</li>)}</ul>}
      {!working && activity.eventStatus === "agent_error" && <p role="alert" className="mt-3 text-sm text-rc-danger">{activity.reason || "Analisis belum selesai. Coba proses ulang pesan."}</p>}
    </section>
  );
}
