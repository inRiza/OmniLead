"use client";

import { createContext, useContext, useId, type ComponentProps, type CSSProperties, type ReactNode } from "react";
import * as Recharts from "recharts";
import { cn } from "@/lib/utils";

export type ChartConfig = Record<string, { label: ReactNode; color: string; icon?: ReactNode }>;

const ChartContext = createContext<{ config: ChartConfig } | null>(null);

function useChart() {
  const ctx = useContext(ChartContext);
  if (!ctx) throw new Error("useChart harus dipakai di dalam ChartContainer");
  return ctx;
}

export function ChartContainer({
  config,
  className,
  children,
  id,
}: {
  config: ChartConfig;
  className?: string;
  children: ComponentProps<typeof Recharts.ResponsiveContainer>["children"];
  id?: string;
}) {
  const auto = useId();
  const chartId = `chart-${(id ?? auto).replace(/:/g, "")}`;
  const vars = Object.fromEntries(Object.entries(config).map(([k, v]) => [`--color-${k}`, v.color])) as CSSProperties;
  return (
    <ChartContext.Provider value={{ config }}>
      <div
        data-chart={chartId}
        style={vars}
        className={cn(
          "flex aspect-video justify-center text-xs [&_.recharts-cartesian-axis-tick_text]:fill-rc-fg-subtle [&_.recharts-cartesian-grid_line]:stroke-rc-border [&_.recharts-curve.recharts-tooltip-cursor]:stroke-rc-border-strong [&_.recharts-rectangle.recharts-tooltip-cursor]:fill-rc-accent-soft/60 [&_.recharts-surface]:outline-none [&_.recharts-wrapper]:outline-none",
          className,
        )}
      >
        <Recharts.ResponsiveContainer>{children}</Recharts.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  );
}

export const ChartTooltip = Recharts.Tooltip;
export const ChartLegend = Recharts.Legend;

type Item = { dataKey?: string | number; name?: string | number; value?: number | string; color?: string; payload?: Record<string, unknown> };

export function ChartTooltipContent({
  active,
  payload,
  label,
  labelKey,
  hideTotal,
}: {
  active?: boolean;
  payload?: Item[];
  label?: ReactNode;
  labelKey?: string;
  hideTotal?: boolean;
}) {
  const { config } = useChart();
  if (!active || !payload?.length) return null;
  const title = labelKey ? (payload[0]?.payload?.[labelKey] as ReactNode) : label;
  const total = payload.reduce((s, p) => s + (Number(p.value) || 0), 0);
  return (
    <div className="min-w-40 rounded-lg border border-rc-border bg-rc-surface px-3 py-2 text-xs shadow-[0_12px_32px_-12px_rgba(11,23,54,0.25)]">
      {title != null && <p className="mb-1.5 font-medium text-rc-fg">{title}</p>}
      <div className="flex flex-col gap-1">
        {payload.map((p) => {
          const key = String(p.dataKey ?? p.name);
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 shrink-0 rounded-[2px]" style={{ background: p.color ?? `var(--color-${key})` }} />
              <span className="flex-1 text-rc-fg-muted">{config[key]?.label ?? p.name}</span>
              <span className="font-medium text-rc-fg tabular-nums">{p.value}</span>
            </div>
          );
        })}
        {!hideTotal && payload.length > 1 && (
          <div className="mt-1 flex items-center justify-between border-t border-rc-border pt-1">
            <span className="text-rc-fg-muted">Total</span>
            <span className="font-semibold text-rc-fg tabular-nums">{total}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function ChartLegendContent({ payload, className }: { payload?: readonly Item[]; className?: string }) {
  const { config } = useChart();
  if (!payload?.length) return null;
  return (
    <div className={cn("flex flex-wrap items-center justify-center gap-x-5 gap-y-2 pt-4", className)}>
      {payload.map((p) => {
        const key = String(p.dataKey ?? p.value);
        const c = config[key];
        return (
          <div key={key} className="flex items-center gap-1.5 text-xs text-rc-fg-muted">
            {c?.icon ?? <span className="h-2.5 w-2.5 rounded-[2px]" style={{ background: p.color }} />}
            {c?.label ?? p.value}
          </div>
        );
      })}
    </div>
  );
}
