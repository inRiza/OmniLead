"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { Logo, LogoMark } from "@/components/brand/Logo";
import { HeroContours } from "@/components/brand/HeroContours";

const input =
  "mt-1.5 block min-h-11 w-full rounded-md border border-rc-border bg-rc-surface px-3.5 text-sm text-rc-fg outline-none placeholder:text-rc-fg-subtle focus:border-rc-accent focus:ring-2 focus:ring-rc-accent/15";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [registration, setRegistration] = useState(false);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [show, setShow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      void api.session().then((s) => {
        if (!s.enabled || s.user) window.location.replace("/bisnis");
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
      window.location.replace(mode === "register" ? "/bisnis?baru=1" : "/bisnis");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Tidak dapat masuk");
      setBusy(false);
    }
  }

  const login = mode === "login";

  return (
    <main className="rc-brand rc-app grid min-h-dvh bg-rc-surface text-rc-fg lg:grid-cols-2">
      <section className="flex flex-col px-6 py-6 sm:px-10 lg:px-16">
        <Link href="/" aria-label="Kembali ke beranda" className="w-fit">
          <Logo />
        </Link>

        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-12">
          <h1 className="text-3xl font-semibold tracking-tight">{login ? "Selamat datang kembali" : "Buat akun OmniLead"}</h1>
          <p className="mt-2 text-sm text-rc-fg-muted">
            {login ? "Masuk untuk melihat pelanggan dan hasil kerja agen Anda." : "Satu akun untuk semua bisnis Anda. Tambahkan bisnis dan hubungkan kanal setelah masuk."}
          </p>

          <form onSubmit={submit} className="mt-8 flex flex-col gap-4">
            {!login && (
              <label className="text-sm font-medium">
                Nama Anda
                <input name="name" autoComplete="name" required maxLength={100} placeholder="Nama lengkap" className={input} />
              </label>
            )}
            <label className="text-sm font-medium">
              Email
              <input name="email" type="email" autoComplete="email" required maxLength={254} placeholder="nama@bisnis.com" className={input} />
            </label>
            <label className="text-sm font-medium">
              Kata sandi
              <span className="relative block">
                <input
                  name="password"
                  type={show ? "text" : "password"}
                  autoComplete={login ? "current-password" : "new-password"}
                  required
                  minLength={login ? 1 : 12}
                  maxLength={256}
                  placeholder={login ? "Kata sandi Anda" : "Minimal 12 karakter"}
                  className={`${input} pr-11`}
                />
                <button
                  type="button"
                  onClick={() => setShow((v) => !v)}
                  aria-label={show ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                  className="absolute top-1/2 right-1.5 inline-flex h-8 w-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-md text-rc-fg-muted hover:text-rc-fg"
                >
                  {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </span>
            </label>
            {error && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
            <button
              disabled={busy || !ready}
              className="group mt-2 inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-md bg-rc-accent px-4 text-sm font-semibold text-white transition-colors hover:bg-rc-accent-hover disabled:cursor-wait disabled:opacity-50"
            >
              {busy ? "Memproses…" : login ? "Masuk" : "Buat akun"}
              {!busy && <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />}
            </button>
          </form>

          {registration && (
            <p className="mt-6 text-center text-sm text-rc-fg-muted">
              {login ? "Belum punya akun? " : "Sudah punya akun? "}
              <button
                type="button"
                disabled={busy}
                className="cursor-pointer font-semibold text-rc-accent hover:underline"
                onClick={() => {
                  setMode(login ? "register" : "login");
                  setError("");
                }}
              >
                {login ? "Daftar" : "Masuk"}
              </button>
            </p>
          )}
        </div>

        <p className="flex items-center gap-1.5 text-xs text-rc-fg-subtle">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
          Data pelanggan tersimpan terpisah untuk setiap bisnis.
        </p>
      </section>

      <aside className="relative hidden overflow-hidden bg-rc-hero lg:m-3 lg:flex lg:items-center lg:justify-center lg:rounded-2xl lg:p-12 xl:p-16">
        <HeroContours />
        <div className="relative mx-auto max-w-md px-4 text-center">
          <p className="inline-flex flex-wrap items-center justify-center gap-x-2.5 gap-y-2 text-2xl leading-snug font-semibold tracking-tight text-balance text-white sm:text-3xl xl:text-4xl">
            {login ? (
              <>
                Mulai raih untung dengan
                <span className="inline-flex items-center gap-2 whitespace-nowrap">
                  <LogoMark size={36} className="rounded-lg shadow-sm" />
                  <span>OmniLead</span>
                </span>
              </>
            ) : (
              <>
                Daftarkan bisnis Anda bersama
                <span className="inline-flex items-center gap-2 whitespace-nowrap">
                  <LogoMark size={36} className="rounded-lg shadow-sm" />
                  <span>OmniLead</span>
                </span>
              </>
            )}
          </p>
        </div>
      </aside>
    </main>
  );
}
