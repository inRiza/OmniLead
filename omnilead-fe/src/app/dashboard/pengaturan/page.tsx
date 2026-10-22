"use client";

import { useState, type ReactNode } from "react";
import { CircleCheck, Pencil, Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Channel } from "@/lib/types";
import { channelLabel, cn } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { ChannelIcon } from "@/components/primitives";
import { Button } from "@/components/action/button";
import { Select } from "@/components/ui/select";
import { SettingsDialog } from "@/components/dashboard/SettingsDialog";
import { useDashboard } from "@/components/dashboard/DashboardContext";

const CHANNELS: Channel[] = ["whatsapp", "instagram", "facebook", "email"];

function Toggle({ on, onChange, label, disabled }: { on: boolean; onChange: () => void; label: string; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      disabled={disabled}
      onClick={onChange}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200 disabled:cursor-not-allowed disabled:opacity-50",
        on ? "bg-rc-accent" : "bg-rc-border-strong",
      )}
    >
      <span className={cn("inline-block h-5 w-5 rounded-full bg-white transition-transform duration-200", on ? "translate-x-[22px]" : "translate-x-0.5")} />
    </button>
  );
}

function Row({ title, body, children }: { title: string; body: ReactNode; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-6 py-4 first:pt-0 last:pb-0">
      <div className="min-w-0">
        <p className="text-base font-semibold text-rc-fg">{title}</p>
        <p className="mt-1 text-sm text-rc-fg-muted">{body}</p>
      </div>
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const d = useDashboard();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);

  async function run(key: string, fn: () => Promise<void>) {
    setBusy(key);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Pengaturan belum tersimpan");
    } finally {
      setBusy(null);
    }
  }

  const preferences = d.settings?.preferences ?? [];

  return (
    <>
      <Topbar title="Pengaturan agen" subtitle="Atur kapan dan di kanal mana agen boleh bekerja" />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 p-4 pb-10 md:p-6">
          {error && <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

          <section className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
            <h2 className="text-lg font-semibold text-rc-fg">Status agen</h2>
            <div className="mt-5 divide-y divide-rc-border">
              <Row
                title={d.paused ? "Agen sedang dijeda" : "Agen aktif"}
                body={d.paused ? "Semua aksi ditahan. Pesan baru tetap dicatat dan dianalisis setelah agen dilanjutkan." : "Agen membaca pesan baru dan menyiapkan balasan di semua kanal yang aktif."}
              >
                <Toggle on={!d.paused} label="Agen aktif" disabled={busy !== null || !d.loaded} onChange={() => void run("pause", d.togglePause)} />
              </Row>
              <Row title="Mode latihan" body="Agen tetap bekerja, tetapi tidak ada pesan yang benar-benar terkirim ke pelanggan.">
                <Toggle on={d.dryRun} label="Mode latihan" disabled={busy !== null || !d.loaded} onChange={() => void run("dry", () => d.setDryRun(!d.dryRun))} />
              </Row>
            </div>
          </section>

          <section className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
            <h2 className="text-lg font-semibold text-rc-fg">Kanal yang boleh dibalas agen</h2>
            <p className="mt-2 text-sm text-rc-fg-muted">Matikan kanal tertentu tanpa memutus koneksinya.</p>
            <div className="mt-5 divide-y divide-rc-border">
              {CHANNELS.map((c) => {
                const enabled = !d.disabledChannels.includes(c);
                const status = d.channels.find((x) => x.channel === c);
                return (
                  <div key={c} className="flex items-center gap-3 py-4 first:pt-0 last:pb-0">
                    <ChannelIcon channel={c} size="md" />
                    <div className="min-w-0 flex-1">
                      <p className="text-base font-semibold text-rc-fg">{channelLabel[c]}</p>
                      <p className="mt-1 text-sm text-rc-fg-muted">{status?.connected ? "Terhubung" : "Belum terhubung"}</p>
                    </div>
                    <Toggle
                      on={enabled}
                      label={`Agen di ${channelLabel[c]}`}
                      disabled={busy !== null || !d.loaded}
                      onChange={() => void run(c, () => d.setChannelEnabled(c, !enabled))}
                    />
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-xl border border-rc-border bg-rc-surface p-5 md:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-rc-fg">Batas & preferensi</h2>
                <p className="mt-2 text-sm text-rc-fg-muted">Aturan yang selalu diikuti agen saat menyiapkan dan mengirim balasan.</p>
              </div>
              <Button purpose="action" className="gap-1.5" disabled={!d.loaded} onClick={() => setEditing(true)}>
                <Pencil className="h-4 w-4" aria-hidden />
                Ubah
              </Button>
            </div>
            <dl className="mt-5 grid gap-4 border-t border-rc-border pt-5 sm:grid-cols-2">
              <div>
                <dt className="text-xs font-medium text-rc-fg-muted">Batas kirim</dt>
                <dd className="mt-1 text-sm font-semibold text-rc-fg">{d.settings?.rate_limit_per_hour ?? "-"} pesan per jam per kanal</dd>
              </div>
              <div>
                <dt className="text-xs font-medium text-rc-fg-muted">Jumlah aturan</dt>
                <dd className="mt-1 text-sm font-semibold text-rc-fg">{preferences.length} aturan aktif</dd>
              </div>
            </dl>
            {preferences.length > 0 ? (
              <ul className="mt-5 flex flex-col gap-2">
                {preferences.map((p) => (
                  <li key={p} className="flex items-start gap-2.5 rounded-lg bg-rc-bg px-3.5 py-2.5 text-sm text-rc-fg">
                    <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-rc-accent" aria-hidden />
                    {p}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-5 text-sm text-rc-fg-muted">Belum ada aturan. Klik Ubah untuk menambahkan.</p>
            )}
          </section>
        </div>
      </ContentInset>
      <SettingsDialog
        open={editing}
        onOpenChange={setEditing}
        busy={busy === "prefs"}
        wide
        title="Ubah batas & preferensi"
        description="Perubahan berlaku untuk balasan berikutnya di semua kanal bisnis ini."
      >
        {editing && (
          <PreferencesForm
            rate={d.settings?.rate_limit_per_hour ?? 30}
            preferences={preferences}
            busy={busy === "prefs"}
            onCancel={() => setEditing(false)}
            onSave={(rate, prefs) =>
              void run("prefs", async () => {
                await api.patchSettings({ rate_limit_per_hour: rate, preferences: prefs });
                await d.refresh();
                setEditing(false);
              })
            }
          />
        )}
      </SettingsDialog>
    </>
  );
}

const RATES = [10, 20, 30, 50, 100, 200];

const TEMPLATES = [
  "Selalu sapa pelanggan dengan Kak",
  "Jangan sebut harga di komentar publik, arahkan ke DM",
  "Diskon maksimal 5% dan hanya untuk pesanan besar",
  "Tawarkan DP 50% untuk pesanan di atas Rp1.000.000",
  "Balas dalam Bahasa Indonesia yang ramah dan singkat",
];

function PreferencesForm({
  rate,
  preferences,
  busy,
  onCancel,
  onSave,
}: {
  rate: number;
  preferences: string[];
  busy: boolean;
  onCancel: () => void;
  onSave: (rate: number, preferences: string[]) => void;
}) {
  const [limit, setLimit] = useState(String(rate));
  const [items, setItems] = useState<string[]>(preferences.length ? preferences : [""]);
  const options = [...new Set([...RATES, rate])].sort((a, b) => a - b);
  const unused = TEMPLATES.filter((t) => !items.includes(t));

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        onSave(Number(limit), items.map((i) => i.trim()).filter(Boolean));
      }}
    >
      <div className="text-sm font-medium">
        Batas kirim per jam per kanal
        <Select
          className="mt-1.5"
          label="Batas kirim per jam"
          value={limit}
          onChange={setLimit}
          options={options.map((r) => ({ value: String(r), label: `${r} pesan per jam` }))}
        />
      </div>

      <fieldset>
        <legend className="text-sm font-medium">Aturan balasan</legend>
        <div className="mt-2 flex flex-col gap-2">
          {items.map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                value={item}
                onChange={(e) => setItems((cur) => cur.map((v, j) => (j === i ? e.target.value : v)))}
                maxLength={200}
                placeholder="Tulis aturan, misalnya: selalu tawarkan ongkir gratis di Jakarta Timur"
                className="min-h-10 flex-1 rounded-md border border-rc-border bg-rc-surface px-3 text-sm text-rc-fg outline-none placeholder:text-rc-fg-subtle focus:border-rc-accent focus:ring-2 focus:ring-rc-accent/15"
              />
              <button
                type="button"
                aria-label="Hapus aturan"
                onClick={() => setItems((cur) => cur.filter((_, j) => j !== i))}
                className="inline-flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-md text-rc-fg-muted hover:bg-red-50 hover:text-red-700"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button purpose="action" className="gap-1.5" onClick={() => setItems((cur) => [...cur, ""])}>
            <Plus className="h-4 w-4" aria-hidden />
            Tambah aturan
          </Button>
          {unused.length > 0 && (
            <Select<string>
              label="Pakai contoh aturan"
              className="w-56"
              value={null}
              placeholder="Pakai contoh aturan"
              onChange={(t) => setItems((cur) => [...cur.filter((v) => v.trim()), t])}
              options={unused.map((t) => ({ value: t, label: t }))}
            />
          )}
        </div>
      </fieldset>

      <div className="flex justify-end gap-2 border-t border-rc-border pt-4">
        <Button purpose="action" disabled={busy} onClick={onCancel}>
          Batal
        </Button>
        <Button purpose="action" style="primary" type="submit" disabled={busy}>
          {busy ? "Menyimpan…" : "Simpan"}
        </Button>
      </div>
    </form>
  );
}
