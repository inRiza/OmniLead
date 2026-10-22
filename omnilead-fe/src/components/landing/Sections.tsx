"use client";

import { useEffect, useRef, useState, type ComponentType, type ReactNode, type SVGProps } from "react";
import {
  ArrowRight,
  BellRing,
  Bot,
  Check,
  CheckCheck,
  ChevronsLeftRight,
  MessageCircleQuestion,
  ShieldCheck,
  Users,
} from "lucide-react";
import Image from "next/image";
import { LogoMark } from "@/components/brand/Logo";
import { usePrefersReducedMotion } from "@/components/landing/Interactive";
import { ChannelIcon } from "@/components/primitives";
import type { Channel } from "@/lib/types";
import { cn } from "@/lib/utils";

type Icon = ComponentType<SVGProps<SVGSVGElement>>;

const focusRing = "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rc-accent";

const WHY_ROWS = [
  {
    ask: "brp harga nasbox 30 org kak?",
    bot: "Maaf, saya tidak mengerti. Ketik 1 untuk Menu, 2 untuk Promo.",
    agent: "Halo Kak! Nasi box komplit Rp35.000 per porsi, jadi Rp1.050.000 untuk 30 orang. Mau untuk tanggal berapa?",
  },
  {
    ask: "bisa kirim tgl 30 ke kantor?",
    bot: "Pilihan tidak valid. Silakan ketik 1 atau 2.",
    agent: "Bisa, Kak. Tanggal 30 masih kosong, kami antar sebelum jam makan siang.",
  },
  {
    ask: "ada diskon kalo ambil banyak?",
    bot: "Promo hari ini: tidak tersedia. Ketik MENU untuk kembali.",
    agent: "Untuk 30 porsi ada potongan 5%, Kak. Totalnya jadi Rp997.500.",
  },
  {
    ask: "oke kak, aku pesan ya",
    bot: "Terima kasih telah menghubungi kami. Sesi Anda telah berakhir.",
    agent: "Siap, Kak! Pesanannya kami catat, rincian pembayaran segera kami kirim.",
  },
];

const ANI_AVATAR = "https://api.dicebear.com/9.x/notionists/svg?seed=Ani&backgroundColor=ffd5dc";

const bubble = "max-w-[85%] w-fit rounded-lg px-3 py-2 text-sm leading-relaxed";

const TYPE_MS = 700;
const ROW_MS = 1300;
const START = 94;
const END = 3;
const SWEEP_MS = 1800;

function Dots() {
  return (
    <span className="inline-flex h-5 items-center gap-1" aria-label="Sedang mengetik">
      {[0, 150, 300].map((d) => (
        <span
          key={d}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-current opacity-50 motion-reduce:animate-none"
          style={{ animationDelay: `${d}ms` }}
        />
      ))}
    </span>
  );
}

export function WhyToggle() {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = usePrefersReducedMotion();
  const [started, setStarted] = useState(false);
  const [rawStep, setStep] = useState(0);
  const [rawPos, setPos] = useState(START);
  const [sweeping, setSweeping] = useState(false);
  const total = WHY_ROWS.length * 2;

  useEffect(() => {
    const el = ref.current;
    if (!el || reduced) return;
    const io = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) {
          setStarted(true);
          io.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduced]);

  useEffect(() => {
    if (!started) return;
    const timers: number[] = [];
    WHY_ROWS.forEach((_, i) => {
      timers.push(window.setTimeout(() => setStep(i * 2 + 1), i * ROW_MS));
      timers.push(window.setTimeout(() => setStep(i * 2 + 2), i * ROW_MS + TYPE_MS));
    });
    const end = (WHY_ROWS.length - 1) * ROW_MS + TYPE_MS + 400;
    timers.push(window.setTimeout(() => setSweeping(true), end));
    timers.push(window.setTimeout(() => setPos(END), end + 50));
    timers.push(window.setTimeout(() => setSweeping(false), end + 100 + SWEEP_MS));
    return () => timers.forEach(clearTimeout);
  }, [started]);

  const step = reduced ? total : rawStep;
  const pos = reduced && rawPos === START ? END : rawPos;
  const clip = { clipPath: `inset(0 0 0 ${pos}%)` };
  const clipBot = { clipPath: `inset(0 ${100 - pos}% 0 0)` };
  const ease = sweeping ? "duration-[1800ms] ease-in-out" : "duration-0";

  return (
    <div className="mx-auto max-w-3xl overflow-hidden rounded-xl bg-[#eef1f6] select-none">
      <div ref={ref} className="relative">
        <div className="grid">
          <div className="col-start-1 row-start-1 flex justify-start bg-[#eef1f6] px-4 pt-4 sm:px-6">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-black/[0.05] px-2.5 py-1 text-xs font-medium text-rc-fg-muted">
              <Bot className="h-3.5 w-3.5" aria-hidden /> Chatbot biasa
            </span>
          </div>
          <div
            className={cn("col-start-1 row-start-1 flex justify-end bg-[#eef1f6] px-4 pt-4 transition-[clip-path] sm:px-6", ease)}
            style={clip}
          >
            <span className="inline-flex items-center gap-1.5 rounded-md bg-rc-accent/10 px-2.5 py-1 text-xs font-medium text-rc-accent">
              <LogoMark size={14} /> OmniLead
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-3 pb-5">
          {WHY_ROWS.map((r, i) => {
            const visible = step >= i * 2 + 1;
            const typing = step === i * 2 + 1;
            return (
              <div key={r.ask} className={cn("transition-opacity duration-500", visible ? "opacity-100" : "opacity-0")}>
                <div className="grid">
                  <div
                    className={cn(
                      "col-start-1 row-start-1 flex justify-end bg-[#eef1f6] px-4 opacity-55 transition-[clip-path] sm:px-6",
                      ease,
                    )}
                    style={clipBot}
                  >
                    <p className={cn(bubble, "rounded-tr-none bg-[#dde1e8] text-sm text-rc-fg-muted")}>
                      {typing ? <Dots /> : <span className={visible ? "rc-enter inline" : "invisible"}>{r.bot}</span>}
                    </p>
                  </div>
                  <div
                    className={cn("col-start-1 row-start-1 flex justify-end bg-[#eef1f6] px-4 transition-[clip-path] sm:px-6", ease)}
                    style={clip}
                  >
                    <p className={cn(bubble, "rounded-tr-none bg-[#d8e4ff] text-rc-fg")}>
                      {typing ? (
                        <Dots />
                      ) : (
                        <span className={visible ? "rc-enter inline" : "invisible"}>
                          {r.agent}
                          <span className="float-right mt-1.5 ml-3 inline-flex items-center gap-1 text-[11px] text-rc-fg-subtle">
                            10.0{i}
                            <CheckCheck className="h-3.5 w-3.5 text-rc-accent" aria-hidden />
                          </span>
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div
          aria-hidden
          className={cn("pointer-events-none absolute inset-0 transition-transform", ease)}
          style={{ transform: `translateX(${pos}%)` }}
        >
          <span className="absolute inset-y-0 left-0 w-px -translate-x-1/2 bg-rc-accent/60" />
          <span className="absolute top-[1.65rem] left-0 inline-flex h-7 w-7 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-rc-accent text-rc-accent-fg">
            <ChevronsLeftRight className="h-4 w-4" />
          </span>
        </div>

        <input
          type="range"
          min={0}
          max={100}
          value={pos}
          onChange={(e) => {
            setSweeping(false);
            setPos(Number(e.target.value));
          }}
          aria-label="Geser untuk membandingkan chatbot biasa dan OmniLead"
          className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
        />
      </div>
    </div>
  );
}

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

const skillCard = "rounded-lg bg-white px-4 py-3 text-sm text-rc-fg";

const TONES = {
  blue: { bg: "bg-rc-accent/15", ink: "text-rc-accent" },
  amber: { bg: "bg-amber-400/30", ink: "text-amber-700" },
};

function Note({ children, label, i, tone }: { children: ReactNode; label: string; i: number; tone: keyof typeof TONES }) {
  const d = 450 + i * 420;
  const t = TONES[tone];
  return (
    <span className="relative mx-0.5 inline-block px-1 leading-6">
      <span
        aria-hidden
        className={cn("rc-progress absolute inset-0 origin-left rounded", t.bg)}
        style={{ animationDuration: "350ms", animationDelay: `${d}ms` }}
      />
      <span className="relative">{children}</span>
      <span
        className={cn("rc-enter absolute top-full left-1 mt-1 text-[11px] leading-4 font-medium whitespace-nowrap", t.ink)}
        style={{ animationDelay: `${d + 180}ms` }}
      >
        {label}
      </span>
    </span>
  );
}

function Later({ ms, children, className }: { ms: number; children: ReactNode; className?: string }) {
  return (
    <div className={cn("rc-enter", className)} style={{ animationDelay: `${ms}ms` }}>
      {children}
    </div>
  );
}

function SkillVisual({ k }: { k: string }) {
  if (k === "konteks")
    return (
      <div className="flex w-full max-w-md flex-col gap-3">
        <Later ms={0} className="flex items-center gap-2 text-xs text-rc-fg-muted">
          <ChannelIcon channel="whatsapp" /> Pesan masuk dari Ani
        </Later>
        <Later ms={120}>
          <p className={cn(skillCard, "rounded-tl-none pt-2 pb-6 leading-[3.5rem]")}>
            <Note i={0} tone="blue" label="tanya harga">
              brp harga
            </Note>{" "}
            <Note i={1} tone="blue" label="nasi box">
              nasbox
            </Note>{" "}
            <Note i={2} tone="blue" label="30 porsi">
              30 org
            </Note>{" "}
            <Note i={3} tone="blue" label="2 November">
              tgl 2 nov
            </Note>{" "}
            kak?
          </p>
        </Later>
        <Later ms={2350} className="text-sm text-rc-fg-muted">
          Dipahami sebagai <span className="font-medium text-rc-fg">permintaan harga nasi box untuk 30 orang, 2 November.</span>
        </Later>
      </div>
    );
  if (k === "cek")
    return (
      <div className="flex w-full max-w-md flex-col gap-3">
        <Later ms={0} className="flex items-center gap-2 text-xs text-rc-fg-muted">
          <LogoMark size={18} /> Draf balasan untuk Ani
        </Later>
        <Later ms={120}>
          <p className={cn(skillCard, "rounded-tr-none pt-2 pb-6 leading-[3.5rem]")}>
            Nasi box komplit{" "}
            <Note i={0} tone="amber" label="sesuai katalog">
              Rp35.000
            </Note>{" "}
            per porsi, untuk 30 orang{" "}
            <Note i={1} tone="amber" label="hitungan benar">
              Rp1.050.000
            </Note>
            . Ada{" "}
            <Note i={2} tone="amber" label="di bawah batas 5%">
              diskon 5%
            </Note>{" "}
            untuk{" "}
            <Note i={3} tone="amber" label="hanya data Ani">
              Kak Ani
            </Note>
            .
          </p>
        </Later>
        <Later ms={2350} className="flex items-center gap-2 text-sm font-medium text-amber-700">
          <Check className="h-4 w-4" aria-hidden /> Lolos semua pengecekan, dikirim otomatis
        </Later>
      </div>
    );
  if (k === "profil")
    return (
      <div className="flex w-full max-w-md flex-col items-center gap-4 sm:flex-row sm:items-center">
        <div className="flex w-full flex-col gap-2 sm:w-auto">
          {(
            [
              ["instagram", "@ani.majujaya"],
              ["whatsapp", "+62 812 3456 7890"],
              ["email", "ani@majujaya.co.id"],
            ] as [Channel, string][]
          ).map(([c, id], i) => (
            <Later key={c} ms={i * 260}>
              <span className="flex items-center gap-2.5 rounded-lg bg-white/70 px-3 py-2 text-sm text-rc-fg-muted">
                <ChannelIcon channel={c} />
                {id}
              </span>
            </Later>
          ))}
        </div>
        <Later ms={900} className="hidden sm:block">
          <ArrowRight className="h-5 w-5 text-rc-navy/40" aria-hidden />
        </Later>
        <Later ms={1150} className="w-full sm:w-auto sm:flex-1">
          <div className={cn(skillCard, "flex items-center gap-3")}>
            <Image src={ANI_AVATAR} alt="" width={48} height={48} unoptimized className="h-12 w-12 shrink-0 rounded-full" />
            <div className="min-w-0">
              <p className="font-semibold">Ani Rahmawati</p>
              <p className="mt-2 flex flex-wrap gap-1.5">
                {["PT Maju Jaya", "3 kanal"].map((b, i) => (
                  <span
                    key={b}
                    className="rc-pop inline-flex rounded-md bg-rc-navy/[0.07] px-2 py-0.5 text-xs font-medium text-rc-navy"
                    style={{ animationDelay: `${1400 + i * 150}ms` }}
                  >
                    {b}
                  </span>
                ))}
                <span
                  className="rc-pop inline-flex rounded-md bg-rc-highlight px-2 py-0.5 text-xs font-medium text-rc-navy"
                  style={{ animationDelay: "1700ms" }}
                >
                  Hot 86
                </span>
              </p>
            </div>
          </div>
        </Later>
      </div>
    );
  return (
    <div className="flex w-full max-w-md flex-col gap-2">
      <Later ms={0}>
        <div className={cn(skillCard, "flex items-center gap-3")}>
          <LogoMark size={32} />
          <span className="min-w-0 flex-1">
            <span className="block font-medium">Penawaran terkirim ke Ani</span>
            <span className="block text-xs text-rc-fg-muted">Hari ini, 14.20</span>
          </span>
        </div>
      </Later>
      <Later ms={400}>
        <div className={cn(skillCard, "rc-dim flex items-center gap-3")} style={{ animationDelay: "2000ms" }}>
          <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
            <BellRing className="h-4 w-4" aria-hidden />
          </span>
          <span className="min-w-0 flex-1">
            <span className="relative block w-fit font-medium">
              Hubungi Ani lagi
              <span
                aria-hidden
                className="rc-progress absolute top-1/2 left-0 h-px w-full origin-left bg-rc-fg"
                style={{ animationDuration: "400ms", animationDelay: "2000ms" }}
              />
            </span>
            <span className="block text-xs text-rc-fg-muted">Besok, 10.00</span>
          </span>
          <span className="rc-enter text-xs font-medium text-emerald-700" style={{ animationDelay: "2300ms" }}>
            Dibatalkan otomatis
          </span>
        </div>
      </Later>
      <Later ms={1300}>
        <div className={cn(skillCard, "flex items-center gap-3")}>
          <Image src={ANI_AVATAR} alt="" width={32} height={32} unoptimized className="h-8 w-8 shrink-0 rounded-full" />
          <span className="min-w-0 flex-1">
            <span className="block font-medium">Ani membalas: &ldquo;oke kak, jadi pesan ya&rdquo;</span>
            <span className="block text-xs text-rc-fg-muted">Hari ini, 16.05</span>
          </span>
        </div>
      </Later>
    </div>
  );
}

const SKILL_MS = 6000;

export function SkillsExplorer() {
  const [active, setActive] = useState(SKILLS[0].key);
  const [touched, setTouched] = useState(false);
  const [paused, setPaused] = useState(false);
  const sk = SKILLS.find((s) => s.key === active) ?? SKILLS[0];

  function next() {
    const i = SKILLS.findIndex((s) => s.key === active);
    setActive(SKILLS[(i + 1) % SKILLS.length].key);
  }

  return (
    <div
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]"
    >
      <div role="tablist" aria-label="Kemampuan AI" aria-orientation="vertical" className="flex flex-col">
        {SKILLS.map((s) => {
          const on = s.key === active;
          return (
            <button
              key={s.key}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => {
                setTouched(true);
                setActive(s.key);
              }}
              className={cn(
                "relative cursor-pointer overflow-hidden border-t border-rc-border py-5 pr-4 pl-5 text-left transition-colors duration-300 last:border-b",
                focusRing,
                on ? "bg-rc-bg" : "hover:bg-rc-bg/60",
              )}
            >
              <span aria-hidden className={cn("absolute inset-y-0 left-0 w-0.5 transition-colors duration-300", on ? "bg-rc-accent" : "bg-transparent")} />
              <span className="flex items-center gap-3">
                <span
                  className={cn(
                    "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors duration-300",
                    on ? cn(s.tint, s.ink) : "bg-rc-bg text-rc-fg-muted",
                  )}
                >
                  <s.icon className="h-[18px] w-[18px]" aria-hidden />
                </span>
                <span className={cn("text-base font-semibold tracking-tight transition-colors duration-300", on ? "text-rc-fg" : "text-rc-fg-muted")}>
                  {s.title}
                </span>
              </span>
              <span
                className={cn(
                  "grid transition-[grid-template-rows,opacity,margin] duration-500 ease-out",
                  on ? "mt-2 grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0",
                )}
              >
                <span className="overflow-hidden pl-12 text-sm text-rc-fg-muted">{s.body}</span>
              </span>
              {on && !touched && (
                <span
                  aria-hidden
                  onAnimationEnd={next}
                  className="rc-progress absolute bottom-0 left-0 h-0.5 w-full origin-left bg-rc-accent/40"
                  style={{ animationDuration: `${SKILL_MS}ms`, animationPlayState: paused ? "paused" : "running" }}
                />
              )}
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        aria-label={sk.title}
        className={cn("flex min-h-[22rem] items-center justify-center rounded-xl p-6 transition-colors duration-500 sm:p-10", sk.tint)}
      >
        <div key={sk.key} className="rc-panel flex w-full justify-center">
          <SkillVisual k={sk.key} />
        </div>
      </div>
    </div>
  );
}
