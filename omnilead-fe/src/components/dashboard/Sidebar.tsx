"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ComponentType, type SVGProps } from "react";
import {
  Activity,
  BookOpen,
  House,
  Inbox,
  Lightbulb,
  Menu,
  Plug,
  ScrollText,
  Users,
  X,
} from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { cn } from "@/lib/utils";
import { useDashboard } from "./DashboardContext";
import { useAccount } from "./AccountProvider";
import { LogoutButton } from "./LogoutButton";

type NavItem = {
  href: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  badge?: number;
};

const main: NavItem[] = [
  { href: "/dashboard", label: "Beranda", icon: House },
  { href: "/dashboard/inbox", label: "Workspace", icon: Inbox },
  { href: "/dashboard/agent", label: "Aktivitas agen", icon: Activity },
  { href: "/dashboard/leads", label: "Lead", icon: Users },
  { href: "/dashboard/konten", label: "Konten", icon: Lightbulb },
];

const secondary: NavItem[] = [
  { href: "/dashboard/knowledge", label: "Pengetahuan & Tone", icon: BookOpen },
  { href: "/dashboard/integrasi", label: "Integrasi", icon: Plug },
  { href: "/dashboard/audit", label: "Audit", icon: ScrollText },
];

function useNav() {
  const pathname = usePathname();
  const { pendingCount } = useDashboard();
  const withBadge = (items: NavItem[]): NavItem[] =>
    items.map((i) =>
      i.href === "/dashboard/inbox" ? { ...i, badge: pendingCount } : i,
    );
  function isActive(href: string): boolean {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }
  return { main: withBadge(main), isActive };
}

export function Sidebar() {
  const { session } = useAccount();
  const user = session.user;
  const nav = useNav();

  return (
    <aside className="rc-scrollbar hidden h-full w-60 shrink-0 flex-col bg-rc-bg md:flex">
      <Link href="/" className="flex min-h-14 shrink-0 items-center px-4 py-3">
        <Logo />
      </Link>

      <nav className="flex flex-1 flex-col gap-5 px-2 py-1">
        <NavGroup items={nav.main} isActive={nav.isActive} />
        <div>
          <p className="px-2.5 pb-1 text-sm font-medium text-rc-fg-subtle">
            Pengaturan
          </p>
          <NavGroup items={secondary} isActive={nav.isActive} />
        </div>
      </nav>

      <div className="p-3 pt-0">
        <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-rc-navy text-sm font-semibold text-white">
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
                  ? "bg-rc-accent-soft text-rc-accent"
                  : "text-rc-fg-muted hover:bg-rc-surface-hover hover:text-rc-fg",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="flex-1">{item.label}</span>
              {item.badge ? (
                <span
                  className={cn(
                    "rounded-md px-1.5 py-0.5 text-sm font-medium tabular-nums",
                    active
                      ? "bg-rc-accent text-white"
                      : "bg-rc-highlight-soft text-[#8a5300]",
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

// Navigasi ponsel: empat menu utama di bawah layar, sisanya lewat tombol Menu.
export function MobileNav() {
  const nav = useNav();
  const [open, setOpen] = useState(false);
  const pinned = nav.main.slice(0, 4);
  const rest = [...nav.main.slice(4), ...secondary];
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-rc-navy/30 md:hidden" onClick={() => setOpen(false)}>
          <nav
            aria-label="Menu lainnya"
            className="rc-enter absolute inset-x-3 bottom-20 rounded-xl border border-rc-border bg-rc-surface p-2 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            {rest.map((item) => {
              const Icon = item.icon;
              const active = nav.isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    "flex min-h-12 items-center gap-3 rounded-md px-3 text-base font-medium",
                    active ? "bg-rc-accent-soft text-rc-accent" : "text-rc-fg hover:bg-rc-surface-hover",
                  )}
                >
                  <Icon className="h-5 w-5" aria-hidden />
                  {item.label}
                </Link>
              );
            })}
            <LogoutButton className="mt-1 w-full" />
          </nav>
        </div>
      )}
      <nav
        aria-label="Navigasi utama"
        className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-rc-border bg-rc-surface pb-[env(safe-area-inset-bottom)] md:hidden"
      >
        {pinned.map((item) => {
          const Icon = item.icon;
          const active = nav.isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative flex min-h-16 flex-col items-center justify-center gap-1 text-xs font-medium",
                active ? "text-rc-accent" : "text-rc-fg-muted",
              )}
            >
              <Icon className="h-5 w-5" aria-hidden />
              <span className="max-w-full truncate px-1">{item.label === "Aktivitas agen" ? "Agen" : item.label}</span>
              {item.badge ? (
                <span className="absolute top-2 left-1/2 ml-2 rounded-full bg-rc-highlight px-1.5 text-[11px] font-semibold text-rc-navy">
                  {item.badge}
                </span>
              ) : null}
            </Link>
          );
        })}
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((o) => !o)}
          className={cn(
            "flex min-h-16 cursor-pointer flex-col items-center justify-center gap-1 text-xs font-medium",
            open || rest.some((i) => nav.isActive(i.href)) ? "text-rc-accent" : "text-rc-fg-muted",
          )}
        >
          {open ? <X className="h-5 w-5" aria-hidden /> : <Menu className="h-5 w-5" aria-hidden />}
          Menu
        </button>
      </nav>
    </>
  );
}
