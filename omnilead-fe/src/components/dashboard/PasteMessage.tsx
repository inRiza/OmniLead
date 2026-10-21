"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Channel } from "@/lib/types";
import { Button } from "@/components/action/button";
import { useDashboard } from "./DashboardContext";

// Tempel pesan dari kanal aktif untuk menyiapkan draf balasan.
const CHANNELS: { value: Channel; label: string }[] = [
  { value: "instagram", label: "Instagram" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "email", label: "Email" },
];
const MAX_IMAGE = 5 * 1024 * 1024;

function readBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = () => reject(new Error("Gagal membaca gambar"));
    reader.readAsDataURL(file);
  });
}

export function PasteMessage({ onCreated }: { onCreated: (eventId: string) => void }) {
  const { refresh } = useDashboard();
  const [channel, setChannel] = useState<Channel>("instagram");
  const [handle, setHandle] = useState("");
  const [name, setName] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = (file !== null || text.trim() !== "") && !busy;

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      let event;
      if (file) {
        if (file.size > MAX_IMAGE) throw new Error("Gambar melebihi 5 MB");
        event = await api.pasteImage({
          channel,
          image_base64: await readBase64(file),
          mime_type: file.type || "image/png",
        });
      } else {
        event = await api.pasteText({
          channel,
          text: text.trim(),
          handle: handle.trim(),
          name: name.trim() || undefined,
        });
      }
      setText("");
      setFile(null);
      await refresh();
      onCreated(event.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal memproses pesan");
    } finally {
      setBusy(false);
    }
  }

  const field =
    "w-full rounded-md border border-rc-border bg-rc-bg px-3 py-2 text-sm text-rc-fg outline-none focus:border-rc-fg";

  return (
    <div className="rounded-lg border border-rc-border bg-rc-surface p-6">
      <h2 className="text-sm font-semibold text-rc-fg">Tempel pesan dari kanal tanpa API</h2>
      <p className="mt-1 text-sm text-rc-fg-muted">
        Tempel teks atau unggah screenshot DM. Agen menyiapkan draf; Anda yang
        mengirim lewat <span className="font-medium text-rc-fg">Salin &amp; buka</span>.
      </p>

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1 text-sm font-medium text-rc-fg-subtle">
          Kanal
          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value as Channel)}
            className={field}
          >
            {CHANNELS.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-rc-fg-subtle">
          Handle / username
          <input
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            placeholder="@sari.home"
            className={field}
            disabled={file !== null}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-rc-fg-subtle">
          Nama (opsional)
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={field}
            disabled={file !== null}
          />
        </label>
      </div>

      <label className="mt-3 flex flex-col gap-1 text-sm font-medium text-rc-fg-subtle">
        Isi pesan
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          placeholder="kak bisa kirim hampers ke Bandung?"
          className={`${field} resize-none`}
          disabled={file !== null}
        />
      </label>

      <label className="mt-3 flex flex-col gap-1 text-sm font-medium text-rc-fg-subtle">
        Atau screenshot (PNG/JPG, maks 5 MB)
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm text-rc-fg"
        />
      </label>

      {error ? (
        <p role="alert" className="mt-2 text-sm font-medium text-rc-danger">
          {error}
        </p>
      ) : null}

      <div className="mt-3">
        <Button purpose="action" style="primary" disabled={!canSubmit} onClick={submit}>
          {busy ? "Memproses…" : file ? "Baca screenshot & proses" : "Proses pesan"}
        </Button>
      </div>
    </div>
  );
}
