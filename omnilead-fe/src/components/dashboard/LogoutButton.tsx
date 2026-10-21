"use client";

import { useState } from "react";
import { LogOut } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/action/button";
import { useAccount } from "./AccountProvider";
import { cn } from "@/lib/utils";

export function LogoutButton({ className }: { className?: string }) {
  const { session } = useAccount();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!session.user) return null;
  return <div className={cn("min-w-0", className)}>
    <Button purpose="action" style="ghost" className="w-full justify-start gap-2" disabled={busy} onClick={async () => {
      setBusy(true); setError("");
      try { await api.logout(); window.location.replace("/login"); }
      catch (e) { setError(e instanceof Error ? e.message : "Belum berhasil keluar. Coba lagi."); setBusy(false); }
    }}><LogOut size={16} />{busy ? "Keluar…" : "Keluar"}</Button>
    {error && <p role="alert" className="mt-1 break-words text-sm text-rc-danger">{error}</p>}
  </div>;
}
