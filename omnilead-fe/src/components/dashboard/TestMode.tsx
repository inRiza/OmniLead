"use client";

import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import { FlaskConical } from "lucide-react";
import { api, type TestMode } from "@/lib/api";
import { cn } from "@/lib/utils";

let state: TestMode | null = null;
let loading = false;
const listeners = new Set<() => void>();

function emit(next: TestMode | null) {
  state = next;
  listeners.forEach((l) => l());
}

function load() {
  if (loading || state) return;
  loading = true;
  api
    .testMode()
    .then(emit)
    .catch(() => emit({ available: false, enabled: false, accounts: [] }))
    .finally(() => {
      loading = false;
    });
}

function useTestMode() {
  const value = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => state,
    () => null,
  );
  useEffect(() => {
    const t = setTimeout(load, 0);
    return () => clearTimeout(t);
  }, []);
  return value;
}

export function TestModeToggle({ collapsed }: { collapsed: boolean }) {
  const mode = useTestMode();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!mode?.available) return null;
  const ready = mode.accounts.filter((a) => a.configured).length;

  async function toggle() {
    setBusy(true);
    setError("");
    try {
      emit(await api.setTestMode(!mode!.enabled));
      window.location.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Mode pengujian belum bisa diubah");
      setBusy(false);
    }
  }

  return (
    <div className={cn("mb-2 rounded-lg", collapsed ? "" : "border border-rc-border bg-rc-surface p-2.5")}>
      <button
        type="button"
        role="switch"
        aria-checked={mode.enabled}
        aria-label="Mode pengujian"
        title={collapsed ? `Mode pengujian ${mode.enabled ? "aktif" : "mati"}` : undefined}
        disabled={busy}
        onClick={() => void toggle()}
        className={cn(
          "flex w-full cursor-pointer items-center gap-2.5 rounded-md text-left text-sm disabled:cursor-wait disabled:opacity-60",
          collapsed ? "justify-center py-2" : "",
          mode.enabled ? "text-amber-700" : "text-rc-fg-muted hover:text-rc-fg",
        )}
      >
        <FlaskConical className="h-[18px] w-[18px] shrink-0" aria-hidden />
        {!collapsed && (
          <>
            <span className="flex-1 font-medium">Mode pengujian</span>
            <span className={cn("relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors", mode.enabled ? "bg-amber-500" : "bg-rc-border-strong")}>
              <span className={cn("inline-block h-4 w-4 rounded-full bg-white transition-transform", mode.enabled ? "translate-x-[18px]" : "translate-x-0.5")} />
            </span>
          </>
        )}
      </button>
      {!collapsed && (
        <p className="mt-1.5 text-xs text-rc-fg-muted">
          {mode.enabled ? `Memakai ${ready} akun dari .env, tanpa OAuth dan tunnel.` : "Pakai akun kanal dari .env untuk uji coba."}
        </p>
      )}
      {error && !collapsed ? <p role="alert" className="mt-1.5 text-xs text-red-700">{error}</p> : null}
    </div>
  );
}

export function TestModeBanner() {
  const mode = useTestMode();
  if (!mode?.enabled) return null;
  const missing = mode.accounts.filter((a) => !a.configured).map((a) => a.channel);
  return (
    <p role="status" className="flex flex-wrap items-center justify-center gap-x-2 gap-y-1 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
      <FlaskConical className="h-4 w-4" aria-hidden />
      <span className="font-medium">Mode pengujian aktif.</span>
      Kanal memakai akun dari .env backend. Webhook tidak dipakai, tarik pesan lewat Sinkronkan di Workspace.
      {missing.length ? <span>Belum diisi: {missing.join(", ")}.</span> : null}
      <Link href="/dashboard/integrasi" className="underline">
        Lihat kanal
      </Link>
    </p>
  );
}
