"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

interface DashboardState {
  paused: boolean;
  togglePause: () => void;
}

const Ctx = createContext<DashboardState | null>(null);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [paused, setPaused] = useState(false);
  return (
    <Ctx.Provider value={{ paused, togglePause: () => setPaused((v) => !v) }}>
      {children}
    </Ctx.Provider>
  );
}

export function useDashboard(): DashboardState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useDashboard harus di dalam DashboardProvider");
  return ctx;
}
