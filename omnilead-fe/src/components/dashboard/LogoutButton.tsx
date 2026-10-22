"use client";

import { useState } from "react";
import { LogOut } from "lucide-react";
import { api } from "@/lib/api";
import { useAccount } from "./AccountProvider";
import { cn } from "@/lib/utils";

export function LogoutButton({ className, inline }: { className?: string; inline?: boolean }) {
  const { session } = useAccount();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!session.user) return null;
  return (
    <div className={cn("min-w-0", className)}>
      <button
        type="button"
        disabled={busy}
        className={cn(
          "group inline-flex cursor-pointer items-center gap-2 rounded-md border border-red-200/90 bg-red-50 px-3.5 py-1.5 text-sm font-medium text-rc-danger transition-[background-color,border-color] hover:border-red-300 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-40",
          inline ? "w-auto justify-center" : "w-full justify-start",
        )}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            await api.logout();
            window.location.replace("/login");
          } catch (e) {
            setError(e instanceof Error ? e.message : "Belum berhasil keluar. Coba lagi.");
            setBusy(false);
          }
        }}
      >
        <LogOut size={16} className="shrink-0 transition-transform group-hover:translate-x-0.5" aria-hidden />
        {busy ? "Keluar…" : "Keluar"}
      </button>
      {error && <p role="alert" className="mt-1 break-words text-sm text-rc-danger">{error}</p>}
    </div>
  );
}
