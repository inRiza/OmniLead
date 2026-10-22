"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { LeadDetail, LeadProfile } from "@/lib/types";
import { stageLabel } from "@/lib/ui";
import { Button } from "@/components/action/button";
import { Select } from "@/components/ui/select";

type Stage = LeadProfile["stage"];
const STAGES: Stage[] = ["baru", "tertarik", "penawaran", "deal", "batal"];
const field = "mt-1 block w-full rounded-lg border border-rc-border bg-rc-bg px-3 py-2 text-sm text-rc-fg outline-none focus:border-rc-accent";

export function LeadManage({ lead, onSaved }: { lead: LeadDetail["lead"]; onSaved: () => Promise<void> }) {
  const [stage, setStage] = useState<Stage>(lead.stage);
  const [value, setValue] = useState(lead.estimatedValue?.toString() ?? "");
  const [lostReason, setLostReason] = useState(lead.lostReason ?? "");
  const [notes, setNotes] = useState(lead.notes ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      await api.updateLead(lead.id, {
        stage,
        notes,
        lost_reason: stage === "batal" ? lostReason : "",
        ...(value.trim() ? { estimated_value: Number(value.replace(/\D/g, "")) } : {}),
      });
      await onSaved();
      setMessage("Tersimpan.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Belum tersimpan");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border border-rc-border bg-rc-surface p-5">
      <p className="text-sm font-semibold text-rc-fg">Kelola lead</p>
      <p className="mt-1 text-xs text-rc-fg-muted">Ubah tahap bila agen belum tahu, misalnya DP sudah Anda terima.</p>
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div className="text-sm font-medium text-rc-fg">
          Tahap
          <Select
            label="Tahap"
            className="mt-1 w-full"
            value={stage}
            onChange={setStage}
            options={STAGES.map((s) => ({ value: s, label: stageLabel[s] }))}
          />
        </div>
        <label className="text-sm font-medium text-rc-fg">
          Nilai peluang (Rp)
          <input inputMode="numeric" value={value} onChange={(e) => setValue(e.target.value)} placeholder="Contoh: 2100000" className={field} />
        </label>
        {stage === "batal" && (
          <label className="text-sm font-medium text-rc-fg sm:col-span-2">
            Alasan batal
            <input value={lostReason} onChange={(e) => setLostReason(e.target.value)} maxLength={500} placeholder="Contoh: acara diundur" className={field} />
          </label>
        )}
        <label className="text-sm font-medium text-rc-fg sm:col-span-2">
          Catatan internal
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} maxLength={5000} placeholder="Hanya terlihat oleh Anda" className={field} />
        </label>
      </div>
      <div className="mt-4 flex items-center gap-3">
        <Button purpose="action" style="primary" disabled={busy} onClick={() => void save()}>
          {busy ? "Menyimpan…" : "Simpan"}
        </Button>
        {message && <p role="status" className="text-sm text-rc-fg-muted">{message}</p>}
      </div>
    </section>
  );
}
