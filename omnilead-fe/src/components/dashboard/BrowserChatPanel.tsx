"use client";

import { useEffect, useRef, useState } from "react";
import { LockKeyhole, MessageCircle, Send } from "lucide-react";
import { Button } from "@/components/action/button";
import { browserApi, type BrowserChannel, type BrowserSession, type BrowserState } from "@/lib/browser-api";

const inputClass = "mt-2 w-full rounded-lg border border-rc-border bg-rc-surface px-3 py-2 text-sm text-rc-fg";
const ACTIVE = new Set(["opening", "running", "thinking", "executing", "extracting", "manual", "authenticating", "closing"]);

interface Props {
  state: BrowserState | null;
  channel: BrowserChannel;
  accountLabel: string;
  consent: boolean;
  onState: (state: BrowserState) => void;
  onAccountLabel: (value: string) => void;
}

export function BrowserChatPanel({ state, channel, accountLabel, consent, onState, onAccountLabel }: Props) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const session = state?.session;
  const working = Boolean(session && ACTIVE.has(session.status));
  const stage = session?.auth?.stage;
  const count = session?.chat?.length ?? 0;

  useEffect(() => { end.current?.scrollIntoView({ block: "nearest" }); }, [count, stage]);

  async function send(text: string) {
    if (!text.trim() || busy || working) return;
    setMessage(""); setError(""); setBusy(true);
    try { onState(await browserApi.chat(text, channel, accountLabel, consent)); }
    catch (e) { setError(e instanceof Error ? e.message : "Pesan belum dapat diproses."); }
    finally { setBusy(false); }
  }

  return <section className="rounded-xl border border-rc-border bg-rc-surface p-5">
    <h2 className="flex items-center gap-2 text-base font-semibold"><MessageCircle className="h-4 w-4" />Chat dengan agen</h2>
    <div className="mt-4 max-h-[520px] space-y-3 overflow-y-auto pr-1" aria-live="polite" aria-relevant="additions">
      <div className="rounded-xl bg-rc-bg p-3 text-sm leading-relaxed">Halo! Ceritakan yang ingin dikerjakan. Coba “login Instagram”, lalu “baca pesan pelanggan terbaru dan siapkan balasan”. Saya akan memberi kabar tentang langkah dan hasilnya.</div>
      {session?.chat?.map((item) => <div key={item.id} className={`whitespace-pre-wrap break-words rounded-xl p-3 text-sm leading-relaxed ${item.role === "user" ? "ml-5 border border-rc-border" : "mr-3 bg-rc-bg"}`}>
        <p className="mb-1 text-xs font-medium text-rc-fg-muted">{item.role === "user" ? "Anda" : "Agen"}</p>{item.text}
      </div>)}
      {session && stage && ["credentials", "username", "password", "verification"].includes(stage) && <SecureLogin key={`${session.channel}:${stage}`} session={session} accountLabel={accountLabel} disabled={busy || working} onState={onState} onAccountLabel={onAccountLabel} />}
      {stage === "manual" && <p className="rounded-lg border border-rc-border p-3 text-sm text-rc-fg-muted">{session?.auth.message} Kontrol manual tersedia di bawah layar browser.</p>}
      {working && <p role="status" className="rounded-lg bg-rc-bg p-3 text-sm text-rc-fg-muted">{session?.status === "authenticating" ? "Mengisi formulir dan menunggu hasil login…" : session?.status === "opening" ? "Membuka browser kanal…" : "Agen sedang bekerja. Langkah berikutnya muncul di sini."}</p>}
      {error && <p role="alert" className="rounded-lg border border-rc-border p-3 text-sm text-rc-danger">{error}</p>}
      <div ref={end} />
    </div>
    {!session && <Button purpose="action" className="mt-4" disabled={busy || !state?.enabled} onClick={() => void send(`Login ${channel}`)}>Bantu saya login</Button>}
    {session?.pending && <div className="mt-4 rounded-lg border border-rc-border p-3 text-sm">
      <p>Agen menunggu persetujuan langkah yang terlihat di layar.</p>
      <div className="mt-3 flex gap-2"><Button purpose="action" disabled={busy} onClick={() => void send("setujui")}>Setujui langkah</Button><Button purpose="action" disabled={busy} onClick={() => void send("tolak")}>Tolak</Button></div>
    </div>}
    <form className="mt-4 border-t border-rc-border pt-4" onSubmit={(event) => { event.preventDefault(); void send(message); }}>
      <label className="block text-sm">Pesan untuk agen<textarea className={`${inputClass} min-h-24 resize-y`} maxLength={2000} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Contoh: login Instagram atau baca pesan terbaru" disabled={busy || working || !state?.enabled} /></label>
      <p className="mt-2 text-xs text-rc-fg-muted">Password dan kode verifikasi diisi lewat kartu aman dalam chat.</p>
      <p className="mt-3 text-xs leading-relaxed text-rc-fg-muted">{consent ? "Agen membaca layar otomatis saat mengerjakan pesan Anda, menggunakan akun yang sedang terbuka." : "Pembacaan layar dimatikan di pengaturan sesi."}</p>
      <Button purpose="action" style="primary" type="submit" className="mt-3 w-full" disabled={busy || working || !message.trim() || !state?.enabled}><Send className="mr-2 h-4 w-4" />Kirim ke agen</Button>
    </form>
  </section>;
}

function SecureLogin({ session, accountLabel, disabled, onState, onAccountLabel }: { session: BrowserSession; accountLabel: string; disabled: boolean; onState: Props["onState"]; onAccountLabel: Props["onAccountLabel"] }) {
  const [username, setUsername] = useState(accountLabel || session.account_label);
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const stage = session.auth.stage;
  const userNeeded = stage === "credentials" || stage === "username";
  const passwordNeeded = stage === "credentials" || stage === "password";
  async function login() {
    const credentials = { username, password, code, image_revision: session.image_revision, confirmed: true };
    setPassword(""); setCode(""); setError(""); setBusy(true);
    try {
      onState(await browserApi.login(credentials));
      if (username.trim()) onAccountLabel(username.trim().slice(0, 100));
    } catch (e) { setError(e instanceof Error ? e.message : "Login belum dapat dikirim."); }
    finally { credentials.password = ""; credentials.code = ""; setBusy(false); }
  }
  return <form className="rounded-xl border border-rc-border p-4" onSubmit={(event) => { event.preventDefault(); void login(); }}>
    <h3 className="flex items-center gap-2 text-sm font-semibold"><LockKeyhole className="h-4 w-4" />{stage === "verification" ? "Kode verifikasi" : "Login akun"}</h3>
    <p className="mt-2 text-xs leading-relaxed text-rc-fg-muted">Agen mengisi kolom dan menekan tombol login. Password/kode langsung ke browser dan tidak disimpan dalam chat atau dikirim ke model.</p>
    {userNeeded && <label className="mt-3 block text-sm">Username / email<input className={inputClass} required maxLength={200} autoComplete="off" value={username} onChange={(event) => setUsername(event.target.value)} disabled={disabled || busy} /></label>}
    {passwordNeeded && <label className="mt-3 block text-sm">Password<input className={inputClass} type="password" required maxLength={1000} autoComplete="off" value={password} onChange={(event) => setPassword(event.target.value)} disabled={disabled || busy} /></label>}
    {stage === "verification" && <label className="mt-3 block text-sm">Kode dari platform<input className={inputClass} type="password" inputMode="numeric" required maxLength={30} autoComplete="off" value={code} onChange={(event) => setCode(event.target.value)} disabled={disabled || busy} /></label>}
    {error && <p role="alert" className="mt-3 text-sm text-rc-danger">{error}</p>}
    <Button purpose="action" style="primary" type="submit" className="mt-4 w-full" disabled={disabled || busy}>{stage === "verification" ? "Masukkan & kirim kode" : "Isi akun & lanjutkan login"}</Button>
  </form>;
}
