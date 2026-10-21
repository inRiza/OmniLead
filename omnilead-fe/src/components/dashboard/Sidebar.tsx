"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, SVGProps } from "react";
import { Logo } from "@/components/brand/Logo";
import { cn } from "@/lib/utils";
import { useDashboard } from "./DashboardContext";
import { useAccount } from "./AccountProvider";
import { LogoutButton } from "./LogoutButton";
import {
  HomeIcon,
  InboxIcon,
  ListIcon,
  PlugIcon,
  SparkIcon,
  UsersIcon,
} from "./icons";

type NavItem = {
  href: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  badge?: number;
};

const main: NavItem[] = [
  { href: "/dashboard", label: "Beranda", icon: HomeIcon },
  { href: "/dashboard/inbox", label: "Workspace", icon: InboxIcon },
  { href: "/dashboard/agent", label: "Aktivitas agen", icon: SparkIcon },
  { href: "/dashboard/leads", label: "Lead", icon: UsersIcon },
  { href: "/dashboard/konten", label: "Konten", icon: SparkIcon },
];

const secondary: NavItem[] = [
  { href: "/dashboard/knowledge", label: "Pengetahuan & Tone", icon: SparkIcon },
  { href: "/dashboard/integrasi", label: "Integrasi", icon: PlugIcon },
  { href: "/dashboard/audit", label: "Audit", icon: ListIcon },
];

export function Sidebar() {
  const pathname = usePathname();
  const { pendingCount } = useDashboard();
  const { session } = useAccount();
  const user = session.user;
  const withBadge = (items: NavItem[]): NavItem[] =>
    items.map((i) =>
      i.href === "/dashboard/inbox" ? { ...i, badge: pendingCount } : i,
    );

  function isActive(href: string): boolean {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  return (
    <aside className="rc-scrollbar hidden h-full w-60 shrink-0 flex-col bg-rc-bg md:flex">
      <Link href="/" className="flex min-h-14 shrink-0 items-center px-4 py-3">
        <Logo />
      </Link>

      <nav className="flex flex-1 flex-col gap-5 px-2 py-1">
        <NavGroup items={withBadge(main)} isActive={isActive} />
        <div>
          <p className="px-2.5 pb-1 text-sm font-medium text-rc-fg-subtle">
            Pengaturan
          </p>
          <NavGroup items={secondary} isActive={isActive} />
        </div>
      </nav>

      <div className="p-3 pt-0">
        <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-rc-border bg-rc-primary text-sm font-semibold text-rc-primary-fg">
            {user ? user.name.slice(0, 2).toUpperCase() : "OL"}
          </div>
          <div className="min-w-0 leading-tight">
            <div className="truncate text-sm font-medium text-rc-fg">
              {user?.name ?? "Demo OmniLead"}
            </div>
            <div className="truncate text-sm text-rc-fg-muted">
              {user?.business ?? "Lingkungan lokal"}
            </div>
          </div>
        </div>
        <LogoutButton className="mt-2" />
      </div>
    </aside>
  );
}

function NavGroup({
  items,
  isActive,
}: {
  items: NavItem[];
  isActive: (href: string) => boolean;
}) {
  return (
    <ul className="flex flex-col gap-0.5">
      {items.map((item) => {
        const active = isActive(item.href);
        const Icon = item.icon;
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-rc-surface-hover text-rc-fg"
                  : "text-rc-fg-muted hover:bg-rc-surface-hover/70 hover:text-rc-fg",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="flex-1">{item.label}</span>
              {item.badge ? (
                <span
                  className={cn(
                    "rounded-md px-1.5 py-0.5 text-sm font-medium tabular-nums",
                    active
                      ? "bg-rc-border/60 text-rc-fg"
                      : "bg-rc-surface-hover text-rc-fg-muted",
                  )}
                >
                  {item.badge}
                </span>
              ) : null}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
