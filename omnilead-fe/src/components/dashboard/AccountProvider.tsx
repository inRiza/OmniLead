"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { api, setActiveWorkspace, type AccountSession } from "@/lib/api";

const Context = createContext<{ session: AccountSession; refreshAccount: () => Promise<void> } | null>(null);

export function AccountProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AccountSession | null>(null);
  const [error, setError] = useState("");
  const workspace = useRef<string | null>(null);
  const refreshAccount = useCallback(async () => {
    try {
      const result = await api.session();
      if (result.enabled && !result.user) {
        window.location.replace("/login");
        return;
      }
      const next = result.user?.workspace_id ?? null;
      setActiveWorkspace(next);
      if (workspace.current && workspace.current !== next) {
        window.location.reload();
        return;
      }
      workspace.current = next;
      setSession(result);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal memuat akun");
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => void refreshAccount(), 0);
    const onFocus = () => void refreshAccount();
    window.addEventListener("focus", onFocus);
    return () => { clearTimeout(timer); window.removeEventListener("focus", onFocus); };
  }, [refreshAccount]);

  if (!session) return (
    <main className="flex min-h-dvh items-center justify-center bg-rc-bg p-6 text-rc-fg">
      <div role="status" className="text-center">
        <p>{error || "Memuat akun Anda…"}</p>
        {error && <button className="mt-4 cursor-pointer underline" onClick={() => void refreshAccount()}>Coba lagi</button>}
      </div>
    </main>
  );
  return <Context.Provider value={{ session, refreshAccount }}>{children}</Context.Provider>;
}

export function useAccount() {
  const value = useContext(Context);
  if (!value) throw new Error("AccountProvider belum dipasang");
  return value;
}
