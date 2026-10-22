"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Building2, LayoutGrid, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/action/button";
import { Select } from "@/components/ui/select";
import { useAccount } from "./AccountProvider";
import { SettingsDialog } from "./SettingsDialog";

const ADD = "__add";
const MANAGE = "__manage";

export function WorkspaceSwitcher() {
  const { session } = useAccount();
  const router = useRouter();
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
    <Select
      id="active-workspace"
      label="Bisnis aktif"
      align="right"
      className="w-52 md:w-60"
      value={session.user.workspace_id}
      disabled={busy}
      options={[
        ...(session.user.workspaces ?? [{ id: session.user.workspace_id, name: session.user.business }]).map((workspace) => ({
          value: workspace.id,
          label: workspace.name,
          icon: <Building2 aria-hidden className="h-4 w-4 shrink-0 text-rc-fg-muted" />,
        })),
        { value: ADD, label: "Tambah bisnis", icon: <Plus aria-hidden className="h-4 w-4 shrink-0 text-rc-accent" /> },
        { value: MANAGE, label: "Kelola semua bisnis", icon: <LayoutGrid aria-hidden className="h-4 w-4 shrink-0 text-rc-fg-muted" /> },
      ]}
      onChange={(id) => {
        if (id === ADD) { setError(""); setName(""); setOpen(true); return; }
        if (id === MANAGE) { router.push("/bisnis"); return; }
        if (id === session.user?.workspace_id) return;
        setBusy(true); setError("");
        void api.selectWorkspace(id).then(() => window.location.reload()).catch((e) => { setError(e.message); setBusy(false); });
      }}
    />
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
