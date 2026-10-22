"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { Channel } from "@/lib/types";
import { channelLabel } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { ChannelIcon } from "@/components/primitives";

const CHANNELS: { channel: Channel; detail: string; ready: boolean }[] = [
  { channel: "instagram", detail: "DM dan komentar", ready: true },
  { channel: "whatsapp", detail: "Pesan WhatsApp Business", ready: false },
  { channel: "facebook", detail: "Messenger dan komentar", ready: false },
  { channel: "email", detail: "Kotak masuk email", ready: false },
];

export default function AgenPage() {
  return (
    <>
      <Topbar title="Agen" subtitle="Pilih kanal yang ingin dibaca dan dijawab agen." />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-2 p-5 md:p-6">
          {CHANNELS.map(({ channel, detail, ready }) => {
            const body = (
              <>
                <ChannelIcon channel={channel} size="md" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-rc-fg">{channelLabel[channel]}</p>
                  <p className="text-xs text-rc-fg-muted">{detail}</p>
                </div>
                {ready ? (
                  <ChevronRight aria-hidden className="h-4 w-4 text-rc-fg-subtle transition-transform group-hover:translate-x-0.5" />
                ) : (
                  <span className="text-xs text-rc-fg-subtle">Segera hadir</span>
                )}
              </>
            );
            return ready ? (
              <Link
                key={channel}
                href={`/dashboard/agen/${channel}`}
                className="group flex items-center gap-3 rounded-xl border border-rc-border bg-rc-surface px-4 py-3.5 transition-colors hover:border-rc-accent/40"
              >
                {body}
              </Link>
            ) : (
              <div key={channel} aria-disabled className="flex cursor-not-allowed items-center gap-3 rounded-xl border border-rc-border bg-rc-surface px-4 py-3.5 opacity-50">
                {body}
              </div>
            );
          })}
        </div>
      </ContentInset>
    </>
  );
}
