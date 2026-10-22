"use client";

import Link from "next/link";
import { useDashboard } from "./DashboardContext";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";
import { LogoutButton } from "./LogoutButton";
import { MobileNav } from "./Sidebar";

export function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  const { paused, error, agent } = useDashboard();

  return (
    <header className="shrink-0 bg-rc-bg">
      <div className="flex min-h-16 flex-wrap items-center justify-between gap-3 py-3 pr-1 pl-1 md:pl-0">
        <div className="flex min-w-0 items-center gap-2">
          <MobileNav />
          <div className="min-w-0">
            <h1 className="text-lg font-semibold tracking-tight text-rc-fg">{title}</h1>
            {subtitle ? <p className="text-sm leading-snug text-rc-fg-muted">{subtitle}</p> : null}
          </div>
        </div>

        <div className="ml-auto flex max-w-full items-center gap-2">
          <WorkspaceSwitcher />
          <LogoutButton inline className="md:hidden" />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        {error ? (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            Backend tidak terhubung. {error}. Data di layar mungkin sudah usang.
          </p>
        ) : null}
        {!error && agent && !agent.reachable ? (
          <p role="alert" className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Service agen tidak terjangkau. Pesan baru akan ditandai dan bisa dianalisis ulang setelah agen menyala.
          </p>
        ) : null}
        {paused ? (
          <p role="status" className="flex flex-wrap items-center justify-center gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800">
            Agen sedang dijeda. Semua aksi ditahan.
            <Link href="/dashboard/pengaturan" className="underline">
              Buka pengaturan
            </Link>
          </p>
        ) : null}
      </div>
    </header>
  );
}
