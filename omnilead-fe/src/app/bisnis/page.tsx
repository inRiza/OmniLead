"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight, Building2, Check, Plus } from "lucide-react";
import { api, setActiveWorkspace, type Connection } from "@/lib/api";
import type { Channel } from "@/lib/types";
import { channelLabel, cn } from "@/lib/ui";
import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/action/button";
import { ChannelIcon } from "@/components/primitives";
import { Select } from "@/components/ui/select";
import { AccountProvider, useAccount } from "@/components/dashboard/AccountProvider";

const CATEGORIES = ["Katering & makanan", "Fashion & hijab", "Hampers & hadiah", "Kecantikan", "Jasa", "Lainnya"] as const;
type Category = (typeof CATEGORIES)[number];

const CHANNEL_NEEDS: { channel: Channel; provider: string; need: string }[] = [
  { channel: "whatsapp", provider: "whatsapp", need: "Nomor WhatsApp Business untuk membaca dan membalas chat pelanggan." },
  { channel: "instagram", provider: "instagram", need: "Akun Instagram Business atau Creator untuk komentar dan DM." },
  { channel: "facebook", provider: "facebook", need: "Facebook Page bisnis untuk komentar post dan Messenger." },
  { channel: "email", provider: "gmail", need: "Akun Gmail bisnis untuk membaca dan membalas email penawaran." },
];

const input =
  "mt-1.5 w-full rounded-md border border-rc-border bg-rc-surface px-3 py-2.5 text-sm text-rc-fg outline-none placeholder:text-rc-fg-subtle focus:border-rc-accent focus:ring-2 focus:ring-rc-accent/15";

export default function BusinessPage() {
  return (
    <AccountProvider>
      <div className="rc-brand rc-app min-h-dvh bg-rc-bg text-rc-fg">
        <header className="mx-auto flex h-16 w-full max-w-5xl items-center px-5">
          <Link href="/">
            <Logo />
          </Link>
        </header>
        <main className="mx-auto w-full max-w-5xl px-5 pt-6 pb-16">
          <BusinessFlow />
        </main>
      </div>
    </AccountProvider>
  );
}

function BusinessFlow() {
  const { session } = useAccount();
  const user = session.user;
  const spaces = user?.workspaces ?? (user ? [{ id: user.workspace_id, name: user.business }] : []);
  const [mode, setMode] = useState<"pick" | "create" | "connect">("pick");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<string>("");

  useEffect(() => {
    const t = setTimeout(() => {
      const q = new URLSearchParams(window.location.search);
      if (q.get("baru") === "1") setMode("create");
    }, 0);
    return () => clearTimeout(t);
  }, []);

  async function enter(id: string) {
    setBusy(id);
    setError("");
    try {
      if (id !== user?.workspace_id) await api.selectWorkspace(id);
      window.location.replace("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Bisnis belum bisa dibuka");
      setBusy(null);
    }
  }

  if (mode === "create")
    return (
      <CreateForm
        onBack={spaces.length ? () => setMode("pick") : undefined}
        onCreated={(name) => {
          setCreated(name);
          setMode("connect");
        }}
      />
    );
  if (mode === "connect") return <ConnectStep business={created} />;

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">Pilih bisnis</h1>
      <p className="mt-1 text-sm text-rc-fg-muted">
        Halo{user?.name ? `, ${user.name.split(" ")[0]}` : ""}. Setiap bisnis punya pelanggan, kanal, dan pengetahuan agen sendiri. Jumlah bisnis mengikuti paket langganan Anda.
      </p>
      {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {spaces.map((w) => {
          const current = w.id === user?.workspace_id;
          return (
            <button
              key={w.id}
              type="button"
              disabled={busy !== null}
              onClick={() => void enter(w.id)}
              className={cn(
                "group flex cursor-pointer flex-col rounded-xl border bg-rc-surface p-5 text-left transition-colors disabled:cursor-wait",
                current ? "border-rc-accent/50" : "border-rc-border hover:border-rc-accent/50",
              )}
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-rc-accent-soft text-rc-accent">
                <Building2 className="h-5 w-5" aria-hidden />
              </span>
              <span className="mt-4 text-base font-semibold text-rc-fg">{w.name}</span>
              <span className="mt-1 text-xs text-rc-fg-muted">{current ? "Terakhir dibuka" : "Bisnis"}</span>
              <span className="mt-5 inline-flex items-center gap-1 text-sm font-medium text-rc-accent">
                {busy === w.id ? "Membuka…" : "Masuk"}
                <ArrowRight aria-hidden className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </span>
            </button>
          );
        })}
        <button
          type="button"
          onClick={() => setMode("create")}
          className="flex min-h-48 cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-rc-border-strong bg-transparent p-5 text-rc-fg-muted transition-colors hover:border-rc-accent hover:text-rc-accent"
        >
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-rc-surface">
            <Plus className="h-5 w-5" aria-hidden />
          </span>
          <span className="text-sm font-medium">Buat bisnis baru</span>
        </button>
      </div>
    </div>
  );
}

function Steps({ step }: { step: 1 | 2 }) {
  return (
    <ol className="mb-8 flex items-center gap-3 text-sm">
      {["Profil bisnis", "Kanal untuk agen"].map((label, i) => {
        const n = i + 1;
        const done = n < step;
        const on = n === step;
        return (
          <li key={label} className="flex items-center gap-3">
            {i > 0 && <span className="h-px w-8 bg-rc-border-strong" />}
            <span className={cn("flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold", done || on ? "bg-rc-accent text-white" : "bg-rc-surface-hover text-rc-fg-muted")}>
              {done ? <Check className="h-3.5 w-3.5" aria-hidden /> : n}
            </span>
            <span className={on ? "font-medium text-rc-fg" : "text-rc-fg-muted"}>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

function CreateForm({ onBack, onCreated }: { onBack?: () => void; onCreated: (name: string) => void }) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState<Category | null>(null);
  const [about, setAbout] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy || !name.trim()) return;
    setBusy(true);
    setError("");
    try {
      const ws = await api.addWorkspace(name.trim());
      await api.selectWorkspace(ws.id);
      setActiveWorkspace(ws.id);
      if (about.trim() || category) {
        await api.saveKnowledge({
          name: "Profil bisnis",
          content: [category ? `Jenis usaha: ${category}` : "", about.trim()].filter(Boolean).join("\n\n"),
          products: [],
        });
      }
      onCreated(ws.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bisnis belum dapat dibuat");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      {onBack && (
        <button type="button" onClick={onBack} className="mb-6 inline-flex cursor-pointer items-center gap-1.5 text-sm text-rc-fg-muted hover:text-rc-fg">
          <ArrowLeft className="h-4 w-4" aria-hidden /> Kembali ke daftar bisnis
        </button>
      )}
      <Steps step={1} />
      <h1 className="text-2xl font-semibold tracking-tight">Buat bisnis baru</h1>
      <p className="mt-1 text-sm text-rc-fg-muted">Informasi ini dipakai agen untuk mengenali bisnis Anda saat membalas pelanggan.</p>
      <form onSubmit={submit} className="mt-8 flex flex-col gap-5 rounded-xl border border-rc-border bg-rc-surface p-6">
        <label className="block text-sm font-medium">
          Nama bisnis
          <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} placeholder="Contoh: Dapur Bunda Catering" className={input} />
        </label>
        <div className="text-sm font-medium">
          Jenis usaha
          <Select className="mt-1.5" label="Jenis usaha" placeholder="Pilih jenis usaha" value={category} onChange={setCategory} options={CATEGORIES.map((c) => ({ value: c, label: c }))} />
        </div>
        <label className="block text-sm font-medium">
          Tentang bisnis <span className="font-normal text-rc-fg-muted">(opsional)</span>
          <textarea
            value={about}
            onChange={(e) => setAbout(e.target.value)}
            rows={4}
            maxLength={2000}
            placeholder="Produk utama, area pengiriman, jam operasional, dan cara pemesanan."
            className={input}
          />
        </label>
        {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
        <div className="flex justify-end border-t border-rc-border pt-5">
          <Button purpose="action" type="submit" style="primary" className="min-h-10 gap-1.5 px-5" disabled={busy || !name.trim()}>
            {busy ? "Membuat bisnis…" : "Lanjut ke kanal"}
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Button>
        </div>
      </form>
    </div>
  );
}

function ConnectStep({ business }: { business: string }) {
  const [connections, setConnections] = useState<Connection[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      setConnections(await api.connections());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Status kanal belum bisa dimuat");
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => void load(), 0);
    return () => clearTimeout(t);
  }, [load]);

  async function connect(provider: string) {
    setBusy(provider);
    setError("");
    try {
      const start = await api.connect(provider);
      if (start.mode === "redirect") {
        window.location.assign(start.url);
        return;
      }
      window.location.replace("/dashboard/integrasi");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Kanal belum bisa dihubungkan");
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Steps step={2} />
      <h1 className="text-2xl font-semibold tracking-tight">Hubungkan kanal untuk agen</h1>
      <p className="mt-1 text-sm text-rc-fg-muted">
        <span className="font-medium text-rc-fg">{business}</span> sudah dibuat. Hubungkan kanal tempat pelanggan menghubungi Anda, agar agen bisa membaca dan membalas pesan.
      </p>
      {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
      <div className="mt-8 divide-y divide-rc-border rounded-xl border border-rc-border bg-rc-surface">
        {CHANNEL_NEEDS.map((c) => {
          const conn = connections.find((x) => x.provider === c.provider);
          const connected = conn?.status === "connected";
          const available = conn ? conn.configured : true;
          return (
            <div key={c.channel} className="flex items-center gap-4 p-5">
              <ChannelIcon channel={c.channel} size="md" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-rc-fg">{channelLabel[c.channel]}</p>
                <p className="mt-0.5 text-sm text-rc-fg-muted">{connected ? conn?.label || "Terhubung" : c.need}</p>
              </div>
              {connected ? (
                <span className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-700">
                  <Check className="h-3.5 w-3.5" aria-hidden /> Terhubung
                </span>
              ) : (
                <Button purpose="action" disabled={busy !== null || !available} onClick={() => void connect(c.provider)} title={available ? undefined : "Belum dikonfigurasi di server"}>
                  {busy === c.provider ? "Menghubungkan…" : available ? "Hubungkan" : "Belum tersedia"}
                </Button>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-rc-fg-muted">Bisa juga diatur nanti dari menu Integrasi.</p>
        <Button purpose="action" style="primary" className="min-h-10 gap-1.5 px-5" onClick={() => window.location.replace("/dashboard")}>
          Masuk ke dashboard
          <ArrowRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
