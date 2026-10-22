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
    a: "Tidak. AI hanya menyiapkan balasan. Pesan baru terkirim setelah Anda setujui, dan semua pengiriman bisa dihentikan dengan tombol jeda.",
  },
  {
    q: "Dari mana AI tahu harga dan stok?",
    a: "Dari katalog dan daftar tanya-jawab yang Anda isi. Kalau balasan menyebut harga di luar katalog atau diskon melebihi batas, balasan itu ditahan.",
  },
  {
    q: "Kanal apa saja yang bisa dipakai?",
    a: "WhatsApp, Instagram (komentar dan DM), Facebook (komentar Page dan Messenger), dan Gmail. Hubungkan akun bisnis lewat halaman Integrasi. Selama kanal belum terhubung, tempel pesannya untuk menyiapkan draf balasan.",
  },
  {
    q: "Apakah AI paham bahasa chat sehari-hari?",
    a: "Ya. Singkatan dan typo seperti \"brp harga nasbox 30 org kak?\" tetap dipahami.",
  },
  {
    q: "Bagaimana kalau balasan dari AI kurang tepat?",
    a: "Ubah dulu sebelum dikirim, atau tolak dan tulis alasannya. Alasan itu dipakai supaya balasan berikutnya lebih sesuai.",
  },
];

function Bar({ className }: { className?: string }) {
  return <span className={cn("block h-2.5 rounded-sm bg-rc-border", className)} />;
}

function HeroDashboard() {
  return (
    <div
      aria-hidden
      className="flex h-[22rem] overflow-hidden rounded-t-lg border border-b-0 border-rc-border bg-rc-bg sm:h-[30rem] lg:h-[36rem]"
    >
      <aside className="hidden w-56 shrink-0 flex-col gap-6 border-r border-rc-border bg-rc-surface p-5 md:flex">
        <Logo />
        <div className="flex flex-col gap-4">
          {["w-24", "w-28", "w-20", "w-32", "w-24", "w-16"].map((w, i) => (
            <span key={i} className="flex items-center gap-3">
              <span className="h-4 w-4 rounded-sm bg-rc-border" />
              <Bar className={w} />
            </span>
          ))}
        </div>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-14 items-center justify-between border-b border-rc-border bg-rc-surface px-5">
          <Bar className="w-40" />
          <span className="flex items-center gap-3">
            <Bar className="hidden w-24 sm:block" />
            <span className="h-8 w-8 rounded-full bg-rc-border" />
          </span>
        </div>
        <div className="flex flex-1 flex-col gap-4 p-5">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="flex flex-col gap-3 rounded-md border border-rc-border bg-rc-surface p-4">
                <Bar className="w-20" />
                <Bar className="h-5 w-14" />
              </div>
            ))}
          </div>
          <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <div className="flex flex-col gap-4 rounded-md border border-rc-border bg-rc-surface p-4">
              <Bar className="w-32" />
              <div className="flex-1 rounded-sm bg-rc-bg" />
            </div>
            <div className="hidden flex-col gap-4 rounded-md border border-rc-border bg-rc-surface p-4 lg:flex">
              <Bar className="w-24" />
              {[0, 1, 2, 3, 4].map((i) => (
                <span key={i} className="flex items-center gap-3">
                  <span className="h-7 w-7 shrink-0 rounded-full bg-rc-border" />
                  <span className="flex flex-1 flex-col gap-1.5">
                    <Bar className="w-3/4" />
                    <Bar className="h-2 w-1/2" />
                  </span>
                </span>
              ))}
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
              title="Agen bekerja 24/7, Anda yang memutuskan"
              sub="Pilih kanal, lalu lihat agen membaca pesan, menilai prioritas, dan menyiapkan balasan dari katalog. Balasan baru terkirim setelah Anda setujui."
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
