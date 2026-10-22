"use client";

import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { AgentChat } from "@/components/dashboard/AgentChat";
import { useDashboard } from "@/components/dashboard/DashboardContext";

export default function AgenPage() {
  const d = useDashboard();
  return (
    <>
      <Topbar title="Agen" subtitle="Satu percakapan untuk mengelola pelanggan Anda." />
      <ContentInset className="flex pl-3 md:pl-0">
        <AgentChat onChanged={d.refresh} className="h-full w-full" />
      </ContentInset>
    </>
  );
}
