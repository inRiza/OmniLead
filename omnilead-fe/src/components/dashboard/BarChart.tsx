"use client";

import { useState } from "react";

export interface Bar {
  label: string;
  value: number;
}

export function BarChart({
  data,
  height = 140,
  unit = "",
}: {
  data: Bar[];
  height?: number;
  unit?: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const max = Math.max(...data.map((d) => d.value), 1);
  const gap = 10;
  const n = data.length;

  return (
    <div className="relative w-full" style={{ height }}>
      <div className="flex h-full items-end" style={{ gap }}>
        {data.map((d, i) => {
          const h = Math.max((d.value / max) * (height - 22), 3);
          const active = hover === i;
          return (
            <button
              key={d.label}
              type="button"
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}
              className="group flex h-full flex-1 flex-col items-center justify-end"
              style={{ minWidth: 0 }}
            >
              <div
                className="w-full rounded-t-sm transition-colors"
                style={{
                  height: h,
                  background: active
                    ? "var(--rc-fg)"
                    : "var(--rc-border-strong)",
                }}
              />
              <span className="mt-1.5 truncate text-xs text-rc-fg-subtle">
                {d.label}
              </span>
            </button>
          );
        })}
      </div>

      {hover !== null ? (
        <div
          className="pointer-events-none absolute -top-1 rounded-md border border-rc-border bg-rc-surface px-2 py-1 text-xs font-medium text-rc-fg"
          style={{
            left: `calc(${((hover + 0.5) / n) * 100}% )`,
            transform: "translateX(-50%)",
          }}
        >
          {data[hover].value}
          {unit}
        </div>
      ) : null}
    </div>
  );
}
