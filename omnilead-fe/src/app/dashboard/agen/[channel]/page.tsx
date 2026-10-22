"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { InstagramAgent } from "@/components/dashboard/InstagramAgent";
import { useDashboard } from "@/components/dashboard/DashboardContext";

export default function AgenChannelPage() {
  const { channel } = useParams<{ channel: string }>();
  const d = useDashboard();
  return (
    <>
      <Topbar title="Agen Instagram" subtitle="Agen membaca pesan baru lalu menyiapkan balasan." />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 p-5 md:p-6">
          <Link href="/dashboard/agen" className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-rc-fg-muted transition-colors hover:text-rc-fg">
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Semua kanal
          </Link>
          {channel === "instagram" ? (
            <InstagramAgent onFinished={d.refresh} />
          ) : (
            <p className="rounded-xl border border-dashed border-rc-border-strong px-5 py-10 text-center text-sm text-rc-fg-muted">
              Kanal ini belum tersedia untuk agen.
            </p>
          )}
        </div>
      </ContentInset>
    </>
  );
}
