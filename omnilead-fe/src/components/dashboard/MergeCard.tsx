"use client";

import type { LeadProfile, ProposedAction } from "@/lib/types";
import { channelLabel } from "@/lib/ui";
import { ChannelIcon } from "@/components/primitives";

function confidenceLabel(value: number): string {
  if (value >= 0.75) return "tinggi";
  if (value >= 0.5) return "sedang";
  return "rendah";
}

function ProfileBox({ title, lead }: { title: string; lead?: LeadProfile }) {
  return (
    <div className="flex-1 rounded-md border border-rc-border bg-rc-bg p-3">
      <p className="text-sm font-medium text-rc-fg-subtle">{title}</p>
      {lead ? (
        <>
          <p className="mt-1 text-sm font-semibold text-rc-fg">{lead.name}</p>
          {lead.company ? (
            <p className="text-sm text-rc-fg-muted">{lead.company}</p>
          ) : null}
          <p className="mt-1 text-sm text-rc-fg-muted">
            Tahap {lead.stage}
            {lead.scoreValue ? ` · skor ${lead.scoreValue}` : ""}
          </p>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {lead.channels.map((c) => (
              <span
                key={c}
                className="inline-flex items-center gap-1 rounded-md bg-rc-surface-hover/70 px-1.5 py-0.5 text-sm text-rc-fg-muted"
              >
                <ChannelIcon channel={c} />
                {channelLabel[c]}
              </span>
            ))}
          </div>
        </>
      ) : (
        <p className="mt-1 text-sm text-rc-fg-muted">Profil tidak ditemukan</p>
      )}
    </div>
  );
}

/** Usulan gabung identitas: dua profil berdampingan beserta bukti dan keyakinan. */
export function MergeEvidence({
  action,
  leadsById,
}: {
  action: ProposedAction;
  leadsById: Record<string, LeadProfile>;
}) {
  const source = leadsById[String(action.payload.source_lead_id ?? "")];
  const target = leadsById[String(action.payload.target_lead_id ?? "")];
  const confidence = Number(action.payload.confidence ?? 0);
  const evidence = Array.isArray(action.payload.evidence)
    ? (action.payload.evidence as string[])
    : [];

  return (
    <div className="mt-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <ProfileBox title="Profil baru" lead={source} />
        <ProfileBox title="Profil yang sudah ada" lead={target} />
      </div>
      <p className="mt-3 text-sm font-medium text-rc-fg">
        Keyakinan {Math.round(confidence * 100)}% ({confidenceLabel(confidence)})
      </p>
      <div
        className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-rc-surface-hover"
        role="progressbar"
        aria-valuenow={Math.round(confidence * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Keyakinan merge"
      >
        <div
          className="h-full rounded-full bg-rc-fg"
          style={{ width: `${Math.round(confidence * 100)}%` }}
        />
      </div>
      <ul className="mt-2 list-disc pl-4 text-sm text-rc-fg-muted">
        {evidence.map((e) => (
          <li key={e}>{e}</li>
        ))}
      </ul>
      <p className="mt-2 text-sm text-rc-fg-muted">
        Agen tidak pernah menggabungkan profil sendiri. Setelah disetujui, semua
        riwayat dipindahkan ke profil yang sudah ada.
      </p>
    </div>
  );
}
