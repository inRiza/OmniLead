"use client";

import { useState, type FormEvent } from "react";
import { Plus } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/action/button";
import { useAccount } from "./AccountProvider";
import { SettingsDialog } from "./SettingsDialog";

export function WorkspaceSwitcher() {
  const { session } = useAccount();
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  if (!session.user) return null;
  async function addWorkspace(event: FormEvent) {
    event.preventDefault();
    if (busy || !name.trim()) return;
    setBusy(true); setError("");
    try { await api.addWorkspace(name.trim()); window.location.reload(); }
    catch (e) { setError(e instanceof Error ? e.message : "Bisnis belum dapat ditambahkan."); setBusy(false); }
  }
  return <div className="min-w-0">
    <div className="flex items-center gap-2">
    <label className="sr-only" htmlFor="active-workspace">Bisnis aktif</label>
    <select id="active-workspace" value={session.user.workspace_id} disabled={busy} className="min-h-9 min-w-0 max-w-48 rounded-md border border-rc-border bg-rc-surface px-2 py-1.5 text-sm font-medium text-rc-fg md:max-w-64" onChange={(event) => {
      const id = event.target.value;
      setBusy(true); setError("");
      void api.selectWorkspace(id).then(() => window.location.reload()).catch((e) => { setError(e.message); setBusy(false); });
    }}>
      {(session.user.workspaces ?? [{ id: session.user.workspace_id, name: session.user.business }]).map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
    </select>
    <Button purpose="action" disabled={busy} className="gap-1.5 whitespace-nowrap px-2 md:px-3" aria-label="Tambah bisnis" onClick={() => { setError(""); setName(""); setOpen(true); }}><Plus size={16} /><span className="hidden xl:inline">Tambah bisnis</span></Button>
    </div>
    {error && !open && <p role="alert" className="mt-1 text-sm text-rc-danger">{error}</p>}
    <SettingsDialog open={open} onOpenChange={setOpen} busy={busy} title="Tambah bisnis" description="Buat ruang untuk bisnis lain. Pelanggan, akun kanal, dan pengetahuan agen dikelola terpisah untuk setiap bisnis.">
      <form onSubmit={addWorkspace} className="space-y-5">
        <label className="block text-sm font-medium">Nama bisnis baru<input name="workspace_name" required maxLength={100} value={name} onChange={(event) => setName(event.target.value)} placeholder="Contoh: Bimo Katering" className="mt-2 block w-full rounded-lg border border-rc-border bg-rc-bg px-3 py-2 text-base" /></label>
        {error && <p role="alert" className="text-sm text-rc-danger">{error}</p>}
        <div className="flex justify-end gap-2"><Button purpose="action" disabled={busy} onClick={() => setOpen(false)}>Batal</Button><Button purpose="action" style="primary" type="submit" disabled={busy || !name.trim()}>{busy ? "Menambahkan…" : "Tambah bisnis"}</Button></div>
      </form>
    </SettingsDialog>
  </div>;
}
