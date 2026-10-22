"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Check, CircleStop, Monitor, MousePointer2, RefreshCw, X } from "lucide-react";
import { Button } from "@/components/action/button";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { useAccount } from "@/components/dashboard/AccountProvider";
import { BrowserChatPanel } from "@/components/dashboard/BrowserChatPanel";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { browserApi, type BrowserChannel, type BrowserSession, type BrowserState, type ManualControl } from "@/lib/browser-api";

const CHANNELS: [BrowserChannel, string][] = [["instagram", "Instagram"], ["facebook", "Facebook"], ["whatsapp", "WhatsApp Web"], ["email", "Gmail"]];
const STATUS: Record<string, string> = { opening: "Membuka browser", ready: "Browser siap", running: "Membaca layar", thinking: "Menyiapkan langkah", extracting: "Membaca pesan dari layar", manual: "Menjalankan input Anda", authenticating: "Memproses login", awaiting_approval: "Menunggu persetujuan langkah", executing: "Menjalankan langkah", needs_user: "Perlu bantuan Anda", done: "Tugas selesai", stopped: "Tugas dihentikan", closing: "Menutup browser", closed: "Browser ditutup", error: "Perlu diperiksa" };
const OPERATIONS: Record<string, string> = { click: "Klik", type: "Ketik", press: "Tekan tombol", navigate: "Buka halaman" };
const BUSY = new Set(["opening", "running", "thinking", "extracting", "executing", "manual", "authenticating", "closing"]);
const inputClass = "mt-2 w-full rounded-lg border border-rc-border bg-rc-surface px-3 py-2 text-sm text-rc-fg";
const cardClass = "rounded-xl border border-rc-border bg-rc-surface p-5";

export default function BrowserAgentPage() {
  const { session } = useAccount();
  return <BrowserWorkspace key={session.user?.workspace_id ?? "loading"} />;
}

function BrowserWorkspace() {
  const { session: account } = useAccount();
  const { paused, disabledChannels, dryRun } = useDashboard();
  const [state, setState] = useState<BrowserState | null>(null);
  const [channel, setChannel] = useState<BrowserChannel>("instagram");
  const [accountLabel, setAccountLabel] = useState("");
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const [busy, setBusy] = useState(false);
  const [manual, setManual] = useState(false);
  const [manualText, setManualText] = useState("");
  const workspace = account.user?.workspace_id;

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const result = await browserApi.state();
        if (alive) { setState(result); setPollError(""); }
      } catch (e) {
        if (alive) setPollError(e instanceof Error ? e.message : "Browser belum dapat dihubungi");
      } finally {
        if (alive) timer = setTimeout(() => void refresh(), 2000);
      }
    }
    void refresh();
    return () => { alive = false; clearTimeout(timer); };
  }, [workspace]);

  async function act(operation: () => Promise<BrowserState>) {
    setBusy(true); setError("");
    try { setState(await operation()); }
    catch (e) { setError(e instanceof Error ? e.message : "Langkah belum berhasil"); }
    finally { setBusy(false); }
  }

  const session = state?.session;
  const opened = session && session.status !== "closed";
  const working = session && BUSY.has(session.status);
  const pending = session?.pending;
  const activeChannel = opened && session ? session.channel : channel;
  const held = paused || disabledChannels.includes(activeChannel);

  async function control(command: Omit<ManualControl, "image_revision">) {
    if (!session || working || pending || busy) return;
    setConsent(false);
    setManualText("");
    await act(() => browserApi.manual({ ...command, image_revision: session.image_revision }));
  }

  return <>
    <Topbar title="Agen browser" subtitle={`Bekerja melalui layar untuk ${account.user?.business ?? "bisnis aktif"}.`} />
    <ContentInset className="rc-scrollbar overflow-y-auto">
      <div className="mx-auto w-full max-w-6xl space-y-5 pt-1 pb-10">
        <section className={`${cardClass} flex flex-wrap items-center justify-between gap-4`}>
          <div className="max-w-2xl">
            <p className="flex items-center gap-2 text-sm font-semibold"><Monitor className="h-4 w-4" />OpenClaw · browser terbimbing</p>
            <p className="mt-2 text-sm leading-relaxed text-rc-fg-muted">Ceritakan tugas lewat chat. Agen membantu login melalui kartu aman, membaca layar, dan menyiapkan langkah berikutnya. Pengiriman pesan menunggu persetujuan Anda.</p>
          </div>
          {opened && <div className="flex gap-2">
            <Button purpose="action" disabled={busy || session.status === "closing"} onClick={() => void act(browserApi.stop)}><CircleStop className="mr-2 h-4 w-4" />Berhenti</Button>
            <Button purpose="action" disabled={busy || session.status === "closing"} onClick={() => void act(browserApi.close)}><X className="mr-2 h-4 w-4" />Tutup browser</Button>
          </div>}
        </section>

        {(error || pollError) && <p role="alert" className="rounded-lg border border-rc-border bg-rc-surface p-4 text-sm text-rc-danger">{error || pollError}</p>}
        {state && !state.enabled ? <section className={cardClass}>
          <h2 className="font-semibold">Agen browser belum diaktifkan</h2>
          <p className="mt-2 text-sm text-rc-fg-muted">Pengelola perlu mengaktifkan runtime browser pada server OmniLead. Setelah aktif, Anda bisa login dan mengendalikan layarnya dari halaman ini.</p>
        </section> : <div className="grid min-w-0 items-start gap-5 lg:grid-cols-[minmax(340px,430px)_minmax(0,1fr)]">
          <div className="space-y-5">
            <BrowserChatPanel state={state} channel={activeChannel} accountLabel={accountLabel} consent={consent} onState={setState} onAccountLabel={setAccountLabel} onConsent={setConsent} />
            <details className={cardClass}>
              <summary className="cursor-pointer text-sm font-semibold">Kanal &amp; pengaturan akun</summary>
              <label className="mt-4 block text-sm">Kanal
                <select className={inputClass} value={activeChannel} disabled={Boolean(opened) || busy || !state} onChange={(e) => { setChannel(e.target.value as BrowserChannel); setAccountLabel(""); setConsent(false); }}>
                  {CHANNELS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>
              <label className="mt-4 block text-sm">Akun pada browser<input className={inputClass} maxLength={100} placeholder="Username atau alamat email" value={accountLabel} onChange={(e) => setAccountLabel(e.target.value)} /></label>
              <p className="mt-3 text-xs text-rc-fg-muted">Profil terpisah untuk setiap bisnis dan kanal. Login browser berbeda dari koneksi API. Pengetahuan dan tone mengikuti bisnis ini.</p>
              {!opened && <Button purpose="action" className="mt-4" disabled={busy || !state} onClick={() => void act(() => browserApi.open(channel))}>Buka browser</Button>}
              {opened && <Button purpose="action" className="mt-4" disabled={Boolean(working) || busy} onClick={() => void act(browserApi.capture)}><RefreshCw className="mr-2 h-4 w-4" />Perbarui layar</Button>}
              {held && <p className="mt-3 text-xs text-rc-fg-muted">Agen/kanal sedang dijeda. Login pemilik tetap tersedia; aktifkan kanal untuk menjalankan tugas agen.</p>}
            </details>
          </div>

          <div className="min-w-0 space-y-5">
            <section className={`${cardClass} min-w-0`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-base font-semibold">Layar browser</h2>
                <p role="status" className="text-sm text-rc-fg-muted">{STATUS[session?.status ?? ""] ?? "Belum dibuka"}{session ? ` · ${session.steps}/12 langkah` : ""}</p>
              </div>
              {session?.page_url && <p className="mt-2 truncate text-xs text-rc-fg-subtle">{session.page_url}</p>}
              {session?.task && <p className="mt-3 break-words text-sm text-rc-fg-muted">Tugas untuk {session.account_label}: {session.task}</p>}
              {session?.image_base64 ? <div className="relative mt-4 overflow-hidden rounded-lg border border-rc-border bg-rc-bg">
                <button type="button" className="block w-full disabled:cursor-default" aria-label="Klik posisi pada layar browser dalam kontrol manual" disabled={!manual || Boolean(working) || busy || Boolean(pending)} onClick={(event) => {
                  if (!event.detail) return;
                  const rect = event.currentTarget.getBoundingClientRect();
                  void control({ operation: "click", x: Math.round((event.clientX - rect.left) / rect.width * 1000), y: Math.round((event.clientY - rect.top) / rect.height * 1000) });
                }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="block h-auto w-full" width={1280} height={800} src={`data:image/jpeg;base64,${session.image_base64}`} alt="Screenshot terbaru dari browser bisnis aktif" />
                </button>
                {pending && !pending.target_ref && ["click", "type"].includes(pending.operation) && <span aria-label="Sasaran langkah yang diusulkan" className="pointer-events-none absolute flex h-8 w-8 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 border-white bg-rc-accent text-white shadow" style={{ left: `${pending.x / 10}%`, top: `${pending.y / 10}%` }}><MousePointer2 className="h-4 w-4" /></span>}
              </div> : <div className="mt-4 flex min-h-60 items-center justify-center rounded-lg border border-dashed border-rc-border px-6 text-center text-sm text-rc-fg-muted">Buka browser untuk melihat layar. Screenshot diperbarui saat agen mengamati atau Anda menekan Perbarui layar.</div>}
              {session?.observation && <p className="mt-4 whitespace-pre-wrap break-words text-sm text-rc-fg-muted">{session.observation}</p>}
              {session?.error && <div role="alert" className="mt-4 space-y-3">
                <p className="text-sm text-rc-danger">{session.error}</p>
                <Button purpose="action" style="primary" disabled={busy || Boolean(working)} onClick={() => void act(browserApi.reopen)}>Buka ulang browser</Button>
              </div>}
              {opened && <details className="mt-4 border-t border-rc-border pt-4">
                <summary className="mb-3 cursor-pointer text-sm font-medium">Kontrol manual jika diperlukan</summary>
                <label className="flex items-center gap-2 text-sm font-medium"><input type="checkbox" checked={manual} disabled={Boolean(working) || Boolean(pending) || busy} onChange={(event) => { setManual(event.target.checked); setManualText(""); setConsent(false); }} />Kontrol manual untuk login / mengambil alih</label>
                {manual && <form className="mt-3 space-y-3" onSubmit={(event) => { event.preventDefault(); void control({ operation: "type", text: manualText }); }}>
                  <p className="text-xs leading-relaxed text-rc-fg-muted">Klik kolom pada screenshot dahulu. Teks langsung masuk ke browser tanpa dikirim ke model. Tombol Enter atau klik dapat mengirim formulir/pesan; periksa layar sebelum menekannya. Matikan kontrol manual setelah login dan buka inbox.</p>
                  <label className="block text-sm">Teks untuk kolom yang dipilih<input className={inputClass} type="password" autoComplete="off" maxLength={4000} value={manualText} onChange={(event) => setManualText(event.target.value)} /></label>
                  <Button purpose="action" type="submit" disabled={busy || Boolean(working) || !manualText}>Masukkan teks ke browser</Button>
                  <div className="flex flex-wrap gap-2">{(["Tab", "Enter", "Backspace", "Escape", "PageUp", "PageDown", "ControlOrMeta+A"] as const).map((key) => <Button key={key} purpose="action" disabled={busy || Boolean(working)} onClick={() => void control({ operation: "press", key })}>{key === "ControlOrMeta+A" ? "Pilih semua teks" : key}</Button>)}
                    <Button purpose="action" disabled={busy || Boolean(working)} onClick={() => void control({ operation: "inbox" })}>Buka inbox kanal</Button>
                  </div>
                </form>}
              </details>}
              {opened && <div className="mt-4 border-t border-rc-border pt-4">
                <Button purpose="action" disabled={busy || Boolean(working) || Boolean(pending) || held || !consent || manual} onClick={() => void act(() => browserApi.extract(consent))}>Baca pesan layar untuk Workspace</Button>
                <p className="mt-2 text-xs text-rc-fg-muted">Buka satu percakapan, lalu baca pesan pelanggan dari screenshot. Aktifkan izin screenshot di chat. Anda meninjau isi dan pengirim sebelum pesan dianalisis di Workspace.</p>
              </div>}
            </section>

            {session?.extracted && <ImportBrowserMessage key={session.extracted.id} extracted={session.extracted} accountLabel={accountLabel || session.account_label} />}

            {pending && <section className={`${cardClass} border-rc-accent`} aria-label="Persetujuan langkah browser">
              <h2 className="flex items-center gap-2 font-semibold"><MousePointer2 className="h-4 w-4" />Agen ingin: {OPERATIONS[pending.operation]}</h2>
              <p className="mt-3 text-sm text-rc-fg-muted">{pending.reason}</p>
              {pending.target_label && <p className="mt-2 break-words text-sm">Sasaran: {pending.target_label}{pending.target_ref ? ` (${pending.target_ref})` : ""}</p>}
              {pending.operation === "type" && <p className="mt-3 whitespace-pre-wrap break-words rounded-lg bg-rc-bg p-3 text-sm">{pending.text}</p>}
              {pending.operation === "navigate" && <p className="mt-3 break-all rounded-lg bg-rc-bg p-3 text-sm">{pending.url}</p>}
              {pending.operation === "press" && <p className="mt-3 text-sm">Tombol: <kbd>{pending.key}</kbd></p>}
              <p className="mt-3 text-xs text-rc-fg-muted">Periksa sasaran dan teks pada layar. Langkah ini dapat mengirim pesan atau mengubah akun. Persetujuan berlaku untuk satu langkah selama dua menit.</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button purpose="action" style="primary" disabled={busy || held || dryRun} onClick={() => void act(() => browserApi.approve(pending.id))}><Check className="mr-2 h-4 w-4" />Setujui langkah ini</Button>
                <Button purpose="action" disabled={busy} onClick={() => void act(browserApi.stop)}>Tolak &amp; hentikan</Button>
              </div>
              {dryRun && <p className="mt-3 text-xs text-rc-fg-muted">Mode simulasi aktif. Ubah di <Link href="/dashboard/pengaturan" className="underline">Pengaturan Agen</Link> sebelum menjalankan input browser.</p>}
            </section>}

            {session?.result && session.auth?.stage === "none" && <section className={cardClass}>
              <h2 className="font-semibold">Hasil / draf</h2>
              <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-relaxed">{session.result}</p>
              <p className="mt-3 text-xs text-rc-fg-muted">Draf visual belum melewati pemeriksaan Guard CRM. Periksa fakta dan penerima sebelum mengirim.</p>
            </section>}

            {session && session.history.length > 0 && <section className={cardClass}>
              <h2 className="font-semibold">Aktivitas browser</h2>
              <p className="mt-1 text-xs text-rc-fg-muted">Pengamatan, usulan, dan langkah yang benar-benar dijalankan. Riwayat sementara untuk sesi ini.</p>
              <ol className="mt-4 max-h-80 space-y-3 overflow-y-auto">{session.history.slice().reverse().map((item) => <li key={item.id} className="border-l-2 border-rc-border pl-3">
                <p className="text-xs font-medium text-rc-fg-subtle">{item.operation} · {new Date(item.at * 1000).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</p>
                <p className="mt-1 break-words text-sm text-rc-fg-muted">{item.label}</p>
              </li>)}</ol>
            </section>}
          </div>
        </div>}
      </div>
    </ContentInset>
  </>;
}

function ImportBrowserMessage({ extracted, accountLabel }: { extracted: NonNullable<BrowserSession["extracted"]>; accountLabel: string }) {
  const [handle, setHandle] = useState(extracted.handle);
  const [name, setName] = useState(extracted.name);
  const [text, setText] = useState(extracted.text);
  const [confirmed, setConfirmed] = useState(false);
  const [eventId, setEventId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function importMessage() {
    setBusy(true); setError("");
    try {
      const result = await browserApi.importMessage({ extraction_id: extracted.id, account_label: accountLabel,
        handle, name, text, confirmed_incoming: confirmed });
      setEventId(result.event_id);
    } catch (e) { setError(e instanceof Error ? e.message : "Pesan belum masuk Workspace"); }
    finally { setBusy(false); }
  }
  return <section className={cardClass}>
    <h2 className="font-semibold">Tinjau pesan dari layar</h2>
    <p className="mt-2 break-all text-xs text-rc-fg-subtle">Sumber: {extracted.page_url}</p>
    {eventId ? <div className="mt-4 text-sm">
      <p>Pesan sudah masuk Workspace. Agent menyiapkan draf dengan knowledge base dan pemeriksaan Guard bisnis ini.</p>
      <Link href={`/dashboard/inbox?id=${encodeURIComponent(eventId)}`} className="mt-3 inline-block font-medium text-rc-accent underline">Lihat pesan &amp; draf di Workspace</Link>
    </div> : <form onSubmit={(event) => { event.preventDefault(); void importMessage(); }}>
      <label className="mt-4 block text-sm">Username / alamat pengirim<input className={inputClass} required maxLength={200} value={handle} onChange={(e) => setHandle(e.target.value)} /></label>
      <label className="mt-3 block text-sm">Nama pelanggan<input className={inputClass} maxLength={200} value={name} onChange={(e) => setName(e.target.value)} /></label>
      <label className="mt-3 block text-sm">Pesan masuk<textarea className={`${inputClass} min-h-28`} required maxLength={10000} value={text} onChange={(e) => setText(e.target.value)} /></label>
      <label className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-rc-fg-muted"><input type="checkbox" className="mt-0.5" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />Saya memastikan ini pesan pelanggan kepada akun {accountLabel || "yang sudah saya buka"}, dan pengirim serta isi sudah sesuai screenshot.</label>
      <p className="mt-3 text-xs text-rc-fg-muted">Draf untuk sumber browser tidak dikirim melalui koneksi API. Tinjau dan gunakan browser yang sesuai untuk membalas.</p>
      {error && <p role="alert" className="mt-3 text-sm text-rc-danger">{error}</p>}
      <Button purpose="action" type="submit" style="primary" className="mt-4" disabled={busy || !confirmed || !accountLabel.trim() || !handle.trim() || !text.trim()}>{busy ? "Memasukkan pesan…" : "Masukkan & analisis di Workspace"}</Button>
      {!accountLabel.trim() && <p className="mt-2 text-xs text-rc-fg-muted">Isi nama akun yang Anda buka pada formulir tugas dahulu.</p>}
    </form>}
  </section>;
}
