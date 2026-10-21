"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export function SettingsDialog({ open, onOpenChange, title, description, children, wide = false, busy = false }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  children: ReactNode;
  wide?: boolean;
  busy?: boolean;
}) {
  const returnFocus = useRef<HTMLElement | null>(null);
  return <Dialog.Root open={open} onOpenChange={(next) => { if (!busy) onOpenChange(next); }}>
    <Dialog.Portal>
      <Dialog.Overlay className="fixed inset-0 z-50 bg-black/35" />
      <Dialog.Content
        onOpenAutoFocus={() => { returnFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null; }}
        onCloseAutoFocus={(event) => { if (returnFocus.current?.isConnected) { event.preventDefault(); returnFocus.current.focus(); } }}
        className={cn("fixed top-1/2 left-1/2 z-50 flex max-h-[90dvh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-2xl border border-rc-border bg-rc-surface text-rc-fg shadow-xl", wide ? "max-w-2xl" : "max-w-lg")}
      >
        <div className="shrink-0 border-b border-rc-border p-5 pr-14 md:p-6 md:pr-14">
          <Dialog.Title className="break-words text-lg font-semibold">{title}</Dialog.Title>
          <Dialog.Description className="mt-2 text-sm leading-relaxed text-rc-fg-muted">{description}</Dialog.Description>
        </div>
        <div className="rc-scrollbar min-h-0 overflow-y-auto p-5 md:p-6">{children}</div>
        <Dialog.Close disabled={busy} aria-label="Tutup dialog" className="absolute top-4 right-4 cursor-pointer rounded-md p-2 text-rc-fg-muted hover:bg-rc-surface-hover focus-visible:outline-2 disabled:opacity-40"><X size={18} /></Dialog.Close>
      </Dialog.Content>
    </Dialog.Portal>
  </Dialog.Root>;
}
