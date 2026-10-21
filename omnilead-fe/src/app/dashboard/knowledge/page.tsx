"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, type ChannelAgentConfig, type KnowledgeBase, type KnowledgeProduct } from "@/lib/api";
import { useAccount } from "@/components/dashboard/AccountProvider";
import { Topbar } from "@/components/dashboard/Topbar";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Button } from "@/components/action/button";
import { ChannelIcon } from "@/components/primitives";
import type { Channel } from "@/lib/types";
import { channelLabel } from "@/lib/ui";
import { BookOpen, ChevronRight, Plus } from "lucide-react";
import { SettingsDialog } from "@/components/dashboard/SettingsDialog";

const channels: Channel[] = ["instagram", "whatsapp", "email", "linkedin", "tiktok"];
const tones: Record<ChannelAgentConfig["tone"], string> = {
  friendly: "Ramah & hangat", professional: "Profesional", casual: "Santai", concise: "Singkat & jelas", custom: "Gaya sendiri",
};
const emptyConfig: ChannelAgentConfig = { knowledge_base_ids: [], tone: "friendly", custom_tone: "" };
const field = "mt-1 block w-full rounded-lg border border-rc-border bg-rc-bg px-3 py-2 text-base text-rc-fg outline-none focus:border-rc-primary";
const emptyEditor = { id: "", name: "", content: "", products: [] as KnowledgeProduct[] };

export default function KnowledgePage() {
  const { session } = useAccount();
  const [knowledge, setKnowledge] = useState<KnowledgeBase[]>([]);
  const [settings, setSettings] = useState<Record<string, ChannelAgentConfig>>({});
  const [editor, setEditor] = useState(emptyEditor);
  const [editorOpen, setEditorOpen] = useState(false);
  const [activeChannel, setActiveChannel] = useState<Channel | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);
  const [dirtyChannels, setDirtyChannels] = useState<string[]>([]);
  const business = session.user?.business ?? "bisnis Anda";

  const load = useCallback(async () => {
    try {
      const [documents, configs] = await Promise.all([api.knowledgeBases(), api.agentChannelSettings()]);
      setKnowledge(documents); setSettings(configs); setLoaded(true);
    } catch (e) { setError(e instanceof Error ? e.message : "Gagal memuat pengetahuan"); }
  }, []);
  useEffect(() => { const timer = setTimeout(() => void load(), 0); return () => clearTimeout(timer); }, [load]);

  async function run(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true); setError(""); setNotice("");
    try { await action(); }
    catch (e) { setError(e instanceof Error ? e.message : "Gagal menyimpan perubahan"); }
    finally { setBusy(false); }
  }

  function updateChannel(channel: string, patch: Partial<ChannelAgentConfig>) {
    setSettings((current) => ({ ...current, [channel]: { ...(current[channel] ?? emptyConfig), ...patch } }));
    setDirtyChannels((current) => current.includes(channel) ? current : [...current, channel]);
  }

  async function saveKnowledge(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const saved = await api.saveKnowledge({ name: editor.name, content: editor.content, products: editor.products }, editor.id || undefined);
      setKnowledge((current) => [...current.filter((document) => document.id !== saved.id), saved]);
      setEditor(emptyEditor);
      setEditorOpen(false);
      setNotice("Pengetahuan disimpan. Pilih sumber ini pada kanal di bawah agar digunakan agen.");
    });
  }

  function product(index: number, patch: Partial<KnowledgeProduct>) {
    setEditor((current) => ({ ...current, products: current.products.map((item, i) => i === index ? { ...item, ...patch } : item) }));
  }

  return <>
    <Topbar title="Pengetahuan & Tone" subtitle="Kelola sumber informasi dan gaya balasan agen bisnis ini" />
    <ContentInset className="rc-scrollbar overflow-y-auto">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 p-4 pb-10 md:p-6">
        <section className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
          <p className="text-sm font-medium text-rc-fg-muted">PENGETAHUAN BISNIS</p>
          <h2 className="mt-1 break-words text-xl font-semibold">Agen untuk {business}</h2>
          <p className="mt-2 text-base text-rc-fg-muted">Simpan informasi tentang {business}, lalu pilih pengetahuan yang digunakan pada setiap kanal. Semua sumber di halaman ini hanya tersedia untuk bisnis ini.</p>
          <div className="mt-4 flex flex-wrap gap-2"><Button purpose="nav" href="/dashboard/integrasi">Kelola akun & kanal</Button><Button purpose="nav" href="/dashboard/inbox">Coba lewat Tempel pesan</Button></div>
        </section>
        {error && <p role="alert" className="rounded-lg border border-rc-danger p-4 text-sm text-rc-danger">{error}</p>}
        {notice && <p role="status" className="rounded-lg border border-rc-border bg-rc-surface-hover p-4 text-sm">{notice}</p>}
        {!loaded && <p role="status" className="text-sm text-rc-fg-muted">Memuat pengetahuan…</p>}

          <section className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="break-words text-lg font-semibold">Pengetahuan {business}</h2><p className="mt-1 text-sm text-rc-fg-muted">FAQ, katalog produk, layanan, atau kebijakan bisnis.</p></div><Button purpose="action" style="primary" className="gap-2" disabled={busy || !loaded} onClick={() => { setError(""); setEditor(emptyEditor); setEditorOpen(true); }}><Plus size={16} />Tambah pengetahuan</Button></div>
            {!knowledge.length && loaded && <p className="mt-4 text-sm text-rc-fg-muted">Belum ada pengetahuan. Mulai dengan profil bisnis atau daftar pertanyaan pelanggan.</p>}
            <ul className="mt-5 flex flex-col gap-3">{knowledge.map((document) => <li key={document.id} className="rounded-lg border border-rc-border p-4">
              <div className="flex flex-wrap items-center gap-3"><BookOpen size={20} className="shrink-0 text-rc-fg-muted" /><div className="min-w-0 flex-1"><h3 className="break-words text-base font-medium">{document.name}</h3><p className="mt-1 text-sm text-rc-fg-muted">{document.content.length.toLocaleString("id-ID")} karakter · {document.products.length} produk · {channels.filter((channel) => settings[channel]?.knowledge_base_ids.includes(document.id)).length} kanal</p></div>
              <div className="flex gap-2"><Button purpose="action" disabled={busy} aria-label={`Edit ${document.name}`} onClick={() => { setError(""); setEditor({ id: document.id, name: document.name, content: document.content, products: document.products.map((item) => ({ ...item })) }); setEditorOpen(true); }}>Edit</Button><Button purpose="action" style="ghost" disabled={busy} aria-label={`Hapus ${document.name}`} onClick={() => setDeleting(document.id)}>Hapus</Button></div></div>
              {deleting === document.id && <div className="mt-3 text-sm"><p>Hapus sumber ini dan lepaskan dari semua kanal?</p><div className="mt-2 flex gap-2"><Button purpose="action" disabled={busy} onClick={() => void run(async () => { await api.deleteKnowledge(document.id); await load(); if (editor.id === document.id) setEditor(emptyEditor); setDeleting(null); setDirtyChannels([]); setNotice("Pengetahuan dihapus dan dilepas dari kanal."); })}>Ya, hapus</Button><Button purpose="action" onClick={() => setDeleting(null)}>Batal</Button></div></div>}
            </li>)}</ul>
          </section>

        <SettingsDialog open={editorOpen} onOpenChange={setEditorOpen} busy={busy} wide title={`${editor.id ? "Edit" : "Tambah"} pengetahuan untuk ${business}`} description="Beri nama sesuai topiknya, misalnya FAQ pengiriman atau katalog produk. Setelah disimpan, pilih sumber ini pada kanal yang akan menggunakannya.">
          <form onSubmit={saveKnowledge} className="flex flex-col gap-4">
            {error && <p role="alert" className="text-sm text-rc-danger">{error}</p>}
            <label className="text-sm font-medium">Nama / topik pengetahuan<input required value={editor.name} maxLength={100} onChange={(e) => setEditor({ ...editor, name: e.target.value })} placeholder="Contoh: FAQ pengiriman, katalog produk, kebijakan retur" className={field} /></label>
            <label className="text-sm font-medium">Impor Markdown atau teks<input type="file" accept=".md,.txt,.markdown,text/plain,text/markdown" className="mt-2 block w-full text-sm text-rc-fg-muted file:mr-3 file:rounded-md file:border file:border-rc-border file:bg-rc-surface file:px-3 file:py-2 file:text-rc-fg" onChange={(e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              if (!/\.(md|txt|markdown)$/i.test(file.name) || file.size > 100_000) { setError("Pilih file .md atau .txt maksimal 100 KB."); e.target.value = ""; return; }
              void file.text().then((content) => { setEditor((current) => ({ ...current, name: current.name || file.name.replace(/\.[^.]+$/, ""), content: content.replace(/^\uFEFF/, "") })); setError(""); }).catch(() => setError("File tidak dapat dibaca."));
              e.target.value = "";
            }} /><span className="mt-1 block text-sm text-rc-fg-muted">Maksimal 100 KB. Isi file dapat Anda edit sebelum disimpan.</span></label>
            <label className="text-sm font-medium">Isi pengetahuan<textarea value={editor.content} maxLength={100_000} rows={10} onChange={(e) => setEditor({ ...editor, content: e.target.value })} placeholder={"# Jam operasional\nSenin–Sabtu, pukul 09.00–17.00 WIB.\n\n# Pengiriman\nPesanan dikirim setiap hari kerja."} className={`${field} resize-y font-mono`} /></label>
            <div><h3 className="text-sm font-semibold">Produk & harga (opsional)</h3><p className="mt-1 text-sm text-rc-fg-muted">Tambahkan harga produk agar agen dapat membuat penawaran dan menghitung total dengan tepat.</p></div>
            {editor.products.map((item, index) => <fieldset key={index} className="grid grid-cols-2 gap-3 rounded-lg border border-rc-border p-3">
              <legend className="px-1 text-sm">Produk {index + 1}</legend>
              <label className="col-span-2 text-sm">Nama produk<input value={item.name} onChange={(e) => product(index, { name: e.target.value })} required maxLength={120} className={field} /></label>
              <label className="text-sm">Harga (Rp)<input type="number" value={item.unit_price} onChange={(e) => product(index, { unit_price: Number(e.target.value) })} min={0} max={1_000_000_000} step={1} required className={field} /></label>
              <label className="text-sm">Satuan<input value={item.unit} onChange={(e) => product(index, { unit: e.target.value })} required maxLength={30} placeholder="pcs / box / pax" className={field} /></label>
              <label className="text-sm">Minimal pesanan<input type="number" value={item.min_order} onChange={(e) => product(index, { min_order: Number(e.target.value) })} min={1} max={1_000_000} step={1} required className={field} /></label>
              <div className="flex items-end"><Button purpose="action" onClick={() => setEditor({ ...editor, products: editor.products.filter((_, i) => i !== index) })}>Hapus produk</Button></div>
            </fieldset>)}
            <div><Button purpose="action" className="gap-2" disabled={editor.products.length >= 30 || busy} onClick={() => setEditor({ ...editor, products: [...editor.products, { name: "", unit_price: 0, unit: "pcs", min_order: 1 }] })}><Plus size={16} />Tambah produk</Button></div>
            <div className="flex flex-wrap justify-end gap-2 border-t border-rc-border pt-4"><Button purpose="action" disabled={busy} onClick={() => setEditorOpen(false)}>Batal</Button><Button purpose="action" style="primary" type="submit" disabled={busy || !loaded}>{busy ? "Menyimpan…" : "Simpan pengetahuan"}</Button></div>
          </form>
        </SettingsDialog>

        <section className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
          <h2 className="text-lg font-semibold">Pengaturan agen per kanal</h2>
          <p className="mt-2 text-sm text-rc-fg-muted">Pilih Atur untuk menentukan pengetahuan dan tone {business} di setiap kanal.</p>
          <div className="mt-5 divide-y divide-rc-border">{channels.map((channel) => {
            const config = settings[channel] ?? emptyConfig;
            const sources = knowledge.filter((document) => config.knowledge_base_ids.includes(document.id));
            return <div key={channel} className="flex items-center gap-3 py-4 first:pt-0 last:pb-0"><ChannelIcon channel={channel} /><div className="min-w-0 flex-1"><h3 className="text-base font-semibold">{channelLabel[channel]}</h3><p className="mt-1 text-sm text-rc-fg-muted">{sources.length ? `${sources.length} sumber pengetahuan` : "Belum ada pengetahuan"} · {tones[config.tone]}</p>{sources.length > 0 && <p className="mt-1 truncate text-sm text-rc-fg-muted" title={sources.map((source) => source.name).join(", ")}>{sources.map((source) => source.name).join(", ")}</p>}{dirtyChannels.includes(channel) && <p className="mt-1 text-sm text-rc-fg-muted">Perubahan belum disimpan</p>}</div><Button purpose="action" className="shrink-0 gap-1" aria-label={`Atur ${channelLabel[channel]}`} disabled={busy || !loaded} onClick={() => { setError(""); setActiveChannel(channel); }}>Atur<ChevronRight size={16} /></Button></div>;
          })}</div>
        </section>
        {activeChannel && <SettingsDialog open onOpenChange={(open) => { if (!open) setActiveChannel(null); }} busy={busy} title={`Atur agen ${channelLabel[activeChannel]}`} description={`Pengaturan untuk ${business}. Pilih sumber pengetahuan dan gaya balasan yang akan digunakan pada draf ${channelLabel[activeChannel]}.`}>
          {(() => {
            const channel = activeChannel;
            const config = settings[channel] ?? emptyConfig;
            return <form className="flex flex-col gap-5" onSubmit={(e) => {
              e.preventDefault(); void run(async () => { const saved = await api.saveAgentChannelSettings(channel, config); setSettings((current) => ({ ...current, [channel]: saved })); setDirtyChannels((current) => current.filter((id) => id !== channel)); setActiveChannel(null); setNotice(`Pengaturan ${channelLabel[channel]} untuk ${business} disimpan. Berlaku untuk draf berikutnya.`); });
            }}>
              {error && <p role="alert" className="text-sm text-rc-danger">{error}</p>}
              <fieldset><legend className="mb-2 text-sm font-medium">Sumber pengetahuan</legend>{knowledge.length ? knowledge.map((document) => <label key={document.id} className="mb-2 flex items-start gap-2 text-sm"><input type="checkbox" checked={config.knowledge_base_ids.includes(document.id)} onChange={(e) => updateChannel(channel, { knowledge_base_ids: e.target.checked ? [...config.knowledge_base_ids, document.id] : config.knowledge_base_ids.filter((id) => id !== document.id) })} className="mt-1" /><span>{document.name}</span></label>) : <p className="text-sm text-rc-fg-muted">Tambahkan knowledge base terlebih dahulu.</p>}</fieldset>
              <label className="text-sm font-medium">Tone {channelLabel[channel]}<select value={config.tone} onChange={(e) => updateChannel(channel, { tone: e.target.value as ChannelAgentConfig["tone"] })} className={field}>{Object.entries(tones).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
              {config.tone === "custom" && <label className="text-sm font-medium">Gaya balasan yang diinginkan<textarea value={config.custom_tone} onChange={(e) => updateChannel(channel, { custom_tone: e.target.value })} rows={3} maxLength={500} required placeholder="Contoh: Sapa pelanggan dengan kak, tanpa emoji, maksimal dua paragraf." className={field} /></label>}
              <div className="flex justify-end gap-2 border-t border-rc-border pt-4"><Button purpose="action" disabled={busy} onClick={() => setActiveChannel(null)}>Tutup</Button><Button purpose="action" style="primary" type="submit" disabled={busy || !loaded}>{busy ? "Menyimpan…" : `Simpan ${channelLabel[channel]}`}</Button></div>
            </form>;
          })()}
        </SettingsDialog>}
      </div>
    </ContentInset>
  </>;
}
