"use client";

import { useState } from "react";
import { Clock3, MessageSquarePlus, Search, X } from "lucide-react";
import type { ConversationSummary } from "@/lib/chat";
import { cn } from "@/lib/ui";

export function AgentConversationSidebar({ conversations, current, onSelect, onNew, onClose, disabled, mobile, boardOpen }: {
  conversations: ConversationSummary[]; current: string | null; onSelect: (id: string) => void; onNew: () => void;
  onClose: () => void; disabled: boolean; mobile: boolean; boardOpen: boolean;
}) {
  const [search, setSearch] = useState("");
  const filtered = conversations.filter((c) => c.title.toLocaleLowerCase("id-ID").includes(search.toLocaleLowerCase("id-ID")));
  return <aside aria-label="Riwayat percakapan agen" className={cn("min-h-0 shrink-0 flex-col border-r border-rc-border bg-rc-bg", mobile ? "absolute inset-0 z-30 flex" : boardOpen ? "hidden w-56 2xl:flex" : "hidden w-56 lg:flex")}>
    <div className="flex items-center justify-between px-3 py-3"><h2 className="text-xs font-semibold">Percakapan</h2><button onClick={onClose} aria-label="Tutup riwayat percakapan" className="rounded-md p-1.5 text-rc-fg-muted hover:bg-rc-surface-hover"><X className="h-3.5 w-3.5" /></button></div>
    <div className="space-y-3 px-3 pb-3">
      <button onClick={onNew} disabled={disabled} className="flex w-full items-center gap-2 rounded-lg border border-rc-border bg-rc-surface px-3 py-2 text-xs font-medium hover:border-rc-border-strong disabled:opacity-40"><MessageSquarePlus className="h-3.5 w-3.5" />Chat baru</button>
      <label className="flex items-center gap-2 rounded-lg border border-rc-border bg-rc-surface px-2.5 py-2 text-rc-fg-muted"><Search className="h-3.5 w-3.5" /><input aria-label="Cari percakapan" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Cari percakapan" className="min-w-0 flex-1 bg-transparent text-xs outline-none" /></label>
    </div>
    <p className="flex items-center gap-1.5 px-4 py-2 text-[10px] font-medium uppercase tracking-wide text-rc-fg-subtle"><Clock3 className="h-3 w-3" />Terbaru</p>
    <nav aria-label="Daftar percakapan" className="rc-scrollbar min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
      {filtered.map((c) => <button key={c.id} disabled={disabled} onClick={() => onSelect(c.id)} aria-current={c.id === current ? "page" : undefined} title={c.title} className={cn("block w-full truncate rounded-lg px-3 py-2.5 text-left text-xs transition-colors disabled:opacity-50", current === c.id ? "bg-rc-accent-soft font-medium text-rc-accent" : "text-rc-fg-muted hover:bg-rc-surface-hover hover:text-rc-fg")}>{c.title}</button>)}
      {!filtered.length && <p className="px-3 py-5 text-xs leading-relaxed text-rc-fg-muted">{search ? "Percakapan tidak ditemukan." : "Percakapan Anda akan tersimpan di sini."}</p>}
    </nav>
  </aside>;
}
