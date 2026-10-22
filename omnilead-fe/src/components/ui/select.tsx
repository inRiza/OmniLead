"use client";

import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type SelectOption<T extends string> = {
  value: T;
  label: string;
  icon?: ReactNode;
  hint?: string;
};

export function Select<T extends string>({
  value,
  onChange,
  options,
  placeholder = "Pilih",
  disabled,
  className,
  id,
  label,
  size = "md",
  align = "left",
}: {
  value: T | null;
  onChange: (value: T) => void;
  options: SelectOption<T>[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
  label?: string;
  size?: "sm" | "md";
  align?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState(0);
  const [pos, setPos] = useState<CSSProperties | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const listId = useId();
  const current = options.find((o) => o.value === value) ?? null;

  const place = useCallback(() => {
    const r = trigger.current?.getBoundingClientRect();
    if (!r) return;
    const height = Math.min(256, options.length * 40 + 8);
    const below = window.innerHeight - r.bottom;
    const up = below < height + 12 && r.top > below;
    const style: CSSProperties = { position: "fixed", minWidth: r.width, zIndex: 100, pointerEvents: "auto" };
    if (up) style.bottom = window.innerHeight - r.top + 6;
    else style.top = r.bottom + 6;
    if (align === "right") style.right = window.innerWidth - r.right;
    else style.left = r.left;
    setPos(style);
  }, [align, options.length]);

  useLayoutEffect(() => {
    if (open) place();
  }, [open, place]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!root.current?.contains(t) && !list.current?.contains(t)) setOpen(false);
    };
    const onMove = (e: Event) => {
      if (list.current?.contains(e.target as Node)) return;
      place();
    };
    document.addEventListener("pointerdown", onDown);
    window.addEventListener("scroll", onMove, true);
    window.addEventListener("resize", onMove);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      window.removeEventListener("scroll", onMove, true);
      window.removeEventListener("resize", onMove);
    };
  }, [open, place]);

  function openList() {
    if (disabled) return;
    setCursor(Math.max(0, options.findIndex((o) => o.value === value)));
    setOpen(true);
  }

  function pick(i: number) {
    const o = options[i];
    if (!o) return;
    onChange(o.value);
    setOpen(false);
  }

  function onKey(e: React.KeyboardEvent) {
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) {
        e.preventDefault();
        openList();
      }
      return;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setCursor((c) => Math.min(options.length - 1, c + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setCursor((c) => Math.max(0, c - 1));
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      pick(cursor);
    } else if (e.key === "Tab") {
      setOpen(false);
    }
  }

  return (
    <div ref={root} className={cn("relative", className)}>
      <button
        ref={trigger}
        id={id}
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={label}
        disabled={disabled}
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={onKey}
        className={cn(
          "flex w-full cursor-pointer items-center gap-2 rounded-md border bg-rc-surface text-left text-sm text-rc-fg transition-colors disabled:cursor-not-allowed disabled:opacity-50",
          size === "sm" ? "min-h-8 px-2.5" : "min-h-10 px-3",
          open ? "border-rc-accent ring-2 ring-rc-accent/15" : "border-rc-border hover:border-rc-border-strong",
        )}
      >
        {current?.icon}
        <span className={cn("min-w-0 flex-1 truncate", !current && "text-rc-fg-subtle")}>
          {current?.label ?? placeholder}
        </span>
        <ChevronDown
          aria-hidden
          className={cn("h-4 w-4 shrink-0 text-rc-fg-muted transition-transform duration-200", open && "rotate-180 text-rc-accent")}
        />
      </button>
      {open && pos && createPortal(
        <ul
          ref={list}
          id={listId}
          role="listbox"
          data-rc-popover=""
          style={pos}
          className="rc-brand rc-app rc-scrollbar max-h-64 overflow-y-auto rounded-lg border border-rc-border bg-rc-surface p-1 shadow-[0_12px_32px_-12px_rgba(11,23,54,0.25)] fade-in-0"
        >
          {options.map((o, i) => {
            const selected = o.value === value;
            return (
              <li
                key={o.value}
                role="option"
                aria-selected={selected}
                onPointerEnter={() => setCursor(i)}
                onPointerDown={(e) => e.preventDefault()}
                onClick={() => pick(i)}
                className={cn(
                  "flex cursor-pointer items-center gap-2 rounded-md px-2.5 py-2 text-sm whitespace-nowrap",
                  i === cursor ? "bg-rc-accent-soft" : "",
                  selected ? "font-medium text-rc-accent" : "text-rc-fg",
                )}
              >
                {o.icon}
                <span className="min-w-0 flex-1">
                  <span className="block truncate">{o.label}</span>
                  {o.hint && <span className="block truncate text-xs font-normal text-rc-fg-muted">{o.hint}</span>}
                </span>
                {selected && <Check aria-hidden className="h-4 w-4 shrink-0" />}
              </li>
            );
          })}
        </ul>,
        document.body,
      )}
    </div>
  );
}
