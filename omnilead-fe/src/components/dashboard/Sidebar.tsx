"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentType, SVGProps } from "react";
import { cn } from "@/lib/utils";
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
  { href: "/dashboard/inbox", label: "Workspace", icon: InboxIcon, badge: 3 },
  { href: "/dashboard/leads", label: "Lead", icon: UsersIcon },
  { href: "/dashboard/konten", label: "Konten", icon: SparkIcon },
];

const secondary: NavItem[] = [
  { href: "/dashboard/integrasi", label: "Integrasi", icon: PlugIcon },
  { href: "/dashboard/audit", label: "Audit", icon: ListIcon },
];

export function Sidebar() {
  const pathname = usePathname();

  function isActive(href: string): boolean {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  return (
    <aside className="rc-scrollbar hidden h-full w-60 shrink-0 flex-col bg-rc-bg md:flex">
      <div className="flex min-h-14 shrink-0 items-center gap-2.5 px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-rc-primary text-xs font-semibold text-rc-primary-fg">
          O
        </div>
        <span className="text-base font-semibold tracking-tight text-rc-fg">
          OmniLead
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-5 px-2 py-1">
        <NavGroup items={main} isActive={isActive} />
        <div>
          <p className="px-2.5 pb-1 text-xs font-medium text-rc-fg-subtle">
            Pengaturan
          </p>
          <NavGroup items={secondary} isActive={isActive} />
        </div>
      </nav>

      <div className="p-3 pt-0">
        <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-rc-border bg-rc-primary text-xs font-semibold text-rc-primary-fg">
            BR
          </div>
          <div className="min-w-0 leading-tight">
            <div className="truncate text-sm font-medium text-rc-fg">
              Bu Rina
            </div>
            <div className="truncate text-xs text-rc-fg-muted">
              Katering &amp; hampers
            </div>
          </div>
        </div>
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
                    "rounded-md px-1.5 py-0.5 text-xs font-medium tabular-nums",
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
