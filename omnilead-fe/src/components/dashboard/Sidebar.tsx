"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useSyncExternalStore, type ComponentType, type SVGProps } from "react";
import { BookOpen, Bot, Menu, PanelLeftClose, PanelLeftOpen, Settings2, X } from "lucide-react";
import { Logo } from "@/components/brand/Logo";
import { cn } from "@/lib/utils";
import { useAccount } from "./AccountProvider";
import { useDashboard } from "./DashboardContext";
import { LogoutButton } from "./LogoutButton";
import { HomeIcon, InboxIcon, ListIcon, PlugIcon, UsersIcon } from "./icons";

type NavItem = {
  href: string;
  label: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  badge?: number;
};

const main: NavItem[] = [
  { href: "/dashboard", label: "Beranda", icon: HomeIcon },
  { href: "/dashboard/inbox", label: "Workspace", icon: InboxIcon },
  { href: "/dashboard/agen", label: "Agen", icon: Bot },
  { href: "/dashboard/leads", label: "Lead", icon: UsersIcon },
  { href: "/dashboard/integrasi", label: "Integrasi", icon: PlugIcon },
  { href: "/dashboard/audit", label: "Audit", icon: ListIcon },
];

const secondary: NavItem[] = [
  { href: "/dashboard/knowledge", label: "Pengetahuan & Tone", icon: BookOpen },
  { href: "/dashboard/pengaturan", label: "Pengaturan Agen", icon: Settings2 },
];

const KEY = "omnilead.sidebar.collapsed";
const listeners = new Set<() => void>();

function readCollapsed() {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

function writeCollapsed(v: boolean) {
  try {
    localStorage.setItem(KEY, v ? "1" : "0");
  } catch {}
  listeners.forEach((l) => l());
}

function useCollapsed() {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    readCollapsed,
    () => false,
  );
}

function useIsActive() {
  const pathname = usePathname();
  return (href: string) => (href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(href));
}

function mainNav(pendingCount: number): NavItem[] {
  return main.map((i) => (i.href === "/dashboard/inbox" ? { ...i, badge: pendingCount } : i));
}

export function Sidebar() {
  const collapsed = useCollapsed();
  const isActive = useIsActive();
  const { session } = useAccount();
  const { actions } = useDashboard();
  const pendingCount = actions.filter((action) => action.status === "pending").length;
  const user = session.user;
  const navMain = mainNav(pendingCount);

  return (
    <aside
      className={cn(
        "rc-scrollbar hidden h-full shrink-0 flex-col overflow-x-hidden bg-rc-bg transition-[width] duration-300 ease-out md:flex",
        collapsed ? "w-[4.25rem]" : "w-60",
      )}
    >
      <div className={cn("flex min-h-16 shrink-0 items-center gap-2 px-3", collapsed ? "justify-center" : "justify-between")}>
        <Link href="/" aria-label="OmniLead" className={cn("rounded-md px-1", collapsed && "hidden")}>
          <Logo />
        </Link>
        <button
          type="button"
          onClick={() => writeCollapsed(!collapsed)}
          aria-label={collapsed ? "Buka sidebar" : "Ciutkan sidebar"}
          title={collapsed ? "Buka sidebar" : "Ciutkan sidebar"}
          className="inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded-md text-rc-fg-muted transition-colors hover:bg-rc-surface-hover hover:text-rc-fg"
        >
          {collapsed ? <PanelLeftOpen className="h-[18px] w-[18px]" /> : <PanelLeftClose className="h-[18px] w-[18px]" />}
        </button>
      </div>

      <nav className="flex flex-1 flex-col gap-5 px-3 py-1">
        <NavGroup items={navMain} isActive={isActive} collapsed={collapsed} />
        <div>
          {collapsed ? (
            <span className="mx-auto mb-2 block h-px w-6 bg-rc-border" />
          ) : (
            <p className="px-2.5 pb-1 text-xs font-semibold tracking-wide text-rc-fg-subtle uppercase">Pengaturan</p>
          )}
          <NavGroup items={secondary} isActive={isActive} collapsed={collapsed} />
        </div>
      </nav>

      <div className="p-3 pt-0">
        <div className={cn("flex items-center gap-2.5 rounded-md py-1.5", collapsed ? "justify-center px-0" : "px-2")}>
          <div
            title={user?.name}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-rc-accent text-sm font-semibold text-rc-accent-fg"
          >
            {user ? user.name.slice(0, 2).toUpperCase() : "OL"}
          </div>
          {!collapsed && (
            <div className="min-w-0 leading-tight">
              <div className="truncate text-sm font-medium text-rc-fg">{user?.name ?? "Demo OmniLead"}</div>
              <div className="truncate text-xs text-rc-fg-muted">{user?.email ?? user?.business ?? "Lingkungan lokal"}</div>
            </div>
          )}
        </div>
        {!collapsed && <LogoutButton className="mt-1" />}
      </div>
    </aside>
  );
}

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const isActive = useIsActive();
  const { actions } = useDashboard();
  const pendingCount = actions.filter((action) => action.status === "pending").length;
  const pathname = usePathname();
  const [seen, setSeen] = useState(pathname);
  if (seen !== pathname) {
    setSeen(pathname);
    setOpen(false);
  }
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Buka menu"
        className="inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded-md text-rc-fg-muted hover:bg-rc-surface-hover md:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>
      {open && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button type="button" aria-label="Tutup menu" className="fade-in-0 absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />
          <div className="rc-scrollbar absolute inset-y-0 left-0 flex w-72 flex-col overflow-y-auto bg-rc-bg p-3">
            <div className="flex items-center justify-between px-1 pb-3">
              <Logo />
              <button type="button" aria-label="Tutup menu" onClick={() => setOpen(false)} className="inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-rc-surface-hover">
                <X className="h-5 w-5" />
              </button>
            </div>
            <NavGroup items={[...mainNav(pendingCount), ...secondary]} isActive={isActive} collapsed={false} />
          </div>
        </div>
      )}
    </>
  );
}

function NavGroup({
  items,
  isActive,
  collapsed,
}: {
  items: NavItem[];
  isActive: (href: string) => boolean;
  collapsed: boolean;
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
              title={collapsed ? item.label : undefined}
              aria-label={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-2.5 rounded-md py-2 text-sm font-medium transition-colors",
                collapsed ? "justify-center px-0" : "px-2.5",
                active ? "bg-rc-accent-soft text-rc-accent" : "text-rc-fg-muted hover:bg-rc-surface-hover hover:text-rc-fg",
              )}
            >
              <Icon className="h-[18px] w-[18px] shrink-0" />
              {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
              {!collapsed && item.badge ? (
                <span
                  className={cn(
                    "rounded-md px-1.5 py-0.5 text-sm font-medium tabular-nums",
                    active ? "bg-rc-accent text-white" : "bg-rc-highlight-soft text-[#8a5300]",
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
