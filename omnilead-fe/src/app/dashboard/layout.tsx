import type { ReactNode } from "react";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <DashboardProvider>
      <div className="flex h-dvh overflow-hidden bg-rc-bg text-rc-fg">
        <Sidebar />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3 bg-rc-bg pr-4 pb-4 pt-0 [&>*:last-child]:min-h-0 [&>*:last-child]:flex-1">
          {children}
        </div>
      </div>
    </DashboardProvider>
  );
}
