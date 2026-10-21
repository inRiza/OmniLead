import { Suspense, type ReactNode } from "react";
import { MobileNav, Sidebar } from "@/components/dashboard/Sidebar";
import { DashboardProvider } from "@/components/dashboard/DashboardContext";
import { AccountProvider } from "@/components/dashboard/AccountProvider";

// Session-gated pages become available after checking the current account.
export const instant = false;

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <AccountProvider><DashboardProvider>
      <div className="rc-brand flex h-dvh overflow-hidden bg-rc-bg text-rc-fg">
        <Suspense fallback={<aside className="hidden h-full w-60 shrink-0 md:block" />}>
          <Sidebar />
        </Suspense>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-3 bg-rc-bg px-3 pt-0 pb-20 md:px-6 md:pb-4 [&>*:last-child]:min-h-0 [&>*:last-child]:flex-1">
          {children}
        </div>
        <MobileNav />
      </div>
    </DashboardProvider></AccountProvider>
  );
}
