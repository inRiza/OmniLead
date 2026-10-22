"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, type Connection, type FacebookPages, type WhatsAppAccounts } from "@/lib/api";
import { whatsappSignup } from "@/lib/whatsapp-signup";
import { channelLabel } from "@/lib/ui";
import { Button } from "@/components/action/button";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { useDashboard } from "@/components/dashboard/DashboardContext";
import { useAccount } from "@/components/dashboard/AccountProvider";
import { LogoutButton } from "@/components/dashboard/LogoutButton";
import { Topbar } from "@/components/dashboard/Topbar";
import { Badge, ChannelIcon } from "@/components/primitives";
import { Select } from "@/components/ui/select";

const actionLabel: Record<string, string> = {
  list_posts: "Daftar unggahan", read_comments: "Baca komentar", post_comment: "Tulis komentar",
  reply_comment: "Balas komentar", send_message: "Kirim pesan",
};
const explanation: Record<string, string> = {
  instagram: "Hubungkan akun Business atau Creator untuk mengelola komentar dan pesan pelanggan.",
  facebook: "Hubungkan Facebook Page bisnis untuk mengelola komentar di post dan pesan Messenger.",
  email: "Izinkan OmniLead membaca dan membalas email bisnis melalui Gmail.",
  whatsapp: "Pilih akun bisnis dan nomor WhatsApp melalui jendela resmi Meta.",
};
const field = "mt-1 block w-full rounded-lg border border-rc-border bg-rc-bg px-3 py-2 text-base text-rc-fg";

export default function IntegrasiPage() {
  const d = useDashboard();
  const { session, refreshAccount } = useAccount();
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(session.enabled);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<string | null>(null);
  const [whatsapp, setWhatsapp] = useState<WhatsAppAccounts | null>(null);
  const [accountId, setAccountId] = useState("");
  const [pin, setPin] = useState("");
  const [facebook, setFacebook] = useState<FacebookPages | null>(null);
  const [pageId, setPageId] = useState("");

  const loadConnections = useCallback(async () => {
    if (!session.enabled) return;
    try { setConnections(await api.connections()); }
    catch (e) { setError(e instanceof Error ? e.message : "Gagal memuat koneksi"); }
    finally { setLoading(false); }
  }, [session.enabled]);

  useEffect(() => {
    const first = setTimeout(() => {
      const query = new URLSearchParams(window.location.search);
      const result = query.get("connection");
      if (result === "connected") setNotice("Akun berhasil terhubung. Anda dapat mulai mengelola aktivitasnya.");
      if (result === "cancelled") setError("Penghubungan dibatalkan. Akun sebelumnya tetap dapat digunakan.");
      if (result === "failed") setError("Akun belum berhasil dihubungkan. Pastikan semua izin diberikan dan coba kembali. Jika berulang, hubungi pengelola OmniLead.");
      if (result === "select" && query.get("provider") === "facebook") {
        api.facebookPages()
          .then((pages) => { setFacebook(pages); setPageId(pages.pages[0]?.id ?? ""); })
          .catch((e) => setError(e instanceof Error ? e.message : "Pilihan Page tidak tersedia. Hubungkan ulang Facebook."));
      }
      if (result) window.history.replaceState({}, "", "/dashboard/integrasi");
      void loadConnections();
    }, 0);
    const interval = setInterval(() => { if (document.visibilityState === "visible") void loadConnections(); }, 30_000);
    return () => { clearTimeout(first); clearInterval(interval); };
  }, [loadConnections]);

  async function perform(key: string, action: () => Promise<void>) {
    if (busy) return;
    setBusy(key); setError(""); setNotice("");
    try { await action(); }
    catch (e) { setError(e instanceof Error ? e.message : "Tidak dapat menyelesaikan permintaan"); }
    finally { setBusy(null); }
  }

  async function connect(provider: string) {
    await perform(provider, async () => {
      const start = await api.connect(provider);
      if (start.mode === "redirect") { window.location.assign(start.url); return; }
      const result = await whatsappSignup(start);
      setWhatsapp(result); setAccountId(result.accounts[0]?.id ?? ""); setPin("");
    });
  }

  async function disconnect(provider: string) {
    await perform(provider, async () => {
      await api.disconnect(provider); setConfirm(null);
      await Promise.all([loadConnections(), d.refresh()]);
      setNotice("Koneksi diputus. Riwayat pelanggan tetap tersimpan. Anda dapat menghubungkan akun lagi kapan saja.");
    });
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    await perform("profile", async () => {
      await api.updateProfile(String(values.get("name")), String(values.get("business")));
      await refreshAccount(); setNotice("Informasi bisnis disimpan.");
    });
  }

  const chosen = whatsapp?.accounts.find((a) => a.id === accountId);

  return <>
    <Topbar title="Integrasi" subtitle="Hubungkan kanal dan atur akun bisnis Anda" />
    <ContentInset className="rc-scrollbar overflow-y-auto">
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 p-4 pb-8 md:p-6">
        <section className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
          <h2 className="text-lg font-semibold">Kanal untuk {session.user?.business ?? "bisnis Anda"}</h2>
          <p className="mt-2 text-base text-rc-fg-muted">Klik Hubungkan, masuk ke akun Anda, lalu izinkan akses. OmniLead mengelola koneksinya secara otomatis, dan setiap tindakan agen tercatat di Audit.</p>
          <div className="mt-4"><Button purpose="nav" href="/dashboard/knowledge">Atur pengetahuan & tone agen</Button></div>
          {!session.enabled && <p className="mt-3 text-sm text-rc-fg-muted">Mode demo lokal aktif. Pengelola perlu mengaktifkan login untuk menghubungkan akun bisnis.</p>}
        </section>
        {error && <div role="alert" className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}<button type="button" className="ml-3 cursor-pointer underline" onClick={() => { setError(""); void loadConnections(); }}>Periksa kembali</button></div>}
        {notice && <p role="status" className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</p>}
        {loading && <p role="status" className="text-sm text-rc-fg-muted">Memeriksa koneksi akun…</p>}

        {whatsapp && <form className="rounded-xl border border-rc-border bg-rc-surface p-5" onSubmit={(e) => {
          e.preventDefault();
          void perform("whatsapp-select", async () => {
            await api.whatsappSelect(whatsapp.selection, accountId, pin);
            setWhatsapp(null); setPin("");
            await Promise.all([loadConnections(), d.refresh()]); setNotice("WhatsApp berhasil terhubung.");
          });
        }}>
          <h2 className="text-lg font-semibold">Pilih nomor WhatsApp bisnis</h2>
          <p className="mt-1 text-sm text-rc-fg-muted">Nomor berikut sudah dikonfirmasi oleh Meta. Satu nomor aktif untuk bisnis ini.</p>
          <div className="mt-4 text-sm font-medium">Nomor bisnis<Select className="mt-1" label="Nomor bisnis" value={accountId || null} onChange={setAccountId} options={whatsapp.accounts.map((a) => ({ value: a.id, label: a.label }))} /></div>
          {chosen && !chosen.registered && <label className="mt-4 block text-sm font-medium">PIN verifikasi dua langkah<input type="password" inputMode="numeric" autoComplete="off" value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))} pattern="[0-9]{6}" minLength={6} maxLength={6} required className={field} /><span className="mt-1 block text-sm text-rc-fg-muted">Gunakan PIN 6 digit nomor bisnis ini, atau buat PIN untuk nomor yang baru didaftarkan.</span></label>}
          <div className="mt-4 flex gap-2"><Button purpose="action" type="submit" style="primary" disabled={busy !== null || !accountId}>Gunakan nomor ini</Button><Button purpose="action" disabled={busy !== null} onClick={() => { setWhatsapp(null); setPin(""); }}>Batal</Button></div>
        </form>}

        {facebook && <form className="rounded-xl border border-rc-border bg-rc-surface p-5" onSubmit={(e) => {
          e.preventDefault();
          void perform("facebook-select", async () => {
            await api.facebookSelect(pageId);
            setFacebook(null);
            await Promise.all([loadConnections(), d.refresh()]); setNotice("Facebook Page berhasil terhubung.");
          });
        }}>
          <h2 className="text-lg font-semibold">Pilih Facebook Page</h2>
          <p className="mt-1 text-sm text-rc-fg-muted">Akun Anda mengelola beberapa Page. Pilih satu Page untuk bisnis ini.</p>
          <div className="mt-4 text-sm font-medium">Page<Select className="mt-1" label="Facebook Page" value={pageId || null} onChange={setPageId} options={facebook.pages.map((p) => ({ value: p.id, label: p.label }))} /></div>
          <div className="mt-4 flex gap-2"><Button purpose="action" type="submit" style="primary" disabled={busy !== null || !pageId}>Gunakan Page ini</Button><Button purpose="action" disabled={busy !== null} onClick={() => setFacebook(null)}>Batal</Button></div>
        </form>}

        {d.channels.map((channel) => {
          const connection = connections.find((c) => c.channel === channel.channel);
          const connected = session.enabled ? connection?.status === "connected" : channel.connected;
          const enabled = !d.disabledChannels.includes(channel.channel);
          const provider = connection?.provider;
          return <section key={channel.channel} className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
            <div className="flex flex-wrap items-start gap-3">
              <ChannelIcon channel={channel.channel} size="md" />
              <div className="min-w-0 flex-1"><h2 className="text-base font-semibold">{channelLabel[channel.channel]}</h2><p className="mt-1 text-sm text-rc-fg-muted">{explanation[channel.channel]}</p></div>
              <Badge dot tone={connected ? "green" : connection?.status === "reconnect_required" ? "amber" : "gray"}>{connected ? "Terhubung" : connection?.status === "reconnect_required" ? "Perlu autentikasi ulang" : "Belum terhubung"}</Badge>
            </div>
            {connection?.label && <p className="mt-3 text-base font-medium">{connection.label}</p>}
            {connected && connection?.expires_at ? <p className="mt-1 text-xs text-rc-fg-muted">Akses berlaku sampai {new Date(connection.expires_at * 1000).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })}</p> : null}
            {connection?.error && <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{connection.error}</p>}
            {connection && !connection.configured && <p className="mt-3 text-sm text-rc-fg-muted">Koneksi sedang disiapkan oleh pengelola OmniLead. Anda tetap dapat menempel pesan dan mengirim balasan secara manual.</p>}
            <div className="mt-4 flex flex-wrap gap-2">
              {provider && !connection.test_mode && <Button purpose="action" style={connected ? "secondary" : "primary"} disabled={busy !== null || !connection.configured} onClick={() => void connect(provider)}>{busy === provider ? "Menghubungkan…" : connected || connection.status === "reconnect_required" ? "Hubungkan ulang / ganti akun" : `Hubungkan ${channelLabel[channel.channel]}`}</Button>}
              {provider && !connection.test_mode && connection.status !== "disconnected" && <Button purpose="action" disabled={busy !== null} onClick={() => setConfirm(confirm === provider ? null : provider)}>Putuskan koneksi</Button>}
              <Button purpose="action" disabled={busy !== null} onClick={() => void perform(channel.channel, () => d.setChannelEnabled(channel.channel, !enabled))}>{enabled ? "Jeda kanal" : "Aktifkan kanal"}</Button>
            </div>
            {!enabled && <p className="mt-3 text-sm font-medium">Kanal dijeda. Pengiriman ditahan sampai Anda mengaktifkannya kembali.</p>}
            {confirm === provider && provider && <div className="mt-4 rounded-lg border border-rc-border bg-rc-bg p-4"><p className="text-sm">Putuskan {connection.label || channelLabel[channel.channel]} dari bisnis ini? Pengiriman melalui akun ini akan berhenti.</p><div className="mt-3 flex gap-2"><Button purpose="action" disabled={busy !== null} onClick={() => void disconnect(provider)}>Ya, putuskan</Button><Button purpose="action" onClick={() => setConfirm(null)}>Batal</Button></div></div>}
            <div className="mt-4 flex flex-wrap gap-1.5 border-t border-rc-border pt-4">{channel.capabilities.filter((cap) => cap.path !== null).map((cap) => <Badge key={cap.action} tone={cap.available ? "blue" : "gray"}>{actionLabel[cap.action] ?? cap.action}: {cap.available ? "Otomatis" : "Manual sampai terhubung"}</Badge>)}</div>
          </section>;
        })}

        <section className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
          <h2 className="text-base font-semibold">Pengiriman & agen</h2>
          <p className="mt-1 text-sm text-rc-fg-muted">{d.agent?.reachable ? "Agen aktif dan siap membalas." : "Agen belum dapat dihubungi."} Mode latihan saat ini {d.dryRun ? "aktif" : "mati"}.</p>
          <div className="mt-4"><Button purpose="nav" href="/dashboard/pengaturan">Atur di Pengaturan agen</Button></div>
        </section>
        {session.user && <section className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
          <h2 className="text-base font-semibold">Akun bisnis</h2><p className="mt-1 text-sm text-rc-fg-muted">{session.user.email}</p>
          <form key={session.user.name + session.user.business} onSubmit={saveProfile} className="mt-4 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium">Nama Anda<input name="name" defaultValue={session.user.name} required maxLength={100} className={field} /></label>
            <label className="text-sm font-medium">Nama bisnis<input name="business" defaultValue={session.user.business} required maxLength={100} className={field} /></label>
            <div className="flex flex-wrap items-center gap-2 sm:col-span-2">
              <Button purpose="action" type="submit" disabled={busy !== null}>Simpan perubahan</Button>
              <LogoutButton inline />
            </div>
          </form>
        </section>}
      </div>
    </ContentInset>
  </>;
}
