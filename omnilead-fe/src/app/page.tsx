import type { ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ChevronDown } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { HeroContours } from "@/components/brand/HeroContours";
import { AnnouncementBar, HeroStage, LandingHeader, Reveal } from "@/components/landing/Interactive";
import { SkillsExplorer, WhyToggle } from "@/components/landing/Sections";
import { cn } from "@/lib/utils";

const INTEGRATIONS = [
  { slug: "whatsapp", name: "WhatsApp" },
  { slug: "gmail", name: "Gmail" },
  { slug: "instagram", name: "Instagram" },
  { slug: "facebook", name: "Facebook" },
];

const FAQ: { q: string; a: ReactNode }[] = [
  {
    q: "Untuk usaha seperti apa OmniLead dibuat?",
    a: "Untuk UMKM yang menerima pesanan dari banyak kanal sekaligus, seperti katering, hampers, dan toko fashion. Cukup isi katalog sesuai jenis usaha Anda.",
  },
  {
    q: "Apakah AI mengirim pesan sendiri?",
    a: "Ya, dalam mode percaya penuh agen membalas otomatis dari katalog. Guard tetap menahan harga di luar katalog atau diskon berlebihan, dan semua pengiriman bisa dihentikan dengan tombol jeda.",
  },
  {
    q: "Dari mana AI tahu harga dan stok?",
    a: "Dari katalog dan daftar tanya-jawab yang Anda isi. Kalau balasan menyebut harga di luar katalog atau diskon melebihi batas, balasan itu ditahan.",
  },
  {
    q: "Kanal apa saja yang bisa dipakai?",
    a: "WhatsApp, Instagram (komentar dan DM), Facebook (komentar Page dan Messenger), dan Gmail. Hubungkan akun bisnis lewat halaman Integrasi.",
  },
  {
    q: "Apakah AI paham bahasa chat sehari-hari?",
    a: "Ya. Singkatan dan typo seperti \"brp harga nasbox 30 org kak?\" tetap dipahami.",
  },
  {
    q: "Bagaimana kalau balasan dari AI kurang tepat?",
    a: "Perbaiki di Workspace atau Audit, lalu beri masukan. Agen memakai umpan balik itu untuk balasan berikutnya. Mode izin juga bisa diperketat di Pengaturan.",
  },
];

const HERO_MAIN = [
  { label: "Beranda", active: true },
  { label: "Workspace" },
  { label: "Agen" },
  { label: "Lead" },
  { label: "Integrasi" },
  { label: "Audit" },
] as const;

const HERO_SECONDARY = ["Pengetahuan & Tone", "Pengaturan Agen"] as const;

const HERO_STATS = [
  { label: "Pesan masuk", value: "128" },
  { label: "Perlu dibalas", value: "12" },
  { label: "Lead prioritas tinggi", value: "7" },
  { label: "Closing", value: "9" },
] as const;

const HERO_VOLUME = [
  [18, 12, 8, 6],
  [22, 10, 9, 5],
  [14, 16, 7, 4],
  [28, 14, 11, 8],
  [20, 11, 9, 6],
  [25, 13, 10, 7],
  [30, 15, 12, 9],
] as const;

const HERO_REPLIES = [
  { name: "Ani Rahma", score: "Hot", text: "Kak, harga nasi box 50 pax buat Sabtu berapa?", ago: "12 mnt" },
  { name: "Dinda", score: "Warm", text: "Reseller, mau ambil hijab 20 pcs brp?", ago: "34 mnt" },
  { name: "Sari Wulandari", score: "Warm", text: "Hampers premium 10 box brp kak?", ago: "1 jam" },
] as const;

const HERO_LOGS = [
  { event: "Balasan terkirim", detail: "WhatsApp · Ani Rahma", tone: "green" as const, ago: "8 mnt" },
  { event: "Lead dinilai Hot", detail: "Skor 86 · acara 5 hari lagi", tone: "blue" as const, ago: "15 mnt" },
  { event: "Usulan disiapkan", detail: "Instagram · komentar harga", tone: "blue" as const, ago: "28 mnt" },
] as const;

const STACK = ["#0144f5", "#3d6dff", "#7d9dff", "#bccdff"] as const;

function HeroDashboard() {
  return (
    <div
      aria-hidden
      className="flex h-[22rem] overflow-hidden rounded-t-lg border border-b-0 border-rc-border bg-rc-bg sm:h-[30rem] lg:h-[36rem]"
    >
      <aside className="flex w-44 shrink-0 flex-col border-r border-rc-border bg-rc-surface sm:w-56">
        <div className="flex h-14 items-center justify-between border-b border-rc-border px-4">
          <Logo />
          <span className="hidden h-7 w-7 items-center justify-center rounded-md text-rc-fg-muted sm:inline-flex">
            <span className="h-3.5 w-3.5 rounded-sm border border-current" />
          </span>
        </div>
        <nav className="flex flex-1 flex-col gap-5 px-3 py-3">
          <div className="flex flex-col gap-0.5">
            {HERO_MAIN.map((item) => (
              <span
                key={item.label}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-xs sm:text-sm",
                  item.active ? "bg-rc-accent-soft font-semibold text-rc-accent" : "text-rc-fg-muted",
                )}
              >
                <span className={cn("h-4 w-4 shrink-0 rounded-sm", item.active ? "bg-rc-accent/40" : "bg-rc-border")} />
                {item.label}
              </span>
            ))}
          </div>
          <div>
            <p className="px-2.5 pb-1 text-[10px] font-semibold tracking-wide text-rc-fg-subtle uppercase sm:text-xs">Pengaturan</p>
            <div className="flex flex-col gap-0.5">
              {HERO_SECONDARY.map((label) => (
                <span key={label} className="flex items-center gap-2.5 rounded-md px-2.5 py-2 text-xs text-rc-fg-muted sm:text-sm">
                  <span className="h-4 w-4 shrink-0 rounded-sm bg-rc-border" />
                  {label}
                </span>
              ))}
            </div>
          </div>
        </nav>
        <div className="flex items-center gap-2.5 border-t border-rc-border px-4 py-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-rc-accent text-xs font-semibold text-rc-accent-fg">RI</span>
          <span className="min-w-0 leading-tight">
            <span className="block truncate text-sm font-medium text-rc-fg">Rina</span>
            <span className="block truncate text-xs text-rc-fg-muted">Dapur Bu Rina</span>
          </span>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-14 shrink-0 items-center border-b border-rc-border bg-rc-bg px-5">
          <p className="text-lg font-semibold tracking-tight text-rc-fg">Beranda</p>
        </div>
        <div className="rc-scrollbar flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4 pb-6 sm:gap-5 sm:p-5 md:p-7">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-base font-semibold text-rc-fg sm:text-xl">Halo, Rina</p>
              <p className="mt-1 text-xs text-rc-fg-muted sm:text-sm">Ringkasan 7 hari terakhir dari semua kanal.</p>
            </div>
            <span className="inline-flex h-9 items-center rounded-md border border-rc-border bg-rc-surface px-3 text-xs font-medium text-rc-fg sm:text-sm">
              7 hari terakhir
              <ChevronDown className="ml-2 h-3.5 w-3.5 text-rc-fg-muted" aria-hidden />
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {HERO_STATS.map((s) => (
              <div key={s.label} className="rounded-xl border border-rc-border bg-rc-surface p-4 sm:p-5">
                <p className="truncate text-xs font-medium text-rc-fg-muted sm:text-sm">{s.label}</p>
                <p className="mt-2 text-2xl font-semibold tracking-tight text-rc-fg tabular-nums sm:mt-3 sm:text-3xl">{s.value}</p>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-rc-border bg-rc-surface p-4 sm:p-5">
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="text-sm font-semibold text-rc-fg sm:text-base">Volume pesan per kanal</p>
              <p className="text-xs text-rc-fg-muted sm:text-sm">128 pesan</p>
            </div>
            <div className="flex h-28 items-end gap-2 sm:h-36 sm:gap-3">
              {HERO_VOLUME.map((stack, i) => {
                const total = stack.reduce((a, b) => a + b, 0);
                return (
                  <span key={i} className="flex flex-1 flex-col justify-end" style={{ height: `${(total / 70) * 100}%` }}>
                    {stack.map((v, j) => (
                      <span
                        key={j}
                        className={cn("w-full", j === stack.length - 1 ? "rounded-t-sm" : "")}
                        style={{ height: `${(v / total) * 100}%`, backgroundColor: STACK[j] }}
                      />
                    ))}
                  </span>
                );
              })}
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-rc-fg-muted sm:text-xs">
              {["WhatsApp", "Instagram", "Facebook", "Email"].map((label, i) => (
                <span key={label} className="inline-flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: STACK[i] }} />
                  {label}
                </span>
              ))}
            </div>
          </div>

          <div className="hidden rounded-xl border border-rc-border bg-rc-surface p-5 lg:block">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-base font-semibold text-rc-fg">Potensi closing</p>
                <p className="text-sm text-rc-fg-muted">Lead baru dibanding lead yang berhasil closing.</p>
              </div>
              <dl className="flex gap-6 text-right">
                {[
                  ["Lead baru", "24"],
                  ["Closing", "9"],
                  ["Konversi", "38%"],
                  ["Dalam proses", "11"],
                ].map(([k, v]) => (
                  <div key={k}>
                    <dt className="text-xs text-rc-fg-muted">{k}</dt>
                    <dd className="text-lg font-semibold text-rc-fg tabular-nums">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <svg viewBox="0 0 400 96" className="h-24 w-full" preserveAspectRatio="none">
              <path d="M0 70 C40 62, 80 55, 120 48 S200 30, 240 34 S320 50, 400 22" fill="none" stroke="#7d9dff" strokeWidth="2" />
              <path d="M0 82 C40 78, 80 74, 120 68 S200 52, 240 56 S320 64, 400 40" fill="none" stroke="#0144f5" strokeWidth="2.5" />
            </svg>
          </div>

          <div className="hidden grid-cols-2 gap-5 lg:grid">
            <div className="rounded-xl border border-rc-border bg-rc-surface">
              <div className="flex items-center justify-between px-5 pt-5">
                <p className="text-base font-semibold text-rc-fg">Perlu dibalas</p>
                <span className="text-sm font-medium text-rc-accent">Buka workspace</span>
              </div>
              <div className="px-2 pb-2 pt-2">
                {HERO_REPLIES.map((r) => (
                  <div key={r.name} className="flex items-start gap-3 rounded-lg px-3 py-3">
                    <span className="mt-0.5 h-8 w-8 shrink-0 rounded-full bg-rc-border" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-semibold text-rc-fg">{r.name}</span>
                        <span className={cn("rounded-full px-1.5 py-0.5 text-[10px] font-semibold", r.score === "Hot" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-800")}>
                          {r.score}
                        </span>
                        <span className="ml-auto shrink-0 text-xs text-rc-fg-subtle">{r.ago}</span>
                      </div>
                      <p className="mt-0.5 truncate text-sm text-rc-fg-muted">{r.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-rc-border bg-rc-surface">
              <div className="flex items-center justify-between px-5 pt-5">
                <p className="text-base font-semibold text-rc-fg">Hasil kerja agen</p>
                <span className="text-sm font-medium text-rc-accent">Semua log</span>
              </div>
              <div className="px-2 pb-2 pt-2">
                {HERO_LOGS.map((e) => (
                  <div key={e.event} className="flex items-start gap-3 rounded-lg px-3 py-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-sm font-semibold text-rc-fg">{e.event}</span>
                        <span className={cn("rounded-full px-1.5 py-0.5 text-[10px] font-semibold", e.tone === "green" ? "bg-emerald-50 text-emerald-700" : "bg-rc-accent-soft text-rc-accent")}>
                          {e.tone === "green" ? "Berhasil" : "Disiapkan"}
                        </span>
                      </div>
                      <p className="mt-0.5 truncate text-sm text-rc-fg-muted">{e.detail}</p>
                    </div>
                    <span className="shrink-0 text-xs text-rc-fg-subtle">{e.ago}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Lebar konten section di bawah hero. */
const container = "mx-auto w-full max-w-[1320px] px-4 sm:px-6 lg:px-8";
/** Pita section: latar berbeda + garis atas supaya batas antarsection jelas. */
const band = "border-t border-rc-border py-20 lg:py-28";

function SectionHead({
  title,
  sub,
  dark,
}: {
  title: ReactNode;
  sub?: string;
  dark?: boolean;
}) {
  return (
    <Reveal className="mx-auto max-w-3xl text-center">
      <h2 className={cn("text-3xl font-semibold tracking-tight text-balance sm:text-5xl", dark && "text-white")}>
        {title}
      </h2>
      {sub && (
        <p className={cn("mx-auto mt-4 max-w-2xl text-base sm:text-lg", dark ? "text-[#aab4cc]" : "text-rc-fg-muted")}>{sub}</p>
      )}
    </Reveal>
  );
}

function Mark({ children, solid }: { children: ReactNode; solid?: boolean }) {
  return (
    <span className="relative whitespace-nowrap">
      <span
        aria-hidden
        className={cn(
          "absolute inset-x-[-0.08em] rounded-sm",
          solid ? "bottom-[0.02em] h-[0.12em] bg-rc-highlight" : "bottom-[0.08em] h-[0.32em] bg-rc-highlight/70",
        )}
      />
      <span className="relative">{children}</span>
    </span>
  );
}

export default function Landing() {
  return (
    <div className="rc-brand bg-rc-bg text-rc-fg">
      <a
        href="#konten"
        className="sr-only z-50 rounded-md bg-rc-fg px-3 py-2 text-sm text-rc-primary-fg focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Lewati ke konten
      </a>
      <AnnouncementBar />
      <LandingHeader />

      <main id="konten">
        <section className="relative -mt-[4.5rem] overflow-hidden bg-rc-hero pt-[4.5rem] text-white">
          <HeroContours />
          <div className="relative mx-auto w-full max-w-[1320px] px-4 pt-16 pb-14 sm:px-6 sm:pt-24 lg:px-8 lg:pb-20">
            <div className="mx-auto max-w-3xl text-center">
              <h1
                className="rc-enter mt-6 text-4xl font-bold tracking-tight text-balance sm:text-6xl"
                style={{ animationDelay: "80ms" }}
              >
                Raih semua Leadsmu dengan AI, hingga <Mark solid>untung</Mark>
              </h1>
              <p
                className="rc-enter mx-auto mt-6 max-w-2xl text-base text-white/80 sm:text-lg"
                style={{ animationDelay: "160ms" }}
              >
                Multi kanal lead agent yang dapat membawa menuju ke decision-close maker.
              </p>
              <div
                className="rc-enter mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
                style={{ animationDelay: "240ms" }}
              >
                <Link
                  href="/dashboard/inbox"
                  className="group inline-flex min-h-12 items-center gap-2 rounded-md bg-white px-6 text-sm font-medium text-rc-hero transition-colors hover:bg-white/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                >
                  Coba demo
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
                </Link>
                <a
                  href="#agen"
                  className="inline-flex min-h-12 items-center rounded-md border border-white/40 px-6 text-sm font-medium text-white transition-colors hover:border-white hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                >
                  Lihat cara kerja
                </a>
              </div>
            </div>
          </div>
          <div className="relative mx-auto w-full max-w-[1320px] px-4 sm:px-6 lg:px-8">
            <div
              className="rc-enter rounded-t-2xl bg-rc-surface p-2 pb-0 sm:p-3 sm:pb-0"
              style={{ animationDelay: "380ms" }}
            >
              <HeroDashboard />
            </div>
          </div>
        </section>

        <section aria-label="Integrasi" className="bg-rc-surface py-14">
          <div className={container}>
            <p className="text-center text-lg font-semibold text-rc-fg-mute opcity-40">Terintegrasi dengan</p>
            <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-14 gap-y-8 sm:gap-x-20">
              {INTEGRATIONS.map((i) => (
                <li key={i.slug} className="group flex items-center gap-3">
                  <Image
                    src={`https://cdn.simpleicons.org/${i.slug}`}
                    alt=""
                    width={32}
                    height={32}
                    unoptimized
                    className="h-8 w-8 opacity-50 grayscale transition-[filter,opacity] duration-300 group-hover:opacity-100 group-hover:grayscale-0"
                  />
                  <span className="text-xl font-semibold tracking-tight text-rc-fg-subtle transition-colors duration-300 group-hover:text-rc-fg">
                    {i.name}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="agen" className={cn(band, "scroll-mt-24")}>
          <div className={container}>
            <SectionHead
              title="Agen bekerja 24/7"
              sub="Pilih kanal, lalu lihat agen membaca pesan, menilai prioritas, dan membalas dari katalog yang sudah mendukung beragam kanal."
            />
            <Reveal className="mt-12">
              <HeroStage />
            </Reveal>
          </div>
        </section>

        <section id="kenapa" className="scroll-mt-24 py-20 lg:py-28">
          <div className={container}>
            <SectionHead
              title="Bukan sekadar chatbot"
              sub="Pesan yang sama, dua cara membalas. Coba bandingkan."
            />
            <Reveal className="mt-12">
              <WhyToggle />
            </Reveal>
          </div>
        </section>

        <section id="kemampuan" className={cn(band, "scroll-mt-24 bg-rc-surface")}>
          <div className={container}>
            <SectionHead
              title="Bekerja seperti admin terbaik Anda"
              sub="Klik salah satu untuk melihat contohnya."
            />
            <Reveal className="mt-12">
              <SkillsExplorer />
            </Reveal>
          </div>
        </section>

        <section id="faq" className="scroll-mt-24 bg-rc-surface py-20 lg:py-28">
          <div className={container}>
            <SectionHead title="Pertanyaan yang sering diajukan" />
            <Reveal className="mx-auto mt-12 flex max-w-3xl flex-col gap-2">
              {FAQ.map((f) => (
                <details
                  key={f.q}
                  className="group rounded-lg bg-rc-bg px-5 transition-colors duration-300 open:bg-rc-accent-soft hover:bg-rc-surface-hover"
                >
                  <summary className="flex min-h-16 cursor-pointer list-none items-center justify-between gap-4 rounded-lg text-base font-medium focus-visible:outline-2 focus-visible:outline-rc-accent [&::-webkit-details-marker]:hidden">
                    {f.q}
                    <ChevronDown
                      aria-hidden
                      className="h-5 w-5 shrink-0 text-rc-fg-muted transition-[transform,color] duration-300 group-open:rotate-180 group-open:text-rc-accent group-hover:text-rc-fg"
                    />
                  </summary>
                  <p className="pr-10 pb-5 text-rc-fg-muted">{f.a}</p>
                </details>
              ))}
            </Reveal>
          </div>
        </section>
      <section aria-label="Mulai" className="bg-rc-surface pt-10">
        <div className={container}>
          <div className="relative overflow-hidden rounded-t-2xl bg-rc-hero px-6 pt-16 pb-14 text-center text-white sm:px-12 lg:pt-24 lg:pb-20">
            <HeroContours className="[mask-image:linear-gradient(to_bottom,#000_40%,transparent)]" />
            <div className="relative">
              <Reveal>
                <h2 className="mx-auto max-w-3xl text-3xl font-bold tracking-tight text-balance sm:text-5xl">
                  Setiap pesan terjawab. Setiap pembeli <Mark solid>tertangani.</Mark>
                </h2>
                <p className="mx-auto mt-5 max-w-xl text-base text-white/80 sm:text-lg">
                  Anda tetap yang menentukan apa yang dikirim atas nama usaha Anda.
                </p>
                <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                  <Link
                    href="/dashboard/inbox"
                    className="group inline-flex min-h-12 items-center gap-2 rounded-md bg-white px-6 text-sm font-medium text-rc-hero transition-colors hover:bg-white/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                  >
                    Coba demo
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
                  </Link>
                  <Link
                    href="/dashboard/integrasi"
                    className="inline-flex min-h-12 items-center rounded-md border border-white/40 px-6 text-sm font-medium text-white transition-colors hover:border-white hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                  >
                    Hubungkan kanal
                  </Link>
                </div>
              </Reveal>
            </div>
          </div>
        </div>
      </section>
      </main>

      <footer className="relative overflow-hidden bg-rc-hero text-white [--rc-fg:#ffffff] [--rc-primary:#ffffff] [--rc-primary-fg:var(--rc-hero)]">
        <div className={cn(container, "relative")}>
          <div className="flex flex-col gap-10 py-12 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <Logo />
              <p className="mt-3 max-w-xs text-sm text-white/70">AI yang menyiapkan, pemilik yang memutuskan.</p>
            </div>
            <nav aria-label="Tautan footer" className="grid grid-cols-2 gap-x-16 gap-y-3 text-sm">
              <span className="font-medium text-white">Produk</span>
              <span className="font-medium text-white">Aplikasi</span>
              <a href="#agen" className="text-white/70 transition-colors hover:text-white">Agen AI</a>
              <Link href="/dashboard" className="text-white/70 transition-colors hover:text-white">Beranda aplikasi</Link>
              <a href="#kenapa" className="text-white/70 transition-colors hover:text-white">Kenapa OmniLead</a>
              <Link href="/dashboard/inbox" className="text-white/70 transition-colors hover:text-white">Kotak masuk</Link>
              <a href="#kemampuan" className="text-white/70 transition-colors hover:text-white">Kemampuan</a>
              <Link href="/dashboard/integrasi" className="text-white/70 transition-colors hover:text-white">Kanal</Link>
            </nav>
          </div>
          <p className="border-t border-white/15 py-6 text-sm text-white/60">© 2026 Tim OmniLead · Agentic AI Hackathon 2026</p>
        </div>
      </footer>
    </div>
  );
}
