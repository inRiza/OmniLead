"use client";

import { useState, type ComponentType, type ReactNode, type SVGProps } from "react";
import {
  ArrowRight,
  BellRing,
  Bot,
  Check,
  ClipboardCheck,
  Inbox,
  KeyRound,
  ListChecks,
  MessageCircleQuestion,
  Pause,
  Play,
  ShieldCheck,
  ToggleRight,
  UserRoundCheck,
  Users,
  Workflow,
  X,
} from "lucide-react";
import { LogoMark } from "@/components/brand/Logo";
import { ChannelIcon } from "@/components/primitives";
import type { Channel } from "@/lib/types";
import { channelLabel } from "@/lib/ui";
import { cn } from "@/lib/utils";

type Icon = ComponentType<SVGProps<SVGSVGElement>>;

const focusRing = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-accent";

/** Elemen yang muncul berurutan; `i` menentukan jeda. */
function Stagger({ i, children, className }: { i: number; children: ReactNode; className?: string }) {
  return (
    <div className={cn("rc-enter", className)} style={{ animationDelay: `${120 + i * 160}ms` }}>
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Kenapa: saklar chatbot biasa vs agen OmniLead                         */
/* ------------------------------------------------------------------ */

export function WhyToggle() {
  const [agent, setAgent] = useState(true);
  return (
    <div className="mx-auto max-w-4xl overflow-hidden rounded-3xl border border-rc-border bg-rc-surface shadow-[0_24px_60px_-36px_rgba(11,23,54,0.35)]">
      <div className="flex flex-col items-center gap-4 border-b border-rc-border bg-rc-bg px-6 py-5 sm:flex-row sm:justify-between">
        <div role="tablist" aria-label="Bandingkan" className="flex rounded-full border border-rc-border bg-rc-surface p-1">
          {[
            { v: false, label: "Chatbot biasa" },
            { v: true, label: "OmniLead" },
          ].map((o) => (
            <button
              key={o.label}
              type="button"
              role="tab"
              aria-selected={agent === o.v}
              onClick={() => setAgent(o.v)}
              className={cn(
                "min-h-9 cursor-pointer rounded-full px-4 text-sm font-medium transition-colors",
                focusRing,
                agent === o.v
                  ? o.v
                    ? "bg-rc-accent text-rc-accent-fg"
                    : "bg-rc-fg text-rc-primary-fg"
                  : "text-rc-fg-muted hover:text-rc-fg",
              )}
            >
              {o.label}
            </button>
          ))}
        </div>
        <p className="text-center text-sm text-rc-fg-muted sm:text-right">
          {agent
            ? "Paham maksud pelanggan, cek harga di katalog, siapkan balasan dan catatan, lalu tunggu persetujuan Anda."
            : "Hanya bisa menjawab lewat menu. Bingung kalau pertanyaannya di luar skrip."}
        </p>
      </div>

      <div key={String(agent)} className="flex min-h-[19rem] flex-col gap-3 p-6 text-sm sm:p-8">
        <Stagger i={0} className="max-w-[80%] self-end">
          <span className="block rounded-2xl rounded-tr-sm bg-rc-surface-hover px-4 py-2.5 text-rc-fg">
            ada paket buat 60 orang kantor kak? tgl 30
          </span>
        </Stagger>
        {agent ? (
          <>
            <Stagger i={1} className="flex max-w-[85%] items-end gap-2 self-start">
              <LogoMark size={26} accent />
              <span className="block rounded-2xl rounded-bl-sm bg-rc-navy px-4 py-2.5 text-white">
                Ada, Kak. Paket B nasi box komplit Rp35.000 per porsi, untuk 60 orang jadi Rp2.100.000. Tanggal 30 masih bisa.
              </span>
            </Stagger>
            <Stagger i={2} className="mt-3 grid gap-2 sm:grid-cols-3">
              {[
                ["Balasan siap", "menunggu persetujuan Anda"],
                ["Pelanggan dicatat", "skor 86 · Hot"],
                ["Pengingat dibuat", "besok pukul 10.00"],
              ].map(([t, d]) => (
                <span key={t} className="flex items-center gap-2 rounded-xl border border-rc-accent/25 bg-rc-accent-soft px-3 py-2.5">
                  <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-rc-accent text-rc-accent-fg">
                    <Check className="h-3 w-3" aria-hidden />
                  </span>
                  <span>
                    <span className="block font-medium text-rc-fg">{t}</span>
                    <span className="block text-rc-fg-muted">{d}</span>
                  </span>
                </span>
              ))}
            </Stagger>
          </>
        ) : (
          <>
            <Stagger i={1} className="flex max-w-[85%] items-end gap-2 self-start">
              <span className="inline-flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-lg bg-rc-surface-hover text-rc-fg-muted">
                <Bot className="h-4 w-4" aria-hidden />
              </span>
              <span className="block rounded-2xl rounded-bl-sm border border-rc-border px-4 py-2.5 text-rc-fg-muted">
                Maaf, saya tidak mengerti. Silakan pilih: 1. Menu 2. Promo
              </span>
            </Stagger>
            <Stagger i={2} className="max-w-[80%] self-end">
              <span className="block rounded-2xl rounded-tr-sm bg-rc-surface-hover px-4 py-2.5 text-rc-fg">buat 60 orang kak</span>
            </Stagger>
            <Stagger i={3} className="flex max-w-[85%] items-end gap-2 self-start">
              <span className="inline-flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-lg bg-rc-surface-hover text-rc-fg-muted">
                <Bot className="h-4 w-4" aria-hidden />
              </span>
              <span className="block rounded-2xl rounded-bl-sm border border-rc-border px-4 py-2.5 text-rc-fg-muted">
                Maaf, saya tidak mengerti. Silakan pilih: 1. Menu 2. Promo
              </span>
            </Stagger>
            <Stagger i={4} className="mt-3 self-center">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-rc-danger/10 px-3 py-1.5 font-medium text-rc-danger">
                <X className="h-4 w-4" aria-hidden /> Pelanggan pindah ke toko lain
              </span>
            </Stagger>
          </>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Kemampuan: daftar di kiri, panel ilustrasi di kanan                   */
/* ------------------------------------------------------------------ */

type Skill = { key: string; icon: Icon; title: string; body: string; tint: string; ink: string };

const SKILLS: Skill[] = [
  {
    key: "konteks",
    icon: MessageCircleQuestion,
    title: "Paham bahasa sehari-hari",
    body: "Mengerti singkatan dan typo, lalu mengambil detail penting seperti jumlah, tanggal, dan maksud pesan.",
    tint: "bg-[#e8eeff]",
    ink: "text-rc-accent",
  },
  {
    key: "cek",
    icon: ShieldCheck,
    title: "Mengecek sebelum menyarankan",
    body: "Harga harus sesuai katalog, diskon tidak melewati batas, dan data pelanggan lain tidak ikut terkirim.",
    tint: "bg-[#fff1d6]",
    ink: "text-amber-700",
  },
  {
    key: "profil",
    icon: Users,
    title: "Mengenali pelanggan yang sama",
    body: "Ani yang komentar di Instagram dan mengirim email dari kantor tercatat sebagai satu orang, lengkap dengan riwayatnya.",
    tint: "bg-[#e4e9f4]",
    ink: "text-rc-navy",
  },
  {
    key: "tindak",
    icon: BellRing,
    title: "Tidak lupa menindaklanjuti",
    body: "Menilai seberapa serius calon pembeli, lalu mengingatkan Anda untuk menghubungi lagi. Pengingat batal sendiri kalau pelanggan sudah membalas.",
    tint: "bg-[#e6f3ef]",
    ink: "text-emerald-700",
  },
];

function SkillVisual({ k }: { k: string }) {
  const card = "rounded-xl bg-white px-3.5 py-2.5 text-sm text-rc-fg shadow-[0_6px_18px_-10px_rgba(11,23,54,0.35)]";
  if (k === "konteks")
    return (
      <div className="flex w-full max-w-sm flex-col gap-4">
        <Stagger i={0}>
          <span className={cn(card, "block rounded-tl-sm")}>brp harga nasbox 30 org tgl 2 nov kak?</span>
        </Stagger>
        <div className="flex flex-wrap gap-2">
          {[
            ["Maksud", "tanya harga"],
            ["Jumlah", "30 porsi"],
            ["Tanggal", "2 Nov"],
            ["Prioritas", "sedang"],
          ].map(([l, v], i) => (
            <Stagger key={l} i={i + 1}>
              <span className="inline-flex flex-col rounded-xl bg-white px-3 py-2 shadow-[0_6px_18px_-10px_rgba(11,23,54,0.35)]">
                <span className="text-xs text-rc-fg-muted">{l}</span>
                <span className="text-sm font-medium text-rc-accent">{v}</span>
              </span>
            </Stagger>
          ))}
        </div>
      </div>
    );
  if (k === "cek")
    return (
      <div className="flex w-full max-w-sm flex-col gap-2">
        {["Harga sesuai katalog", "Diskon tidak lebih dari 5%", "Tidak memuat data pelanggan lain", "Masih dalam batas waktu balas"].map((c, i) => (
          <Stagger key={c} i={i}>
            <p className={cn(card, "flex items-center justify-between gap-3")}>
              {c}
              <span className="rc-pop inline-flex h-5 w-5 items-center justify-center rounded-full bg-amber-500 text-white" style={{ animationDelay: `${300 + i * 160}ms` }}>
                <Check className="h-3 w-3" aria-hidden />
              </span>
            </p>
          </Stagger>
        ))}
      </div>
    );
  if (k === "profil")
    return (
      <div className="flex items-center gap-3 sm:gap-5">
        <div className="flex flex-col gap-2.5">
          {(["instagram", "whatsapp", "email"] as Channel[]).map((c, i) => (
            <Stagger key={c} i={i}>
              <span className="flex items-center gap-2 rounded-xl bg-white px-2.5 py-2 shadow-[0_6px_18px_-10px_rgba(11,23,54,0.35)]">
                <ChannelIcon channel={c} />
                <span className="hidden text-sm sm:inline">{channelLabel[c]}</span>
              </span>
            </Stagger>
          ))}
        </div>
        <Stagger i={3}>
          <ArrowRight className="h-5 w-5 text-rc-navy/50" aria-hidden />
        </Stagger>
        <Stagger i={4}>
          <div className="rounded-2xl bg-white px-4 py-3 shadow-[0_10px_28px_-12px_rgba(11,23,54,0.45)]">
            <p className="font-medium">Ani · PT Maju Jaya</p>
            <p className="text-sm text-rc-fg-muted">3 kanal · 1 riwayat</p>
            <p className="mt-2 inline-flex rounded-full bg-rc-highlight px-2 py-0.5 text-xs font-medium text-rc-navy">Hot · 86</p>
          </div>
        </Stagger>
      </div>
    );
  return (
    <ol className="relative flex w-full max-w-sm flex-col gap-2 pl-5">
      <span aria-hidden className="absolute top-2 bottom-2 left-[7px] w-px bg-emerald-700/25" />
      {[
        ["Hari ini", "Penawaran disetujui dan terkirim"],
        ["Besok pukul 10.00", "Ingatkan kalau belum dibalas"],
        ["Kalau pelanggan membalas", "Pengingat dibatalkan otomatis"],
      ].map(([t, d], i) => (
        <Stagger key={t} i={i} className="relative">
          <span aria-hidden className="absolute top-3.5 -left-5 h-3.5 w-3.5 rounded-full border-2 border-white bg-emerald-600" />
          <p className={card}>
            <span className="font-medium">{t}</span>
            <span className="block text-rc-fg-muted">{d}</span>
          </p>
        </Stagger>
      ))}
    </ol>
  );
}

export function SkillsExplorer() {
  const [active, setActive] = useState(SKILLS[0].key);
  const sk = SKILLS.find((s) => s.key === active) ?? SKILLS[0];
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
      <div role="tablist" aria-label="Kemampuan AI" aria-orientation="vertical" className="flex flex-col gap-2">
        {SKILLS.map((s) => {
          const on = s.key === active;
          return (
            <button
              key={s.key}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => setActive(s.key)}
              onMouseEnter={() => setActive(s.key)}
              className={cn(
                "group cursor-pointer rounded-2xl border p-5 text-left transition-[background-color,border-color,box-shadow] duration-300",
                focusRing,
                on
                  ? "border-rc-border bg-rc-surface shadow-[0_14px_36px_-20px_rgba(11,23,54,0.4)]"
                  : "border-transparent hover:bg-rc-surface/60",
              )}
            >
              <span className="flex items-center gap-3">
                <span className={cn("inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl", s.tint, s.ink)}>
                  <s.icon className="h-5 w-5" aria-hidden />
                </span>
                <span className={cn("text-lg font-semibold tracking-tight", on ? s.ink : "text-rc-fg")}>{s.title}</span>
              </span>
              <span
                className={cn(
                  "grid transition-[grid-template-rows,opacity] duration-300",
                  on ? "mt-2 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                )}
              >
                <span className="overflow-hidden pl-[3.25rem] text-rc-fg-muted">{s.body}</span>
              </span>
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        aria-label={sk.title}
        className={cn(
          "relative flex min-h-[22rem] items-center justify-center overflow-hidden rounded-3xl p-8 transition-colors duration-500",
          sk.tint,
        )}
      >
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{ backgroundImage: "radial-gradient(rgba(11,23,54,0.18) 1px, transparent 1px)", backgroundSize: "20px 20px" }}
        />
        <div key={sk.key} className="relative flex w-full justify-center">
          <SkillVisual k={sk.key} />
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Fitur: tab yang mengganti mockup                                     */
/* ------------------------------------------------------------------ */

type Feature = { key: string; icon: Icon; title: string; body: string };

const FEATURES: Feature[] = [
  { key: "workspace", icon: Inbox, title: "Kotak masuk", body: "Pesan dari semua kanal, diurutkan dari yang paling mendesak." },
  { key: "antrean", icon: ClipboardCheck, title: "Persetujuan", body: "Setujui, ubah, atau tolak tiap balasan. Alasan penolakan dipakai untuk balasan berikutnya." },
  { key: "jejak", icon: Workflow, title: "Langkah AI", body: "Lihat apa saja yang dicek AI sebelum menyarankan balasan." },
  { key: "profil", icon: UserRoundCheck, title: "Profil pelanggan", body: "Riwayat chat dari semua kanal, status, dan skor beserta alasannya." },
];

function MockFrame({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-rc-border bg-rc-surface shadow-[0_24px_60px_-30px_rgba(11,23,54,0.35)]">
      <div className="flex items-center gap-2 border-b border-rc-border bg-rc-bg px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
        <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
        <span className="ml-3 text-sm text-rc-fg-muted">{title}</span>
      </div>
      <div className="min-h-[21rem] p-4 sm:p-5">{children}</div>
    </div>
  );
}

function MockWorkspace() {
  const rows: { channel: Channel; who: string; msg: string; tag: string; tone: string }[] = [
    { channel: "instagram", who: "Ani · PT Maju Jaya", msg: "Kak, bisa buat 60 orang tgl 30? harga?", tag: "Hot", tone: "bg-rc-highlight text-rc-navy" },
    { channel: "whatsapp", who: "Budi", msg: "salah kirim menu, minta refund ya", tag: "Komplain", tone: "bg-rc-danger text-white" },
    { channel: "email", who: "PT Nusa Corp", msg: "Penawaran katering 100 pax", tag: "Warm", tone: "bg-rc-accent-soft text-rc-accent" },
    { channel: "tiktok", who: "@sari.eats", msg: "hampers premium 10 box brp kak?", tag: "Warm", tone: "bg-rc-accent-soft text-rc-accent" },
  ];
  return (
    <div className="flex flex-col gap-2">
      {rows.map((r, i) => (
        <Stagger key={r.who} i={i}>
          <div className="flex items-center gap-3 rounded-xl border border-rc-border px-3 py-3 transition-colors hover:bg-rc-surface-hover">
            <ChannelIcon channel={r.channel} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{r.who}</p>
              <p className="truncate text-sm text-rc-fg-muted">{r.msg}</p>
            </div>
            <span className={cn("rounded-full px-2.5 py-0.5 text-sm font-medium", r.tone)}>{r.tag}</span>
          </div>
        </Stagger>
      ))}
    </div>
  );
}

function MockQueue() {
  const [state, setState] = useState<Record<number, "ok" | "no">>({});
  const items = [
    { kind: "DM Instagram", text: "Paket B Rp35.000 × 60 porsi = Rp2.100.000. Tanggal 30 masih bisa, Kak." },
    { kind: "Balasan WhatsApp", text: "Mohon maaf atas kesalahan menunya, Kak. Boleh kami minta nomor pesanannya?" },
    { kind: "Catatan pelanggan", text: "Ani · status: tertarik → negosiasi" },
  ];
  return (
    <div className="flex flex-col gap-2">
      {items.map((it, i) => (
        <Stagger key={it.kind} i={i}>
          <div
            className={cn(
              "rounded-xl border p-3.5 transition-[border-color,background-color,opacity]",
              state[i] === "ok" ? "border-rc-accent bg-rc-accent-soft/50" : "border-rc-border",
              state[i] === "no" && "opacity-50",
            )}
          >
            <p className="flex items-center justify-between gap-2 text-sm font-medium">
              {it.kind}
              <span className="inline-flex items-center gap-1 text-sm font-normal text-rc-fg-muted">
                <ShieldCheck className="h-3.5 w-3.5 text-rc-accent" aria-hidden /> Lolos pengecekan
              </span>
            </p>
            <p className="mt-1 text-sm text-rc-fg-muted">{it.text}</p>
            <div className="mt-2.5 flex min-h-8 items-center gap-1.5">
              {state[i] ? (
                <span className={cn("rc-pop text-sm font-medium", state[i] === "ok" ? "text-rc-accent" : "text-rc-fg-muted")}>
                  {state[i] === "ok" ? "Disetujui · pesan dikirim" : "Ditolak · alasan dicatat"}
                </span>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={() => setState((s) => ({ ...s, [i]: "ok" }))}
                    className={cn("inline-flex min-h-8 cursor-pointer items-center gap-1 rounded-full bg-rc-fg px-3.5 text-sm font-medium text-rc-primary-fg hover:bg-rc-fg/85", focusRing)}
                  >
                    <Check className="h-3.5 w-3.5" aria-hidden /> Setujui
                  </button>
                  <button
                    type="button"
                    onClick={() => setState((s) => ({ ...s, [i]: "no" }))}
                    className={cn("inline-flex min-h-8 cursor-pointer items-center gap-1 rounded-full px-3 text-sm text-rc-fg-muted hover:bg-rc-surface-hover hover:text-rc-fg", focusRing)}
                  >
                    <X className="h-3.5 w-3.5" aria-hidden /> Tolak
                  </button>
                </>
              )}
            </div>
          </div>
        </Stagger>
      ))}
    </div>
  );
}

function MockTrace() {
  const steps = [
    ["Membaca riwayat pelanggan", "Kemarin Ani bertanya soal katering kantor lewat email"],
    ["Mencari paket di katalog", "Paket B Rp35.000 per porsi, minimal 30 porsi"],
    ["Mengecek batas waktu balas", "Instagram: masih bisa dibalas"],
    ["Menilai calon pembeli", "Skor 86 (Hot): pesanan besar, acara sebentar lagi"],
    ["Menyiapkan balasan", "Balasan komentar dan DM siap diperiksa"],
  ];
  return (
    <div>
      <p className="text-sm text-rc-fg-muted">Tugas</p>
      <p className="font-medium">Membalas pertanyaan harga dari Ani di Instagram</p>
      <ol className="mt-4 flex flex-col gap-2">
        {steps.map(([tool, res], i) => (
          <Stagger key={tool} i={i}>
            <li className="flex items-start gap-3 rounded-xl border border-rc-border px-3 py-2.5">
              <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-rc-navy text-xs font-medium text-white">
                {i + 1}
              </span>
              <span className="min-w-0 text-sm">
                <span className="font-medium text-rc-fg">{tool}</span>
                <span className="block text-rc-fg-muted">{res}</span>
              </span>
            </li>
          </Stagger>
        ))}
      </ol>
    </div>
  );
}

function MockProfile() {
  const events: { channel: Channel; text: string; when: string }[] = [
    { channel: "email", text: "info katering kantor", when: "Kemarin" },
    { channel: "instagram", text: "Kak, bisa buat 60 orang tgl 30? harga?", when: "Hari ini 09.12" },
    { channel: "whatsapp", text: "Oke kak, saya konfirmasi ke atasan dulu", when: "Hari ini 10.40" },
  ];
  return (
    <div className="grid gap-4 sm:grid-cols-[13rem_minmax(0,1fr)]">
      <Stagger i={0}>
        <div className="rounded-xl bg-rc-bg p-4">
          <p className="font-semibold">Ani</p>
          <p className="text-sm text-rc-fg-muted">PT Maju Jaya</p>
          <p className="mt-3 text-4xl font-semibold tracking-tight">86</p>
          <p className="inline-flex rounded-full bg-rc-highlight px-2 py-0.5 text-xs font-medium text-rc-navy">Hot</p>
          <p className="mt-3 text-sm text-rc-fg-muted">Pesanan sekitar Rp2,1 juta, acara 9 hari lagi, pelanggan perusahaan.</p>
        </div>
      </Stagger>
      <ol className="flex flex-col gap-2">
        {events.map((e, i) => (
          <Stagger key={e.when} i={i + 1}>
            <li className="flex items-start gap-3 rounded-xl border border-rc-border px-3 py-2.5">
              <ChannelIcon channel={e.channel} />
              <span className="min-w-0 text-sm">
                <span className="block text-rc-fg">{e.text}</span>
                <span className="block text-rc-fg-muted">{e.when}</span>
              </span>
            </li>
          </Stagger>
        ))}
      </ol>
    </div>
  );
}

export function FeatureTabs() {
  const [active, setActive] = useState(FEATURES[0].key);
  const f = FEATURES.find((x) => x.key === active) ?? FEATURES[0];
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
      <div role="tablist" aria-label="Fitur" className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
        {FEATURES.map((x) => {
          const on = x.key === active;
          return (
            <button
              key={x.key}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => setActive(x.key)}
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-2xl border p-4 text-left transition-[background-color,border-color,box-shadow] duration-300",
                focusRing,
                on
                  ? "border-rc-accent bg-rc-surface shadow-[0_14px_36px_-20px_rgba(47,91,234,0.55)]"
                  : "border-rc-border bg-rc-surface/70 hover:border-rc-border-strong hover:bg-rc-surface",
              )}
            >
              <span
                className={cn(
                  "inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-colors",
                  on ? "bg-rc-accent text-rc-accent-fg" : "bg-rc-accent-soft text-rc-accent",
                )}
              >
                <x.icon className="h-5 w-5" aria-hidden />
              </span>
              <span>
                <span className="block font-semibold">{x.title}</span>
                <span className="mt-0.5 block text-sm text-rc-fg-muted">{x.body}</span>
              </span>
            </button>
          );
        })}
      </div>
      <div role="tabpanel" aria-label={f.title} key={f.key}>
        <MockFrame title={f.title}>
          {f.key === "workspace" && <MockWorkspace />}
          {f.key === "antrean" && <MockQueue />}
          {f.key === "jejak" && <MockTrace />}
          {f.key === "profil" && <MockProfile />}
        </MockFrame>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Kendali: kartu yang bisa dicoba, di atas pita navy                    */
/* ------------------------------------------------------------------ */

const darkCard =
  "flex flex-col rounded-3xl border border-white/10 bg-white/[0.04] p-6 transition-colors duration-300 hover:border-white/20 hover:bg-white/[0.07] sm:p-8";

function DarkHead({ icon: I, title, body }: { icon: Icon; title: string; body: string }) {
  return (
    <>
      <span className="inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-rc-highlight text-rc-navy">
        <I className="h-5 w-5" aria-hidden />
      </span>
      <h3 className="mt-5 text-xl font-semibold tracking-tight text-white">{title}</h3>
      <p className="mt-1.5 text-[#aab4cc]">{body}</p>
    </>
  );
}

function Switch({ on, onChange, label }: { on: boolean; onChange: () => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={onChange}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-highlight",
        on ? "bg-[#4f7bff]" : "bg-white/20",
      )}
    >
      <span className={cn("inline-block h-5 w-5 rounded-full bg-white shadow transition-transform", on ? "translate-x-[22px]" : "translate-x-0.5")} />
    </button>
  );
}

export function ControlPanel() {
  const [paused, setPaused] = useState(false);
  const [channels, setChannels] = useState<Record<string, boolean>>({ whatsapp: true, instagram: true, email: false });
  const now = paused ? "Semua pengiriman dihentikan" : "AI aktif · 3 balasan menunggu";

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className={darkCard}>
        <DarkHead icon={KeyRound} title="AI tidak bisa mengirim sendiri" body="AI hanya menyiapkan. Pesan baru dikirim setelah Anda setuju." />
        <div className="mt-6 flex flex-wrap items-center gap-2 text-sm">
          {["AI menyiapkan", "Anda setuju", "Pesan dikirim", "Pelanggan"].map((s, i, arr) => (
            <span key={s} className="inline-flex items-center gap-2">
              <span
                className={cn(
                  "rounded-full px-3 py-1",
                  s === "Anda setuju" ? "bg-rc-highlight font-medium text-rc-navy" : "bg-white/10 text-white",
                )}
              >
                {s}
              </span>
              {i < arr.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-white/40" aria-hidden />}
            </span>
          ))}
        </div>
      </div>

      <div className={darkCard}>
        <DarkHead icon={Pause} title="Tombol jeda" body="Satu klik menghentikan semua pengiriman, termasuk yang sudah disetujui." />
        <div
          className={cn(
            "mt-6 flex items-center justify-between gap-3 rounded-2xl px-4 py-3 transition-colors",
            paused ? "bg-rc-danger/25" : "bg-white/[0.06]",
          )}
          aria-live="polite"
        >
          <span className="flex items-center gap-2 text-sm text-white">
            <span className={cn("h-2 w-2 rounded-full", paused ? "bg-[#ff8a8a]" : "bg-[#4ade80]")} />
            {now}
          </span>
          <button
            type="button"
            onClick={() => setPaused((p) => !p)}
            className={cn(
              "inline-flex min-h-9 cursor-pointer items-center gap-1.5 rounded-full px-4 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-highlight",
              paused ? "bg-white text-rc-navy" : "bg-rc-danger text-white hover:bg-rc-danger/90",
            )}
          >
            {paused ? <Play className="h-4 w-4" aria-hidden /> : <Pause className="h-4 w-4" aria-hidden />}
            {paused ? "Lanjutkan" : "Jeda AI"}
          </button>
        </div>
      </div>

      <div className={darkCard}>
        <DarkHead icon={ToggleRight} title="Saklar per kanal" body="Kanal yang dimatikan masuk mode uji: balasan tetap disiapkan, tapi tidak benar-benar dikirim." />
        <ul className="mt-6 flex flex-col gap-2">
          {(["whatsapp", "instagram", "email"] as Channel[]).map((c) => (
            <li key={c} className="flex items-center justify-between gap-3 rounded-2xl bg-white/[0.06] px-4 py-2.5">
              <span className="flex items-center gap-3 text-sm text-white">
                <ChannelIcon channel={c} />
                {channelLabel[c]}
                <span className="text-[#7d89a6]">{channels[c] ? "aktif" : "mode uji"}</span>
              </span>
              <Switch
                on={channels[c]}
                label={`Pengiriman lewat ${channelLabel[c]}`}
                onChange={() => setChannels((s) => ({ ...s, [c]: !s[c] }))}
              />
            </li>
          ))}
        </ul>
      </div>

      <div className={darkCard}>
        <DarkHead icon={ListChecks} title="Riwayat tindakan" body="Siapa menyetujui apa, kapan, dan lewat kanal mana. Semua tercatat." />
        <ul className="mt-6 flex flex-col divide-y divide-white/10 rounded-2xl bg-white/[0.06] text-sm">
          {[
            ...(paused ? [["kini", "Bu Rina menjeda AI", "jeda"]] : []),
            ["10.42", "Bu Rina menyetujui DM ke Ani", "terkirim"],
            ["10.40", "Permintaan diskon 70% ditahan", "ditahan"],
            ["10.31", "Profil Ani digabung (Instagram + email)", "dicatat"],
          ]
            .slice(0, 3)
            .map(([t, d, s]) => (
              <li key={t + d} className="flex items-center justify-between gap-3 px-4 py-2.5">
                <span className="min-w-0 text-white">
                  <span className="mr-2 font-mono text-[#7d89a6]">{t}</span>
                  {d}
                </span>
                <span
                  className={cn(
                    "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
                    s === "ditahan" || s === "jeda" ? "bg-rc-highlight text-rc-navy" : "bg-white/10 text-white",
                  )}
                >
                  {s}
                </span>
              </li>
            ))}
        </ul>
      </div>
    </div>
  );
}
