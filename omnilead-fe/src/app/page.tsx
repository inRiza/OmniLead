import type { ComponentType, ReactNode, SVGProps } from "react";
import Link from "next/link";
import { ArrowRight, Gauge, LayoutGrid, MessageCircleQuestion, ShieldCheck, Sparkles, Workflow } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { AnnouncementBar, HeroStage, LandingHeader, Reveal, UseCases } from "@/components/landing/Interactive";
import { ControlPanel, FeatureTabs, SkillsExplorer, WhyToggle } from "@/components/landing/Sections";
import { ChannelIcon } from "@/components/primitives";
import type { Channel } from "@/lib/types";
import { cn } from "@/lib/utils";

type Icon = ComponentType<SVGProps<SVGSVGElement>>;

const CHANNELS: { channel: Channel; name: string; path: string }[] = [
  { channel: "whatsapp", name: "WhatsApp", path: "Terhubung langsung" },
  { channel: "instagram", name: "Instagram", path: "Komentar dan DM" },
  { channel: "email", name: "Gmail", path: "Terhubung langsung" },
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
    a: "Instagram, WhatsApp, dan Gmail tersedia. Hubungkan akun bisnis melalui halaman Integrasi, atau tempel pesan dari kanal tersebut untuk menyiapkan draf balasan.",
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

/** Lebar konten section di bawah hero. */
const container = "mx-auto w-full max-w-[1320px] px-4 sm:px-6 lg:px-8";
/** Pita section: latar berbeda + garis atas supaya batas antarsection jelas. */
const band = "border-t border-rc-border py-20 lg:py-28";

const dotGrid = {
  backgroundImage: "radial-gradient(var(--rc-border-strong) 1px, transparent 1px)",
  backgroundSize: "22px 22px",
};

/** Tag judul section: pil dengan ikon dalam lingkaran berwarna. */
function Eyebrow({ icon: I, children, dark }: { icon: Icon; children: ReactNode; dark?: boolean }) {
  return (
    <p
      className={cn(
        "inline-flex items-center gap-2.5 rounded-full border py-1.5 pr-4 pl-1.5",
        dark
          ? "border-white/15 bg-white/[0.06]"
          : "border-rc-accent/20 bg-rc-surface shadow-[0_6px_18px_-10px_rgba(47,91,234,0.55)]",
      )}
    >
      <span
        className={cn(
          "inline-flex h-8 w-8 items-center justify-center rounded-full",
          dark ? "bg-rc-highlight text-rc-navy" : "bg-rc-accent text-rc-accent-fg",
        )}
      >
        <I className="h-4 w-4" aria-hidden />
      </span>
      <span className={cn("text-[15px] font-semibold tracking-tight", dark ? "text-white" : "text-rc-fg")}>{children}</span>
    </p>
  );
}

function SectionHead({
  icon,
  eyebrow,
  title,
  sub,
  dark,
}: {
  icon: Icon;
  eyebrow: string;
  title: ReactNode;
  sub?: string;
  dark?: boolean;
}) {
  return (
    <Reveal className="mx-auto max-w-3xl text-center">
      <Eyebrow icon={icon} dark={dark}>
        {eyebrow}
      </Eyebrow>
      <h2 className={cn("mt-5 text-3xl font-semibold tracking-tight text-balance sm:text-5xl", dark && "text-white")}>
        {title}
      </h2>
      {sub && (
        <p className={cn("mx-auto mt-4 max-w-2xl text-base sm:text-lg", dark ? "text-[#aab4cc]" : "text-rc-fg-muted")}>{sub}</p>
      )}
    </Reveal>
  );
}

/** Sorotan saffron di bawah kata kunci, seperti stabilo. */
function Mark({ children }: { children: ReactNode }) {
  return (
    <span className="relative whitespace-nowrap">
      <span
        aria-hidden
        className="absolute inset-x-[-0.08em] bottom-[0.08em] h-[0.32em] rounded-sm bg-rc-highlight/70"
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
        {/* Hero (gaya wafer): latar full-bleed, isi di tengah */}
        <section className="relative -mt-[4.5rem] overflow-hidden bg-gradient-to-b from-rc-accent-soft via-rc-bg to-rc-bg pt-[4.5rem]">
          <div aria-hidden className="pointer-events-none absolute inset-0 opacity-70" style={dotGrid} />
          <div
            aria-hidden
            className="pointer-events-none absolute -top-48 right-[-12%] h-[42rem] w-[42rem] rounded-full bg-rc-accent/20 blur-3xl"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute bottom-[-14rem] left-[-10%] h-[32rem] w-[32rem] rounded-full bg-rc-highlight/20 blur-3xl"
          />
          <div className="relative mx-auto w-full max-w-[1320px] px-4 pt-14 pb-16 sm:px-6 sm:pt-20 lg:px-8 lg:pb-24">
            <div className="mx-auto max-w-3xl text-center">
              <p className="rc-enter inline-flex items-center gap-2 rounded-full border border-rc-border bg-rc-surface/80 px-3 py-1 text-sm font-medium text-rc-fg-muted backdrop-blur">
                <span className="h-1.5 w-1.5 rounded-full bg-rc-accent" aria-hidden />
                Asisten penjualan untuk UMKM
              </p>
              <h1
                className="rc-enter mt-6 text-4xl font-semibold tracking-tight text-balance sm:text-6xl"
                style={{ animationDelay: "80ms" }}
              >
                AI yang menyiapkan. Pemilik yang <Mark>memutuskan.</Mark>
              </h1>
              <p
                className="rc-enter mx-auto mt-6 max-w-2xl text-base text-rc-fg-muted sm:text-lg"
                style={{ animationDelay: "160ms" }}
              >
                Pesan pelanggan dari WhatsApp, Instagram, dan email terkumpul di satu tempat. AI menyiapkan
                balasan, mencatat data pelanggan, dan mengingatkan Anda untuk menindaklanjuti. Tidak ada pesan yang
                terkirim sebelum Anda setujui.
              </p>
              <div
                className="rc-enter mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row"
                style={{ animationDelay: "240ms" }}
              >
                <Link
                  href="/dashboard/inbox"
                  className="group inline-flex min-h-12 items-center gap-2 rounded-full bg-rc-accent px-6 text-sm font-medium text-rc-accent-fg shadow-[0_10px_24px_-10px_rgba(47,91,234,0.7)] transition-colors hover:bg-rc-accent-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-accent"
                >
                  Coba demo
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
                </Link>
                <a
                  href="#kasus"
                  className="inline-flex min-h-12 items-center rounded-full border border-rc-border bg-rc-surface/80 px-6 text-sm font-medium text-rc-fg backdrop-blur transition-colors hover:border-rc-accent hover:text-rc-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-accent"
                >
                  Lihat cara kerja
                </a>
              </div>
            </div>
            <div className="rc-enter mt-14 lg:mt-20" style={{ animationDelay: "380ms" }}>
              <HeroStage />
              <p className="mt-4 text-center text-sm text-rc-fg-subtle">
                Ini contoh, bukan data asli. Klik salah satu kanal, lalu setujui atau tolak balasan yang disiapkan.
              </p>
            </div>
          </div>
        </section>

        {/* Kanal (pengganti "Trusted by" Halo AI) — pita putih */}
        <section aria-label="Kanal yang didukung" className="border-y border-rc-border bg-rc-surface py-10">
          <p className="text-center text-sm text-rc-fg-muted">
            Terhubung ke kanal yang <span className="font-medium text-rc-fg">sudah dipakai pelanggan Anda</span>
          </p>
          <div className="relative mt-6 overflow-hidden [mask-image:linear-gradient(90deg,transparent,#000_10%,#000_90%,transparent)]">
            <ul className="rc-marquee flex w-max gap-3">
              {[...CHANNELS, ...CHANNELS].map((c, i) => (
                <li
                  key={`${c.channel}-${i}`}
                  aria-hidden={i >= CHANNELS.length || undefined}
                  className="flex items-center gap-3 rounded-2xl border border-rc-border bg-rc-bg px-5 py-3"
                >
                  <ChannelIcon channel={c.channel} size="md" />
                  <span>
                    <span className="block text-sm font-medium">{c.name}</span>
                    <span className="block text-sm whitespace-nowrap text-rc-fg-muted">{c.path}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* Kenapa — latar halaman */}
        <section id="kenapa" className="scroll-mt-24 py-20 lg:py-28">
          <div className={container}>
            <SectionHead
              icon={Sparkles}
              eyebrow="Kenapa OmniLead"
              title="Bukan sekadar chatbot"
              sub="Pesan yang sama, dua cara membalas. Coba bandingkan."
            />
            <Reveal className="mt-12">
              <WhyToggle />
            </Reveal>
          </div>
        </section>

        {/* Kemampuan — pita putih */}
        <section className={cn(band, "bg-rc-surface")}>
          <div className={container}>
            <SectionHead
              icon={Gauge}
              eyebrow="Kemampuan"
              title="Bekerja seperti admin terbaik Anda"
              sub="Klik salah satu untuk melihat contohnya."
            />
            <Reveal className="mt-12">
              <SkillsExplorer />
            </Reveal>
          </div>
        </section>

        {/* Fitur — pita biru muda */}
        <section id="fitur" className={cn(band, "scroll-mt-24 bg-rc-accent-soft")}>
          <div className={container}>
            <SectionHead
              icon={LayoutGrid}
              eyebrow="Fitur"
              title="Semua urusan membalas pelanggan, di satu layar"
              sub="Balas, setujui, dan pantau pelanggan dari semua kanal tanpa pindah aplikasi."
            />
            <Reveal className="mt-12">
              <FeatureTabs />
            </Reveal>
          </div>
        </section>

        {/* Kasus — latar halaman */}
        <section id="kasus" className={cn(band, "scroll-mt-24")}>
          <div className={container}>
            <SectionHead
              icon={Workflow}
              eyebrow="Contoh kasus"
              title="Dari tanya harga sampai pesan mencurigakan"
              sub="Situasi yang sering dihadapi UMKM, dan cara OmniLead menanganinya."
            />
            <Reveal className="mt-12">
              <UseCases />
            </Reveal>
          </div>
        </section>

        {/* Kendali — pita navy */}
        <section id="kendali" className="relative scroll-mt-24 overflow-hidden bg-rc-navy py-20 lg:py-28">
          <div aria-hidden className="pointer-events-none absolute -top-40 left-1/2 h-80 w-[50rem] -translate-x-1/2 rounded-full bg-rc-accent/30 blur-3xl" />
          <div className={cn(container, "relative")}>
            <SectionHead
              dark
              icon={ShieldCheck}
              eyebrow="Kendali"
              title="Anda tetap memegang kemudi"
              sub="Coba sendiri: hentikan AI, atau matikan pengiriman di kanal tertentu."
            />
            <Reveal className="mt-12">
              <ControlPanel />
            </Reveal>
          </div>
        </section>

        {/* FAQ — pita putih */}
        <section id="faq" className="scroll-mt-24 bg-rc-surface py-20 lg:py-28">
          <div className={container}>
            <SectionHead icon={MessageCircleQuestion} eyebrow="FAQ" title="Pertanyaan yang sering diajukan" />
            <Reveal className="mx-auto mt-12 flex max-w-4xl flex-col gap-3">
              {FAQ.map((f) => (
                <details
                  key={f.q}
                  className="group rounded-2xl border border-rc-border bg-rc-bg px-5 transition-colors open:border-rc-accent/40 open:bg-rc-accent-soft/60 hover:border-rc-border-strong"
                >
                  <summary className="flex min-h-16 cursor-pointer list-none items-center justify-between gap-4 rounded-md text-base font-medium focus-visible:outline-2 focus-visible:outline-rc-accent [&::-webkit-details-marker]:hidden">
                    {f.q}
                    <span
                      aria-hidden
                      className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-rc-surface text-lg text-rc-fg-muted shadow-sm transition-[transform,background-color,color] duration-300 group-open:rotate-45 group-open:bg-rc-accent group-open:text-rc-accent-fg"
                    >
                      +
                    </span>
                  </summary>
                  <p className="pr-12 pb-5 text-rc-fg-muted">{f.a}</p>
                </details>
              ))}
            </Reveal>
          </div>
        </section>

        {/* CTA — latar halaman */}
        <section className="border-t border-rc-border py-20">
          <div className={container}>
            <Reveal className="relative overflow-hidden rounded-[2rem] border border-rc-border bg-gradient-to-br from-[#dfe7ff] via-rc-surface to-[#ffeccc] px-6 py-16 text-center sm:px-12 lg:py-24">
              <div aria-hidden className="pointer-events-none absolute inset-0 opacity-60" style={dotGrid} />
              <div className="relative">
                <Eyebrow icon={Sparkles}>Mulai sekarang</Eyebrow>
                <h2 className="mx-auto mt-5 max-w-3xl text-3xl font-semibold tracking-tight text-balance sm:text-5xl">
                  Setiap pesan terjawab. Setiap pembeli <Mark>tertangani.</Mark>
                </h2>
                <p className="mx-auto mt-4 max-w-xl text-base text-rc-fg-muted sm:text-lg">
                  Anda tetap yang menentukan apa yang dikirim atas nama usaha Anda.
                </p>
                <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                  <Link
                    href="/dashboard/inbox"
                    className="group inline-flex min-h-12 items-center gap-2 rounded-full bg-rc-accent px-6 text-sm font-medium text-rc-accent-fg shadow-[0_10px_24px_-10px_rgba(47,91,234,0.7)] transition-colors hover:bg-rc-accent-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-accent"
                  >
                    Coba demo
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
                  </Link>
                  <Link
                    href="/dashboard/integrasi"
                    className="inline-flex min-h-12 items-center rounded-full border border-rc-border bg-rc-surface px-6 text-sm font-medium transition-colors hover:border-rc-accent hover:text-rc-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-accent"
                  >
                    Hubungkan kanal
                  </Link>
                </div>
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      <footer className="bg-rc-navy text-white [--rc-accent:#8ea8ff] [--rc-border:#1f2d52] [--rc-fg-muted:#aab4cc] [--rc-fg-subtle:#7d89a6] [--rc-fg:#ffffff] [--rc-primary-fg:#0b1a3a] [--rc-primary:#ffffff]">
        <div className={cn(container, "flex flex-col gap-8 py-12 sm:flex-row sm:items-start sm:justify-between")}>
          <div>
            <Logo accent />
            <p className="mt-3 max-w-xs text-sm text-rc-fg-muted">AI yang menyiapkan, pemilik yang memutuskan.</p>
          </div>
          <nav aria-label="Tautan footer" className="grid grid-cols-2 gap-x-16 gap-y-2 text-sm">
            <span className="text-rc-fg-subtle">Produk</span>
            <span className="text-rc-fg-subtle">Aplikasi</span>
            <a href="#kenapa" className="text-rc-fg-muted hover:text-white">Kenapa OmniLead</a>
            <Link href="/dashboard" className="text-rc-fg-muted hover:text-white">Beranda aplikasi</Link>
            <a href="#fitur" className="text-rc-fg-muted hover:text-white">Fitur</a>
            <Link href="/dashboard/inbox" className="text-rc-fg-muted hover:text-white">Kotak masuk</Link>
            <a href="#kendali" className="text-rc-fg-muted hover:text-white">Kendali</a>
            <Link href="/dashboard/integrasi" className="text-rc-fg-muted hover:text-white">Kanal</Link>
          </nav>
        </div>
        <p className={cn(container, "border-t border-rc-border py-6 text-sm text-rc-fg-subtle")}>
          © 2026 Tim OmniLead · Agentic AI Hackathon 2026
        </p>
      </footer>
    </div>
  );
}
