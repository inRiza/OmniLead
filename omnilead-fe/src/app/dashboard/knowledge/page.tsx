"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { BookOpen, Pencil, Plus, Trash2 } from "lucide-react";
import { api, type ChannelAgentConfig, type KnowledgeBase, type KnowledgeProduct } from "@/lib/api";
import { useAccount } from "@/components/dashboard/AccountProvider";
import { Topbar } from "@/components/dashboard/Topbar";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Button } from "@/components/action/button";
import { ChannelIcon } from "@/components/primitives";
import { Select } from "@/components/ui/select";
import { SettingsDialog } from "@/components/dashboard/SettingsDialog";
import type { Channel } from "@/lib/types";
import { channelLabel, cn } from "@/lib/ui";

const channels: Channel[] = ["instagram", "facebook", "whatsapp", "email"];
const tones: Record<ChannelAgentConfig["tone"], string> = {
  friendly: "Ramah & hangat",
  professional: "Profesional",
  casual: "Santai",
  concise: "Singkat & jelas",
  custom: "Gaya sendiri",
};
const emptyConfig: ChannelAgentConfig = { knowledge_base_ids: [], tone: "friendly", custom_tone: "" };
const emptyEditor = { id: "", name: "", content: "", products: [] as KnowledgeProduct[] };
const field =
  "mt-1.5 block min-h-10 w-full rounded-md border border-rc-border bg-rc-surface px-3 py-2 text-sm text-rc-fg outline-none placeholder:text-rc-fg-subtle focus:border-rc-accent focus:ring-2 focus:ring-rc-accent/15";
const section = "rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6";

export default function KnowledgePage() {
  const { session } = useAccount();
  const [knowledge, setKnowledge] = useState<KnowledgeBase[]>([]);
  const [settings, setSettings] = useState<Record<string, ChannelAgentConfig>>({});
  const [editor, setEditor] = useState(emptyEditor);
  const [editorOpen, setEditorOpen] = useState(false);
  const [sourcesFor, setSourcesFor] = useState<Channel | null>(null);
  const [customFor, setCustomFor] = useState<Channel | null>(null);
  const [draft, setDraft] = useState<ChannelAgentConfig>(emptyConfig);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);
  const business = session.user?.business ?? "bisnis Anda";

  const load = useCallback(async () => {
    try {
      const [documents, configs] = await Promise.all([api.knowledgeBases(), api.agentChannelSettings()]);
      setKnowledge(documents);
      setSettings(configs);
      setLoaded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal memuat pengetahuan");
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => void load(), 0);
    return () => clearTimeout(timer);
  }, [load]);

  async function run(key: string, action: () => Promise<void>) {
    if (busy) return;
    setBusy(key);
    setError("");
    setNotice("");
    try {
      await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal menyimpan perubahan");
    } finally {
      setBusy(null);
    }
  }

  function config(channel: Channel) {
    return settings[channel] ?? emptyConfig;
  }

  async function saveChannel(channel: Channel, next: ChannelAgentConfig, message: string) {
    const saved = await api.saveAgentChannelSettings(channel, next);
    setSettings((current) => ({ ...current, [channel]: saved }));
    setNotice(message);
  }

  function changeTone(channel: Channel, tone: ChannelAgentConfig["tone"]) {
    if (tone === "custom") {
      setDraft({ ...config(channel), tone });
      setCustomFor(channel);
      return;
    }
    void run(`tone-${channel}`, () => saveChannel(channel, { ...config(channel), tone }, `Tone ${channelLabel[channel]} diubah menjadi ${tones[tone]}.`));
  }

  async function saveKnowledge(event: FormEvent) {
    event.preventDefault();
    await run("editor", async () => {
      const saved = await api.saveKnowledge({ name: editor.name, content: editor.content, products: editor.products }, editor.id || undefined);
      setKnowledge((current) => [...current.filter((document) => document.id !== saved.id), saved]);
      setEditor(emptyEditor);
      setEditorOpen(false);
      setNotice("Pengetahuan disimpan. Pilih sumber ini pada kanal di bawah agar dipakai agen.");
    });
  }

  function product(index: number, patch: Partial<KnowledgeProduct>) {
    setEditor((current) => ({ ...current, products: current.products.map((item, i) => (i === index ? { ...item, ...patch } : item)) }));
  }

  return (
    <>
      <Topbar title="Pengetahuan & Tone" subtitle="Atur informasi bisnis dan gaya balasan agen di setiap kanal" />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 p-4 pb-10 md:p-6">
          {error && <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
          {notice && <p role="status" className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{notice}</p>}

          <section className={section}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-lg font-semibold text-rc-fg">Pengetahuan bisnis</h2>
                <p className="mt-2 text-sm text-rc-fg-muted">
                  FAQ, katalog produk, layanan, atau kebijakan {business}. Hanya dipakai agen untuk bisnis ini.
                </p>
              </div>
              <Button
                purpose="action"
                style="primary"
                className="min-h-10 gap-1.5"
                disabled={busy !== null || !loaded}
                onClick={() => {
                  setError("");
                  setEditor(emptyEditor);
                  setEditorOpen(true);
                }}
              >
                <Plus className="h-4 w-4" aria-hidden />
                Tambah pengetahuan
              </Button>
            </div>

            {!loaded ? <p role="status" className="mt-5 text-sm text-rc-fg-muted">Memuat pengetahuan…</p> : null}
            {loaded && !knowledge.length ? (
              <p className="mt-5 rounded-lg border border-dashed border-rc-border-strong px-4 py-8 text-center text-sm text-rc-fg-muted">
                Belum ada pengetahuan. Mulai dengan profil bisnis atau daftar pertanyaan pelanggan.
              </p>
            ) : null}

            <div className="mt-5 divide-y divide-rc-border">
              {knowledge.map((document) => {
                const used = channels.filter((channel) => config(channel).knowledge_base_ids.includes(document.id));
                return (
                  <div key={document.id} className="py-4 first:pt-0 last:pb-0">
                    <div className="flex items-center justify-between gap-6">
                      <div className="flex min-w-0 items-start gap-3">
                        <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-rc-accent-soft text-rc-accent">
                          <BookOpen className="h-[18px] w-[18px]" aria-hidden />
                        </span>
                        <div className="min-w-0">
                          <p className="truncate text-base font-semibold text-rc-fg">{document.name}</p>
                          <p className="mt-1 text-sm text-rc-fg-muted">
                            {document.content.length.toLocaleString("id-ID")} karakter, {document.products.length} produk,{" "}
                            {used.length ? `dipakai di ${used.map((c) => channelLabel[c]).join(", ")}` : "belum dipakai kanal mana pun"}
                          </p>
                        </div>
                      </div>
                      <div className="flex shrink-0 gap-2">
                        <Button
                          purpose="action"
                          className="gap-1.5"
                          disabled={busy !== null}
                          aria-label={`Edit ${document.name}`}
                          onClick={() => {
                            setError("");
                            setEditor({ id: document.id, name: document.name, content: document.content, products: document.products.map((item) => ({ ...item })) });
                            setEditorOpen(true);
                          }}
                        >
                          <Pencil className="h-4 w-4" aria-hidden />
                          Edit
                        </Button>
                        <button
                          type="button"
                          aria-label={`Hapus ${document.name}`}
                          disabled={busy !== null}
                          onClick={() => setDeleting(deleting === document.id ? null : document.id)}
                          className="inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded-md text-rc-fg-muted transition-colors hover:bg-red-50 hover:text-red-700 disabled:opacity-50"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                    {deleting === document.id ? (
                      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800">
                        Hapus sumber ini dan lepaskan dari semua kanal?
                        <div className="flex gap-2">
                          <Button purpose="action" onClick={() => setDeleting(null)}>
                            Batal
                          </Button>
                          <Button
                            purpose="action"
                            disabled={busy !== null}
                            className="border-red-600 bg-red-600 text-white hover:bg-red-700"
                            onClick={() =>
                              void run(`delete-${document.id}`, async () => {
                                await api.deleteKnowledge(document.id);
                                await load();
                                setDeleting(null);
                                setNotice("Pengetahuan dihapus dan dilepas dari semua kanal.");
                              })
                            }
                          >
                            Ya, hapus
                          </Button>
                        </div>
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </section>

          <section className={section}>
            <h2 className="text-lg font-semibold text-rc-fg">Tone dan sumber per kanal</h2>
            <p className="mt-2 text-sm text-rc-fg-muted">Perubahan tersimpan langsung dan berlaku untuk balasan berikutnya.</p>
            <div className="mt-5 divide-y divide-rc-border">
              {channels.map((channel) => {
                const c = config(channel);
                const sources = knowledge.filter((document) => c.knowledge_base_ids.includes(document.id));
                return (
                  <div key={channel} className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 py-4 first:pt-0 last:pb-0">
                    <div className="flex min-w-0 items-start gap-3">
                      <ChannelIcon channel={channel} size="md" />
                      <div className="min-w-0">
                        <p className="text-base font-semibold text-rc-fg">{channelLabel[channel]}</p>
                        <p className="mt-1 truncate text-sm text-rc-fg-muted" title={sources.map((s) => s.name).join(", ")}>
                          {sources.length ? sources.map((s) => s.name).join(", ") : "Belum ada sumber pengetahuan"}
                          {c.tone === "custom" && c.custom_tone ? `. Gaya: ${c.custom_tone}` : ""}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Button
                        purpose="action"
                        disabled={busy !== null || !loaded}
                        onClick={() => {
                          setError("");
                          setDraft(c);
                          setSourcesFor(channel);
                        }}
                      >
                        Sumber ({sources.length})
                      </Button>
                      <Select
                        label={`Tone ${channelLabel[channel]}`}
                        className="w-44"
                        align="right"
                        value={c.tone}
                        disabled={busy !== null || !loaded}
                        onChange={(tone) => changeTone(channel, tone)}
                        options={(Object.entries(tones) as [ChannelAgentConfig["tone"], string][]).map(([value, label]) => ({ value, label }))}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      </ContentInset>

      <SettingsDialog
        open={editorOpen}
        onOpenChange={setEditorOpen}
        busy={busy === "editor"}
        wide
        title={editor.id ? "Edit pengetahuan" : "Tambah pengetahuan"}
        description="Beri nama sesuai topiknya, misalnya FAQ pengiriman atau katalog produk. Setelah disimpan, pilih sumber ini pada kanal yang memakainya."
      >
        <form onSubmit={saveKnowledge} className="flex flex-col gap-5">
          <label className="block text-sm font-medium">
            Nama atau topik
            <input
              required
              value={editor.name}
              maxLength={100}
              onChange={(e) => setEditor({ ...editor, name: e.target.value })}
              placeholder="Contoh: FAQ pengiriman, katalog produk, kebijakan retur"
              className={field}
            />
          </label>
          <label className="block text-sm font-medium">
            Impor Markdown atau teks
            <input
              type="file"
              accept=".md,.txt,.markdown,text/plain,text/markdown"
              className="mt-1.5 block w-full text-sm text-rc-fg-muted file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-rc-border file:bg-rc-surface file:px-3 file:py-2 file:text-rc-fg"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                if (!/\.(md|txt|markdown)$/i.test(file.name) || file.size > 100_000) {
                  setError("Pilih file .md atau .txt maksimal 100 KB.");
                  e.target.value = "";
                  return;
                }
                void file
                  .text()
                  .then((content) => {
                    setEditor((current) => ({ ...current, name: current.name || file.name.replace(/\.[^.]+$/, ""), content: content.replace(/^﻿/, "") }));
                    setError("");
                  })
                  .catch(() => setError("File tidak dapat dibaca."));
                e.target.value = "";
              }}
            />
            <span className="mt-1 block text-xs font-normal text-rc-fg-muted">Maksimal 100 KB. Isinya bisa diedit sebelum disimpan.</span>
          </label>
          <label className="block text-sm font-medium">
            Isi pengetahuan
            <textarea
              value={editor.content}
              maxLength={100_000}
              rows={10}
              onChange={(e) => setEditor({ ...editor, content: e.target.value })}
              placeholder={"# Jam operasional\nSenin sampai Sabtu, pukul 09.00 sampai 17.00 WIB.\n\n# Pengiriman\nPesanan dikirim setiap hari kerja."}
              className={cn(field, "resize-y font-mono")}
            />
          </label>

          <div className="border-t border-rc-border pt-5">
            <p className="text-sm font-semibold text-rc-fg">Produk dan harga</p>
            <p className="mt-1 text-sm text-rc-fg-muted">Opsional. Dipakai agen untuk membuat penawaran dan menghitung total dengan tepat.</p>
            <div className="mt-4 flex flex-col gap-3">
              {editor.products.map((item, index) => (
                <div key={index} className="grid grid-cols-2 gap-3 rounded-lg bg-rc-bg p-4 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end">
                  <label className="col-span-2 text-xs font-medium text-rc-fg-muted sm:col-span-1">
                    Nama produk
                    <input value={item.name} onChange={(e) => product(index, { name: e.target.value })} required maxLength={120} className={field} />
                  </label>
                  <label className="text-xs font-medium text-rc-fg-muted">
                    Harga (Rp)
                    <input type="number" value={item.unit_price} onChange={(e) => product(index, { unit_price: Number(e.target.value) })} min={0} max={1_000_000_000} step={1} required className={field} />
                  </label>
                  <label className="text-xs font-medium text-rc-fg-muted">
                    Satuan
                    <input value={item.unit} onChange={(e) => product(index, { unit: e.target.value })} required maxLength={30} placeholder="pcs, box, pax" className={field} />
                  </label>
                  <label className="text-xs font-medium text-rc-fg-muted">
                    Minimal
                    <input type="number" value={item.min_order} onChange={(e) => product(index, { min_order: Number(e.target.value) })} min={1} max={1_000_000} step={1} required className={field} />
                  </label>
                  <button
                    type="button"
                    aria-label={`Hapus produk ${index + 1}`}
                    onClick={() => setEditor({ ...editor, products: editor.products.filter((_, i) => i !== index) })}
                    className="inline-flex h-10 w-10 cursor-pointer items-center justify-center justify-self-end rounded-md text-rc-fg-muted hover:bg-red-50 hover:text-red-700"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
            <Button
              purpose="action"
              className="mt-3 gap-1.5"
              disabled={editor.products.length >= 30 || busy !== null}
              onClick={() => setEditor({ ...editor, products: [...editor.products, { name: "", unit_price: 0, unit: "pcs", min_order: 1 }] })}
            >
              <Plus className="h-4 w-4" aria-hidden />
              Tambah produk
            </Button>
          </div>

          {error && <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
          <div className="flex justify-end gap-2 border-t border-rc-border pt-4">
            <Button purpose="action" disabled={busy === "editor"} onClick={() => setEditorOpen(false)}>
              Batal
            </Button>
            <Button purpose="action" style="primary" type="submit" disabled={busy === "editor" || !loaded}>
              {busy === "editor" ? "Menyimpan…" : "Simpan pengetahuan"}
            </Button>
          </div>
        </form>
      </SettingsDialog>

      {sourcesFor ? (
        <SettingsDialog
          open
          onOpenChange={(open) => !open && setSourcesFor(null)}
          busy={busy === "sources"}
          title={`Sumber pengetahuan ${channelLabel[sourcesFor]}`}
          description="Pilih pengetahuan yang boleh dipakai agen saat membalas di kanal ini."
        >
          <div className="flex flex-col gap-5">
            {knowledge.length ? (
              <div className="divide-y divide-rc-border rounded-lg border border-rc-border">
                {knowledge.map((document) => {
                  const on = draft.knowledge_base_ids.includes(document.id);
                  return (
                    <label key={document.id} className="flex cursor-pointer items-center justify-between gap-4 px-4 py-3 hover:bg-rc-surface-hover">
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-rc-fg">{document.name}</span>
                        <span className="block text-xs text-rc-fg-muted">{document.products.length} produk</span>
                      </span>
                      <input
                        type="checkbox"
                        checked={on}
                        onChange={(e) =>
                          setDraft({
                            ...draft,
                            knowledge_base_ids: e.target.checked
                              ? [...draft.knowledge_base_ids, document.id]
                              : draft.knowledge_base_ids.filter((id) => id !== document.id),
                          })
                        }
                        className="h-4 w-4 shrink-0 accent-[var(--rc-accent)]"
                      />
                    </label>
                  );
                })}
              </div>
            ) : (
              <p className="text-sm text-rc-fg-muted">Tambahkan pengetahuan terlebih dahulu.</p>
            )}
            <div className="flex justify-end gap-2 border-t border-rc-border pt-4">
              <Button purpose="action" disabled={busy === "sources"} onClick={() => setSourcesFor(null)}>
                Batal
              </Button>
              <Button
                purpose="action"
                style="primary"
                disabled={busy === "sources"}
                onClick={() =>
                  void run("sources", async () => {
                    await saveChannel(sourcesFor, draft, `Sumber pengetahuan ${channelLabel[sourcesFor]} disimpan.`);
                    setSourcesFor(null);
                  })
                }
              >
                {busy === "sources" ? "Menyimpan…" : "Simpan"}
              </Button>
            </div>
          </div>
        </SettingsDialog>
      ) : null}

      {customFor ? (
        <SettingsDialog
          open
          onOpenChange={(open) => !open && setCustomFor(null)}
          busy={busy === "custom"}
          title={`Gaya balasan ${channelLabel[customFor]}`}
          description="Tulis gaya balasan yang diinginkan. Agen mengikutinya untuk balasan berikutnya di kanal ini."
        >
          <form
            className="flex flex-col gap-5"
            onSubmit={(e) => {
              e.preventDefault();
              void run("custom", async () => {
                await saveChannel(customFor, { ...draft, tone: "custom" }, `Gaya balasan ${channelLabel[customFor]} disimpan.`);
                setCustomFor(null);
              });
            }}
          >
            <label className="block text-sm font-medium">
              Gaya balasan
              <textarea
                value={draft.custom_tone}
                onChange={(e) => setDraft({ ...draft, custom_tone: e.target.value })}
                rows={4}
                maxLength={500}
                required
                placeholder="Contoh: sapa pelanggan dengan Kak, tanpa emoji, maksimal dua paragraf."
                className={field}
              />
            </label>
            <div className="flex justify-end gap-2 border-t border-rc-border pt-4">
              <Button purpose="action" disabled={busy === "custom"} onClick={() => setCustomFor(null)}>
                Batal
              </Button>
              <Button purpose="action" style="primary" type="submit" disabled={busy === "custom" || !draft.custom_tone.trim()}>
                {busy === "custom" ? "Menyimpan…" : "Simpan gaya"}
              </Button>
            </div>
          </form>
        </SettingsDialog>
      ) : null}
    </>
  );
}
