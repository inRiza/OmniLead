"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Logo } from "@/components/brand/Logo";

const input = "mt-1.5 w-full rounded-lg border border-rc-border bg-rc-bg px-3 py-2.5 text-base text-rc-fg outline-none focus:border-rc-primary";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [registration, setRegistration] = useState(false);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = setTimeout(() => {
      void api.session().then((s) => {
        if (!s.enabled || s.user) window.location.replace("/dashboard");
        else { setRegistration(s.registration_enabled); setReady(true); }
      }).catch((e) => { setError(e.message); setReady(true); });
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const data = new FormData(event.currentTarget);
    const email = String(data.get("email") ?? "");
    const password = String(data.get("password") ?? "");
    setBusy(true); setError("");
    try {
      if (mode === "register") await api.register({ email, password, name: String(data.get("name") ?? "") });
      else await api.login(email, password);
      window.location.replace(mode === "register" ? "/dashboard/integrasi" : "/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tidak dapat masuk");
      setBusy(false);
    }
  }

  return (
    <main className="rc-brand flex min-h-dvh items-center justify-center bg-rc-bg px-5 py-10 text-rc-fg">
      <section className="w-full max-w-md rounded-2xl border border-rc-border bg-rc-surface p-6 shadow-sm sm:p-8">
        <Link href="/" className="mb-7 inline-flex" aria-label="Kembali ke beranda OmniLead"><Logo /></Link>
        <h1 className="text-2xl font-semibold">{mode === "login" ? "Selamat datang kembali" : "Buat akun OmniLead"}</h1>
        <p className="mt-2 text-base text-rc-fg-muted">{mode === "login" ? "Masuk untuk melihat pelanggan dan aktivitas Anda." : "Satu akun untuk semua bisnis Anda. Tambahkan bisnis dan hubungkan kanal setelah masuk."}</p>
        <form onSubmit={submit} className="mt-6 flex flex-col gap-4">
          {mode === "register" && <>
            <label className="text-sm font-medium">Nama Anda<input name="name" autoComplete="name" required maxLength={100} className={input} /></label>
          </>}
          <label className="text-sm font-medium">Email<input name="email" type="email" autoComplete="email" required maxLength={254} className={input} /></label>
          <label className="text-sm font-medium">Kata sandi<input name="password" type="password" autoComplete={mode === "register" ? "new-password" : "current-password"} required minLength={mode === "register" ? 12 : 1} maxLength={256} className={input} />{mode === "register" && <span className="mt-1 block text-sm text-rc-fg-muted">Minimal 12 karakter.</span>}</label>
          {error && <p role="alert" className="text-sm text-rc-danger">{error}</p>}
          <button disabled={busy || !ready} className="mt-1 cursor-pointer rounded-lg bg-rc-hero px-4 py-3 text-base font-semibold text-white transition-colors hover:bg-rc-hero-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-accent disabled:cursor-wait disabled:opacity-50">{busy ? "Memproses…" : mode === "login" ? "Masuk" : "Buat akun"}</button>
        </form>
        {registration && <p className="mt-6 text-center text-sm text-rc-fg-muted">{mode === "login" ? "Belum punya akun? " : "Sudah punya akun? "}<button type="button" disabled={busy} className="cursor-pointer font-semibold text-rc-fg underline" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "Daftar" : "Masuk"}</button></p>}
      </section>
    </main>
  );
}
