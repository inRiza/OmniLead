"use client";

import { useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import Link from "next/link";
import { ArrowRight, ChevronDown, Menu, X } from "lucide-react";
import { Logo, LogoMark } from "@/components/brand/Logo";
import { ChannelMock, type MockScenario } from "@/components/landing/ChannelMocks";
import { LandingChannelIcon, landingChannelLabel } from "@/components/landing/channels";
import { cn } from "@/lib/utils";

// Contoh di halaman ini diambil dari evalset dan katalog demo (data contoh, bukan pelanggan nyata).

const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";

function subscribeReduced(cb: () => void) {
  const mq = window.matchMedia(REDUCED_QUERY);
  mq.addEventListener("change", cb);
  return () => mq.removeEventListener("change", cb);
}

export function usePrefersReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeReduced,
    () => window.matchMedia(REDUCED_QUERY).matches,
    () => false,
  );
}

/** Bungkus section supaya muncul halus saat masuk viewport (sekali saja). */
export function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          io.disconnect();
        }
      },
      { rootMargin: "0px 0px -10% 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      data-shown={shown ? "" : undefined}
      className={cn("rc-reveal", className)}
      style={{ transitionDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

export function AnnouncementBar() {
  return (
    <div className="relative z-50 bg-rc-navy text-white">
      <div className="flex min-h-10 items-center justify-center gap-3 px-4 py-2 text-sm">
        <span className="hidden sm:inline">Prototype OmniLead untuk Agentic AI Hackathon 2026</span>
        <span className="sm:hidden">Hackathon 2026</span>
        <span aria-hidden className="h-4 w-px bg-white/25" />
        <Link
          href="/demo"
          className="group inline-flex items-center gap-1 font-medium whitespace-nowrap text-white hover:text-rc-highlight focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-highlight"
        >
          Coba demo
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden />
        </Link>
      </div>
    </div>
  );
}

const PRODUCT_LINKS = [
  { href: "#agen", label: "Agen AI", desc: "Membalas di semua kanal, 24/7" },
  { href: "#kenapa", label: "Kenapa OmniLead", desc: "Bedanya dengan chatbot biasa" },
  { href: "#kemampuan", label: "Kemampuan", desc: "Paham, mengecek, dan menindaklanjuti" },
];

const navItem =
  "inline-flex min-h-10 items-center gap-1 rounded-md px-4 text-sm font-medium text-rc-fg/80 transition-colors hover:bg-black/5 hover:text-rc-fg focus-visible:outline-2 focus-visible:outline-rc-accent";

const headerAction =
  "hidden min-h-10 items-center justify-center rounded-md px-5 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-accent sm:inline-flex";

function NavLinks() {
  return (
    <>
      <div className="group relative">
        <button type="button" aria-haspopup="true" className={navItem}>
          Produk
          <ChevronDown
            className="h-4 w-4 opacity-60 transition-transform group-focus-within:rotate-180 group-hover:rotate-180"
            aria-hidden
          />
        </button>
        <div className="invisible absolute top-full left-0 pt-2 opacity-0 transition-[opacity,visibility] duration-200 group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100">
          <ul className="w-64 rounded-md border border-[#e2e7f2] bg-white p-1.5 shadow-[0_16px_40px_-16px_rgba(11,23,54,0.25)]">
            {PRODUCT_LINKS.map((l) => (
              <li key={l.href}>
                <a
                  href={l.href}
                  className="block rounded px-3 py-2 transition-colors hover:bg-[#eef3ff] focus-visible:outline-2 focus-visible:outline-[#0144f5]"
                >
                  <span className="block text-sm font-medium text-[#0b1736]">{l.label}</span>
                  <span className="block text-sm text-[#5a6680]">{l.desc}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <a href="#faq" className={navItem}>
        FAQ
      </a>
    </>
  );
}

const onHero = "[--rc-fg:#ffffff] [--rc-primary:#ffffff] [--rc-primary-fg:var(--rc-hero)] [--rc-accent:#ffffff]";

export function LandingHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 24);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);

  const solid = scrolled || open;

  return (
    <header
      className={cn(
        "sticky top-0 z-40",
        solid ? "px-2 pt-3 pb-2 sm:px-3" : cn("h-[4.5rem]", onHero),
      )}
    >
      <div
        className={cn(
          "mx-auto flex items-center gap-8 transition-[max-width,width,margin,padding,height,background-color,border-radius,box-shadow] duration-500 ease-out",
          solid
            ? "h-14 w-full max-w-[1120px] rounded-md border border-[#e2e7f2]/80 bg-white px-5 shadow-[0_12px_40px_-12px_rgba(11,23,54,0.22)]"
            : "h-[4.5rem] w-full max-w-[1320px] rounded-none bg-transparent px-4 sm:px-6 lg:px-8",
        )}
      >
        <Link
          href="/"
          aria-label="OmniLead, ke atas"
          className="rounded focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-rc-accent"
        >
          <Logo />
        </Link>

        <nav aria-label="Navigasi halaman" className="hidden items-center gap-1 md:flex">
          <NavLinks />
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Link
            href="/dashboard"
            className={cn(
              headerAction,
              solid
                ? "bg-[#eef1f6] text-rc-fg hover:bg-[#e4e9f2]"
                : "bg-white/15 text-white ring-1 ring-inset ring-white/35 hover:bg-white/25",
            )}
          >
            Masuk
          </Link>
          <Link
            href="/demo"
            className={cn(
              headerAction,
              solid ? "bg-rc-hero text-white hover:bg-rc-hero-hover" : "bg-white text-rc-hero hover:bg-white/90",
            )}
          >
            Coba demo
          </Link>
          <button
            type="button"
            aria-label={open ? "Tutup menu" : "Buka menu"}
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md text-rc-fg focus-visible:outline-2 focus-visible:outline-rc-accent md:hidden"
          >
            {open ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
          </button>
        </div>
      </div>

      {open && (
        <nav aria-label="Navigasi ponsel" className="rc-enter absolute inset-x-4 top-full mt-1 rounded-md bg-white px-3 pt-2 pb-3 md:hidden">
          {[...PRODUCT_LINKS, { href: "#faq", label: "FAQ", desc: "" }].map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="flex min-h-12 items-center rounded-md px-3 text-base font-medium text-rc-fg hover:bg-rc-surface-hover"
            >
              {l.label}
            </a>
          ))}
          <Link
            href="/demo"
            className="mt-2 flex min-h-12 items-center justify-center rounded-md bg-rc-hero text-base font-medium text-white"
          >
            Coba demo
          </Link>
        </nav>
      )}
    </header>
  );
}

/* ------------------------------------------------------------------ */
/* Hero: kanal → agen → usulan                                          */
/* ------------------------------------------------------------------ */

type Priority = { level: "Tinggi" | "Sedang"; score: number; reason: string };
type StageScenario = MockScenario & { priority: Priority };

const SCENARIOS: StageScenario[] = [
  {
    channel: "instagram",
    customer: "ani.majujaya",
    priority: { level: "Tinggi", score: 86, reason: "60 porsi untuk tanggal 30, atas nama perusahaan" },
    thread: [
      { from: "customer", text: "Kak, bisa buat 60 orang tgl 30? harga?" },
      { from: "agent", text: "Bisa, Kak Ani! Rincian harga untuk 60 porsi kami kirim lewat DM ya." },
      { from: "customer", text: "Bisa kirim ke Cimahi juga kak?" },
      { from: "agent", text: "Bisa, Kak. Kami antar ke Bandung dan Cimahi. Detail paketnya sekalian kami kirim di DM ya." },
    ],
  },
  {
    channel: "whatsapp",
    customer: "Dinda",
    priority: { level: "Sedang", score: 64, reason: "Reseller, 20 pcs, minta harga grosir" },
    thread: [
      { from: "customer", text: "kak aku reseller, mau ambil hijab pashmina 20 pcs brp?" },
      {
        from: "agent",
        text: "Halo Kak Dinda! Hijab Pashmina Plisket Rp49.000 × 20 = Rp980.000. Dengan diskon reseller 10% jadi Rp882.000.",
      },
      { from: "customer", text: "oke kak, bisa dikirim besok?" },
      { from: "agent", text: "Bisa, Kak. Setelah pembayaran masuk, pesanan dikirim besok pagi ya." },
    ],
  },
  {
    channel: "email",
    customer: "PT Nusa Corp",
    priority: { level: "Tinggi", score: 91, reason: "100 pax untuk acara kantor, nilai sekitar Rp3,5 juta" },
    thread: [
      {
        from: "customer",
        text: "Selamat pagi,\n\nMohon penawaran katering 100 pax untuk acara kantor tanggal 12.\n\nTerima kasih,\nRina",
      },
      {
        from: "agent",
        text: "Selamat pagi,\n\nTerima kasih atas permintaannya. Penawaran Paket B nasi box komplit: Rp35.000 × 100 porsi = Rp3.500.000. Pembayaran DP 50% saat konfirmasi.\n\nSalam,\nOmniLead",
      },
      { from: "customer", text: "Baik, kami ambil. Mohon dikirimkan invoice-nya." },
      { from: "agent", text: "Siap. Invoice kami lampirkan dan tanggal 12 sudah kami kunci untuk pesanan Anda." },
    ],
  },
  {
    channel: "facebook",
    customer: "Sari Wulandari",
    priority: { level: "Sedang", score: 58, reason: "10 box hampers, tanya harga" },
    thread: [
      { from: "customer", text: "hampers premium 10 box brp kak?" },
      { from: "agent", text: "Halo Kak Sari! Rincian harga 10 box kami kirim lewat Messenger ya." },
      { from: "customer", text: "kartu ucapannya bisa custom?" },
      { from: "agent", text: "Bisa, Kak. Tulisan kartunya boleh dikirim lewat Messenger juga." },
    ],
  },
];

const STEP_MS = 1100;
const AUTO_NEXT_MS = 4500;

type Frame = { count: number; typing: boolean; ms: number };

// Mode percaya penuh: agen mengetik lalu mengirim tanpa kartu izin.
function framesOf(sc: MockScenario): Frame[] {
  const frames: Frame[] = [{ count: 0, typing: false, ms: STEP_MS }];
  sc.thread.forEach((m, i) => {
    if (m.from === "agent") {
      frames.push({ count: i, typing: true, ms: STEP_MS });
    }
    frames.push({ count: i + 1, typing: false, ms: STEP_MS });
  });
  return frames;
}

function lane(i: number, n: number) {
  const y = ((i + 0.5) / n) * 100;
  return `M0 ${y} C 30 ${y}, 22 50, 50 50`;
}

export function HeroStage() {
  const reduced = usePrefersReducedMotion();
  const [active, setActive] = useState(0);
  const [run, setRun] = useState(0);
  const [phase, setPhase] = useState(0);
  const [touched, setTouched] = useState(false);
  const [hovering, setHovering] = useState(false);
  const sc = SCENARIOS[active];
  const frames = framesOf(sc);
  const last = frames.length - 1;

  useEffect(() => {
    if (reduced) return;
    let at = 400;
    const timers = framesOf(SCENARIOS[active]).slice(0, last).map((f, i) => {
      const t = window.setTimeout(() => setPhase(i + 1), at);
      at += f.ms;
      return t;
    });
    return () => timers.forEach(clearTimeout);
  }, [active, run, reduced, last]);

  const frame = frames[reduced ? last : Math.min(phase, last)];
  const finished = reduced || phase >= last;
  const replied = sc.thread.slice(0, frame.count).some((m) => m.from === "agent");
  const status = frame.typing ? "Agen membalas…" : replied ? "Terkirim otomatis" : "Pesan masuk";

  useEffect(() => {
    if (reduced || touched || hovering || !finished) return;
    const t = window.setTimeout(() => {
      setActive((a) => (a + 1) % SCENARIOS.length);
      setPhase(0);
      setRun((r) => r + 1);
    }, AUTO_NEXT_MS);
    return () => clearTimeout(t);
  }, [reduced, touched, hovering, finished]);

  function choose(i: number) {
    setTouched(true);
    setActive(i);
    setPhase(0);
    setRun((r) => r + 1);
  }

  return (
    <div
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      className="grid grid-cols-1 gap-6 text-rc-fg lg:grid-cols-[13rem_minmax(0,1fr)_minmax(0,30rem)] lg:gap-0"
    >
      <div
        role="tablist"
        aria-label="Pilih kanal pesan masuk"
        className="rc-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1 lg:mx-0 lg:flex-col lg:justify-around lg:overflow-visible lg:px-0 lg:pb-0"
      >
        {SCENARIOS.map((s, i) => {
          const on = i === active;
          return (
            <button
              key={s.channel}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => choose(i)}
              className={cn(
                "flex min-h-14 shrink-0 cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 text-left transition-colors duration-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-accent",
                on ? "border-rc-accent bg-rc-surface" : "border-rc-border bg-rc-surface hover:border-rc-border-strong",
              )}
            >
              <LandingChannelIcon channel={s.channel} size="md" />
              <span className="min-w-0">
                <span className="block text-sm font-medium">{landingChannelLabel[s.channel]}</span>
                <span className={cn("block text-xs whitespace-nowrap", on ? "text-rc-accent" : "text-rc-fg-subtle")}>
                  {on ? status : "Lihat contoh"}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      <div className="relative hidden min-h-[34rem] lg:block" aria-hidden>
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="absolute inset-0 h-full w-full overflow-visible">
          {SCENARIOS.map((s, i) => (
            <path
              key={s.channel}
              d={lane(i, SCENARIOS.length)}
              fill="none"
              vectorEffect="non-scaling-stroke"
              className={cn("transition-[stroke] duration-300", i === active ? "stroke-rc-accent" : "stroke-rc-border-strong")}
              strokeWidth={i === active ? 1.75 : 1}
              pathLength={100}
              strokeDasharray={i === active ? undefined : "1.5 2.5"}
            />
          ))}
          <path
            key={`flow-${active}-${run}`}
            d={lane(active, SCENARIOS.length)}
            fill="none"
            vectorEffect="non-scaling-stroke"
            pathLength={100}
            strokeWidth={3}
            strokeLinecap="round"
            className="rc-flow stroke-rc-highlight"
          />
          <path d="M50 50 L100 50" fill="none" vectorEffect="non-scaling-stroke" strokeWidth={1.75} className="stroke-rc-accent" />
          {replied && (
            <path
              key={`out-${active}-${run}`}
              d="M50 50 L100 50"
              fill="none"
              vectorEffect="non-scaling-stroke"
              pathLength={100}
              strokeWidth={3}
              strokeLinecap="round"
              className="rc-flow stroke-rc-highlight"
            />
          )}
        </svg>
        <span className="absolute top-1/2 left-1/2 flex h-16 w-16 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-xl border border-rc-border bg-rc-surface">
          {frame.typing && <span className="rc-ping absolute inset-0 rounded-xl border-2 border-rc-accent" />}
          <LogoMark size={36} />
        </span>
      </div>

      <div key={`${active}-${run}`} className="rc-enter relative" aria-live="polite">
        <ChannelMock sc={sc} count={frame.count} typing={frame.typing} />
      </div>
    </div>
  );
}
