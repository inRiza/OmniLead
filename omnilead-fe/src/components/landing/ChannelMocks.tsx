"use client";

import { useEffect, useRef, type ReactNode } from "react";
import {
  Archive,
  ArrowLeft,
  Bookmark,
  Camera,
  CheckCheck,
  Ellipsis,
  EllipsisVertical,
  Forward,
  Globe,
  Heart,
  Mail,
  MessageCircle,
  Mic,
  Paperclip,
  Phone,
  Reply,
  Send,
  Share2,
  Smile,
  Star,
  ThumbsUp,
  Trash2,
  Video,
} from "lucide-react";
import { LogoMark } from "@/components/brand/Logo";
import type { LandingChannel } from "@/components/landing/channels";
import { cn } from "@/lib/utils";

export type Msg = { from: "customer" | "agent"; text: string };

export type MockScenario = {
  channel: LandingChannel;
  customer: string;
  thread: Msg[];
};

type MockProps = { sc: MockScenario; count: number; typing: boolean };

function Frame({
  header,
  footer,
  bodyClassName,
  tick,
  children,
}: {
  header: ReactNode;
  footer: ReactNode;
  bodyClassName?: string;
  tick: number;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTo({ top: tick === 0 ? 0 : el.scrollHeight, behavior: tick === 0 ? "auto" : "smooth" });
  }, [tick]);
  return (
    <div className="flex h-[34rem] w-full flex-col overflow-hidden rounded-xl border border-rc-border bg-white text-[#0c0c0c]">
      {header}
      <div ref={ref} className={cn("rc-scrollbar min-h-0 flex-1 overflow-y-auto", bodyClassName)}>
        {children}
      </div>
      {footer}
    </div>
  );
}

function Skel({ className }: { className?: string }) {
  return <span className={cn("block rounded-sm bg-black/[0.07]", className)} />;
}

function Initial({ name, className }: { name: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white",
        className,
      )}
    >
      {name.charAt(0).toUpperCase()}
    </span>
  );
}

function Dots() {
  return (
    <span className="inline-flex items-center gap-1" aria-label="Sedang mengetik">
      {[0, 150, 300].map((d) => (
        <span
          key={d}
          className="h-1.5 w-1.5 animate-bounce rounded-full bg-current opacity-60 motion-reduce:animate-none"
          style={{ animationDelay: `${d}ms` }}
        />
      ))}
    </span>
  );
}

function tickOf(count: number, typing: boolean) {
  return count * 2 + (typing ? 1 : 0);
}

function InstagramMock({ sc, count, typing }: MockProps) {
  const shown = sc.thread.slice(0, count);
  return (
    <Frame
      tick={tickOf(count, typing)}
      header={
        <div className="flex h-14 shrink-0 items-center gap-3 border-b border-[#dbdbdb] px-4">
          <span className="rounded-full bg-gradient-to-tr from-[#feda75] via-[#d62976] to-[#4f5bd5] p-[2px]">
            <span className="block rounded-full bg-white p-[2px]">
              <LogoMark size={26} className="rounded-full" />
            </span>
          </span>
          <span className="min-w-0 flex-1 leading-tight">
            <span className="block text-sm font-semibold">OmniLead</span>
            <span className="block text-xs text-[#737373]">Jakarta, Indonesia</span>
          </span>
          <Ellipsis className="h-5 w-5" aria-hidden />
        </div>
      }
      footer={
        <div className="flex h-12 shrink-0 items-center gap-3 border-t border-[#dbdbdb] px-4 text-sm text-[#737373]">
          <Smile className="h-5 w-5 text-[#0c0c0c]" aria-hidden />
          <span className="flex-1">Tambahkan komentar…</span>
          <span className="font-semibold text-[#0095f6]/40">Kirim</span>
        </div>
      }
    >
      <div className="flex aspect-[4/3] items-end bg-gradient-to-br from-[#f3ede4] to-[#e7dccb] p-4">
        <span className="flex flex-col gap-2">
          <Skel className="h-3 w-32 bg-black/10" />
          <Skel className="h-3 w-20 bg-black/10" />
        </span>
      </div>
      <div className="flex items-center gap-4 px-4 pt-3">
        <Heart className="h-6 w-6" aria-hidden />
        <MessageCircle className="h-6 w-6 -scale-x-100" aria-hidden />
        <Send className="h-6 w-6" aria-hidden />
        <Bookmark className="ml-auto h-6 w-6" aria-hidden />
      </div>
      <div className="space-y-1 px-4 pt-2 pb-3 text-sm">
        <p className="font-semibold">1.248 suka</p>
        <p>
          <span className="font-semibold">OmniLead</span> Nasi box komplit untuk acara kantor dan arisan. Pesan
          minimal 30 pax.
        </p>
        <p className="text-[#737373]">Lihat semua 24 komentar</p>
      </div>
      <div className="space-y-4 px-4 pb-5">
        <div className="flex gap-3">
          <Skel className="h-8 w-8 shrink-0 rounded-full" />
          <span className="flex flex-1 flex-col gap-1.5 pt-1">
            <Skel className="h-2.5 w-3/4" />
            <Skel className="h-2 w-16" />
          </span>
        </div>
        {shown.map((m, i) =>
          m.from === "customer" ? (
            <div key={i} className="rc-enter flex gap-3">
              <Initial name={sc.customer} className="h-8 w-8 bg-[#c13584]" />
              <div className="min-w-0 flex-1 text-sm">
                <p>
                  <span className="font-semibold">{sc.customer}</span> {m.text}
                </p>
                <p className="mt-1 flex gap-3 text-xs font-semibold text-[#737373]">
                  <span>1 mnt</span>
                  <span>Balas</span>
                </p>
              </div>
              <Heart className="mt-1 h-3 w-3 text-[#737373]" aria-hidden />
            </div>
          ) : (
            <div key={i} className="rc-enter ml-11 flex gap-3">
              <LogoMark size={28} className="rounded-full" />
              <div className="min-w-0 flex-1 text-sm">
                <p>
                  <span className="font-semibold">OmniLead</span>{" "}
                  <span className="text-[#00376b]">@{sc.customer}</span> {m.text}
                </p>
                <p className="mt-1 flex gap-3 text-xs font-semibold text-[#737373]">
                  <span>Baru saja</span>
                  <span>Dikirim otomatis</span>
                </p>
              </div>
            </div>
          ),
        )}
        {typing && (
          <div className="rc-enter ml-11 flex items-center gap-3 text-[#737373]">
            <LogoMark size={28} className="rounded-full" />
            <Dots />
          </div>
        )}
      </div>
    </Frame>
  );
}

function WhatsAppMock({ sc, count, typing }: MockProps) {
  const shown = sc.thread.slice(0, count);
  return (
    <Frame
      tick={tickOf(count, typing)}
      bodyClassName="bg-[#efeae2] px-4 py-3"
      header={
        <div className="flex h-14 shrink-0 items-center gap-3 bg-[#008069] px-3 text-white">
          <ArrowLeft className="h-5 w-5" aria-hidden />
          <Initial name={sc.customer} className="h-9 w-9 bg-[#25d366]" />
          <span className="min-w-0 flex-1 leading-tight">
            <span className="block text-sm font-semibold">{sc.customer}</span>
            <span className="block text-xs text-white/80">online</span>
          </span>
          <Video className="h-5 w-5" aria-hidden />
          <Phone className="ml-3 h-5 w-5" aria-hidden />
          <EllipsisVertical className="ml-2 h-5 w-5" aria-hidden />
        </div>
      }
      footer={
        <div className="flex h-14 shrink-0 items-center gap-2 bg-[#f0f2f5] px-3">
          <span className="flex h-10 flex-1 items-center gap-3 rounded-full bg-white px-3 text-sm text-[#8696a0]">
            <Smile className="h-5 w-5" aria-hidden />
            <span className="flex-1">Ketik pesan</span>
            <Paperclip className="h-5 w-5" aria-hidden />
            <Camera className="h-5 w-5" aria-hidden />
          </span>
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[#00a884] text-white">
            <Mic className="h-5 w-5" aria-hidden />
          </span>
        </div>
      }
    >
      <p className="mx-auto mb-3 w-fit rounded-md bg-white px-3 py-1 text-xs text-[#54656f] shadow-[0_1px_0.5px_rgba(11,20,26,0.13)]">
        Hari ini
      </p>
      <div className="flex flex-col gap-2">
        <div className="max-w-[75%] self-start rounded-lg rounded-tl-none bg-white px-3 py-2 shadow-[0_1px_0.5px_rgba(11,20,26,0.13)]">
          <Skel className="h-2.5 w-40" />
          <Skel className="mt-1.5 h-2.5 w-24" />
        </div>
        {shown.map((m, i) =>
          m.from === "customer" ? (
            <div
              key={i}
              className="rc-enter max-w-[80%] self-start rounded-lg rounded-tl-none bg-white px-3 py-1.5 text-sm shadow-[0_1px_0.5px_rgba(11,20,26,0.13)]"
            >
              {m.text}
              <span className="float-right mt-2 ml-3 text-[11px] text-[#667781]">10.4{i}</span>
            </div>
          ) : (
            <div
              key={i}
              className="rc-enter max-w-[80%] self-end rounded-lg rounded-tr-none bg-[#d9fdd3] px-3 py-1.5 text-sm shadow-[0_1px_0.5px_rgba(11,20,26,0.13)]"
            >
              <span className="mb-1 flex items-center gap-1.5 text-xs font-medium text-[#027eb5]">
                <LogoMark size={14} />
                OmniLead
                <span className="font-normal text-[#667781]">dikirim otomatis</span>
              </span>
              {m.text}
              <span className="float-right mt-2 ml-3 inline-flex items-center gap-1 text-[11px] text-[#667781]">
                10.4{i}
                <CheckCheck className="h-3.5 w-3.5 text-[#53bdeb]" aria-hidden />
              </span>
            </div>
          ),
        )}
        {typing && (
          <div className="rc-enter flex items-center gap-2 self-end rounded-lg rounded-tr-none bg-[#d9fdd3] px-3 py-2.5 text-[#667781] shadow-[0_1px_0.5px_rgba(11,20,26,0.13)]">
            <LogoMark size={14} />
            <Dots />
          </div>
        )}
      </div>
    </Frame>
  );
}

function GmailMock({ sc, count, typing }: MockProps) {
  const shown = sc.thread.slice(0, count);
  return (
    <Frame
      tick={tickOf(count, typing)}
      header={
        <div className="flex h-12 shrink-0 items-center gap-5 border-b border-[#e0e0e0] px-4 text-[#444746]">
          <ArrowLeft className="h-5 w-5" aria-hidden />
          <Archive className="h-[18px] w-[18px]" aria-hidden />
          <Trash2 className="h-[18px] w-[18px]" aria-hidden />
          <Mail className="h-[18px] w-[18px]" aria-hidden />
          <EllipsisVertical className="ml-auto h-5 w-5" aria-hidden />
        </div>
      }
      footer={
        <div className="flex shrink-0 gap-2 border-t border-[#e0e0e0] px-4 py-3">
          <span className="inline-flex h-9 items-center gap-2 rounded-full border border-[#747775] px-4 text-sm font-medium text-[#444746]">
            <Reply className="h-4 w-4" aria-hidden /> Balas
          </span>
          <span className="inline-flex h-9 items-center gap-2 rounded-full border border-[#747775] px-4 text-sm font-medium text-[#444746]">
            <Forward className="h-4 w-4" aria-hidden /> Teruskan
          </span>
        </div>
      }
    >
      <div className="px-5 pt-4 pb-2">
        <p className="flex flex-wrap items-center gap-2 text-xl text-[#1f1f1f]">
          Penawaran katering 100 pax
          <span className="rounded bg-[#e1e3e1] px-1.5 py-0.5 text-xs text-[#444746]">Kotak Masuk</span>
        </p>
      </div>
      <div className="divide-y divide-[#e0e0e0]">
        {shown.map((m, i) => {
          const agent = m.from === "agent";
          return (
            <div key={i} className="rc-enter flex gap-3 px-5 py-4">
              {agent ? (
                <LogoMark size={36} className="rounded-full" />
              ) : (
                <Initial name={sc.customer} className="h-9 w-9 bg-[#1a73e8] text-sm" />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex items-start gap-2">
                  <p className="min-w-0 flex-1 text-sm leading-tight">
                    <span className="font-semibold text-[#1f1f1f]">{agent ? "OmniLead" : sc.customer}</span>{" "}
                    <span className="text-xs text-[#5e5e5e]">
                      {agent ? "<omnilead@gmail.com>" : "<procurement@nusacorp.co.id>"}
                    </span>
                    <span className="block text-xs text-[#5e5e5e]">
                      kepada {agent ? `${sc.customer}, dikirim otomatis` : "saya"}
                    </span>
                  </p>
                  <span className="text-xs text-[#5e5e5e]">09.1{i}</span>
                  <Star className="h-4 w-4 text-[#5e5e5e]" aria-hidden />
                </div>
                <p className="mt-3 text-sm whitespace-pre-line text-[#1f1f1f]">{m.text}</p>
              </div>
            </div>
          );
        })}
        {typing && (
          <div className="rc-enter flex items-center gap-3 px-5 py-4 text-sm text-[#5e5e5e]">
            <LogoMark size={36} className="rounded-full" />
            <span className="flex-1 rounded-lg border border-[#e0e0e0] px-3 py-3">
              <Dots />
            </span>
          </div>
        )}
        <div className="flex gap-3 px-5 py-4">
          <Skel className="h-9 w-9 shrink-0 rounded-full" />
          <span className="flex flex-1 flex-col gap-1.5 pt-1">
            <Skel className="h-2.5 w-1/3" />
            <Skel className="h-2 w-1/2" />
          </span>
        </div>
      </div>
    </Frame>
  );
}

function FacebookMock({ sc, count, typing }: MockProps) {
  const shown = sc.thread.slice(0, count);
  return (
    <Frame
      tick={tickOf(count, typing)}
      header={
        <div className="flex h-14 shrink-0 items-center gap-3 border-b border-[#ced0d4] px-4">
          <LogoMark size={36} className="rounded-full" />
          <span className="min-w-0 flex-1 leading-tight">
            <span className="block text-sm font-semibold text-[#050505]">OmniLead</span>
            <span className="flex items-center gap-1 text-xs text-[#65676b]">
              2 jam · <Globe className="h-3 w-3" aria-hidden />
            </span>
          </span>
          <Ellipsis className="h-5 w-5 text-[#65676b]" aria-hidden />
        </div>
      }
      footer={
        <div className="flex h-14 shrink-0 items-center gap-2 border-t border-[#ced0d4] px-4">
          <Skel className="h-8 w-8 rounded-full" />
          <span className="flex h-9 flex-1 items-center rounded-full bg-[#f0f2f5] px-3 text-sm text-[#65676b]">
            Tulis komentar…
          </span>
          <Send className="h-5 w-5 text-[#bcc0c4]" aria-hidden />
        </div>
      }
    >
      <p className="px-4 pt-3 text-sm text-[#050505]">
        Hampers Premium edisi akhir tahun sudah bisa dipesan. Isi kue kering, teh, dan kartu ucapan custom.
      </p>
      <div className="mt-3 flex aspect-[16/10] items-center justify-center bg-gradient-to-br from-[#fde8d7] to-[#f6c9a8]">
        <Skel className="h-16 w-16 rounded-lg bg-white/50" />
      </div>
      <div className="flex items-center justify-between px-4 py-2 text-sm text-[#65676b]">
        <span className="flex items-center gap-1.5">
          <span className="inline-flex h-[18px] w-[18px] items-center justify-center rounded-full bg-[#1877f2] text-white">
            <ThumbsUp className="h-2.5 w-2.5 fill-current" aria-hidden />
          </span>
          86
        </span>
        <span>12 komentar · 3 kali dibagikan</span>
      </div>
      <div className="mx-4 grid grid-cols-3 border-y border-[#ced0d4] py-1 text-sm font-semibold text-[#65676b]">
        <span className="flex items-center justify-center gap-2 py-1.5">
          <ThumbsUp className="h-4 w-4" aria-hidden /> Suka
        </span>
        <span className="flex items-center justify-center gap-2 py-1.5">
          <MessageCircle className="h-4 w-4" aria-hidden /> Komentari
        </span>
        <span className="flex items-center justify-center gap-2 py-1.5">
          <Share2 className="h-4 w-4" aria-hidden /> Bagikan
        </span>
      </div>
      <div className="space-y-3 px-4 py-4">
        <div className="flex gap-2">
          <Skel className="h-8 w-8 shrink-0 rounded-full" />
          <span className="flex w-2/3 flex-col gap-1.5 rounded-2xl bg-[#f0f2f5] px-3 py-2.5">
            <Skel className="h-2.5 w-20" />
            <Skel className="h-2 w-full" />
          </span>
        </div>
        {shown.map((m, i) =>
          m.from === "customer" ? (
            <div key={i} className="rc-enter flex gap-2">
              <Initial name={sc.customer} className="h-8 w-8 bg-[#1877f2]" />
              <div className="min-w-0">
                <p className="rounded-2xl bg-[#f0f2f5] px-3 py-2 text-sm text-[#050505]">
                  <span className="block text-[13px] font-semibold">{sc.customer}</span>
                  {m.text}
                </p>
                <p className="mt-0.5 flex gap-3 px-3 text-xs font-semibold text-[#65676b]">
                  <span>3 mnt</span>
                  <span>Suka</span>
                  <span>Balas</span>
                </p>
              </div>
            </div>
          ) : (
            <div key={i} className="rc-enter ml-10 flex gap-2">
              <LogoMark size={28} className="rounded-full" />
              <div className="min-w-0">
                <p className="rounded-2xl bg-[#f0f2f5] px-3 py-2 text-sm text-[#050505]">
                  <span className="block text-[13px] font-semibold">OmniLead</span>
                  {m.text}
                </p>
                <p className="mt-0.5 flex gap-3 px-3 text-xs font-semibold text-[#65676b]">
                  <span>Baru saja</span>
                  <span>Dikirim otomatis</span>
                </p>
              </div>
            </div>
          ),
        )}
        {typing && (
          <div className="rc-enter ml-10 flex items-center gap-2 text-[#65676b]">
            <LogoMark size={28} className="rounded-full" />
            <span className="rounded-2xl bg-[#f0f2f5] px-3 py-2.5">
              <Dots />
            </span>
          </div>
        )}
      </div>
    </Frame>
  );
}

export function ChannelMock(props: MockProps) {
  switch (props.sc.channel) {
    case "instagram":
      return <InstagramMock {...props} />;
    case "whatsapp":
      return <WhatsAppMock {...props} />;
    case "email":
      return <GmailMock {...props} />;
    case "facebook":
      return <FacebookMock {...props} />;
  }
}
