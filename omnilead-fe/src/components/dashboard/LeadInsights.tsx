import { ArrowRight, CalendarDays, MapPin, Package, Sparkles, Wallet, Hash, Coins } from "lucide-react";
import type { LeadNeeds, LeadScore } from "@/lib/types";
import { cn } from "@/lib/ui";
import { ScoreBadge } from "@/components/primitives";
import { TimeAgo } from "@/components/TimeAgo";

const idr = new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 });

function day(iso?: string) {
  if (!iso) return undefined;
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

export function LeadInsights({
  summary,
  score,
  scoreValue,
  reasons,
  analysis,
  needs,
  estimatedValue,
  nextStep,
  scoredAt,
  className,
}: {
  summary?: string;
  score: LeadScore;
  scoreValue: number;
  reasons: string[];
  analysis?: string;
  needs: LeadNeeds;
  estimatedValue?: number | null;
  nextStep?: string;
  scoredAt?: string;
  className?: string;
}) {
  const fields = [
    { icon: Package, label: "Produk", value: needs.product },
    { icon: Hash, label: "Jumlah", value: needs.qty ? `${needs.qty} ${needs.unit ?? ""}`.trim() : undefined },
    { icon: CalendarDays, label: "Tenggat", value: day(needs.date) },
    { icon: MapPin, label: "Lokasi", value: needs.location },
    { icon: Wallet, label: "Anggaran", value: needs.budget ? idr.format(needs.budget) : undefined },
    { icon: Coins, label: "Potensi nilai", value: estimatedValue ? `±${idr.format(estimatedValue)}` : undefined },
  ];
  return (
    <section className={cn("overflow-hidden rounded-xl border border-rc-border bg-rc-surface", className)}>
      <div className="flex flex-wrap items-start justify-between gap-4 bg-rc-accent-soft/50 p-5">
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 text-xs font-semibold text-rc-accent">
            <Sparkles className="h-3.5 w-3.5" aria-hidden />
            Ringkasan AI
          </p>
          <p className={cn("mt-2 text-sm leading-relaxed", summary ? "text-rc-fg" : "text-rc-fg-subtle")}>
            {summary || "Belum ada ringkasan. Klik Jawab dengan agen untuk menganalisis pesan ini."}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-rc-fg-muted">Priority score</p>
          <div className="mt-1 flex items-center justify-end gap-2">
            <span className="text-2xl font-semibold tracking-tight text-rc-fg tabular-nums">{scoreValue}</span>
            <ScoreBadge score={score} />
          </div>
          {scoredAt ? (
            <p className="mt-1 text-[11px] text-rc-fg-subtle">
              Dihitung <TimeAgo iso={scoredAt} />
            </p>
          ) : null}
        </div>
      </div>

      <div className="grid gap-5 p-5 md:grid-cols-2">
        <div>
          <p className="text-xs font-medium text-rc-fg-muted">Analisis skor</p>
          <p className={cn("mt-2 text-sm leading-relaxed", analysis || reasons.length ? "text-rc-fg" : "text-rc-fg-subtle")}>
            {analysis || (reasons.length ? `Sinyal yang ditemukan: ${reasons.slice(0, 3).join(", ").toLowerCase()}.` : "Belum diketahui")}
          </p>
          <p className="mt-3 text-[11px] leading-relaxed text-rc-fg-subtle">
            Skor dari rubrik awal: niat membeli, nilai pesanan, tenggat, dan kebutuhan tindak lanjut. Bukan peluang beli yang sudah tervalidasi.
          </p>
        </div>
        <div>
          <p className="text-xs font-medium text-rc-fg-muted">Kebutuhan pelanggan</p>
          <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2.5">
            {fields.map(({ icon: Icon, label, value }) => (
              <div key={label} className="flex min-w-0 gap-2">
                <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-rc-fg-subtle" aria-hidden />
                <div className="min-w-0">
                  <dt className="text-[11px] text-rc-fg-muted">{label}</dt>
                  <dd className={cn("truncate text-sm", value ? "text-rc-fg" : "text-rc-fg-subtle")}>{value ?? "Belum diketahui"}</dd>
                </div>
              </div>
            ))}
          </dl>
        </div>
      </div>

      {nextStep ? (
        <div className="flex gap-2.5 border-t border-rc-border px-5 py-3.5 text-sm">
          <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-rc-accent" aria-hidden />
          <p>
            <span className="font-medium text-rc-fg">Langkah berikutnya. </span>
            <span className="text-rc-fg-muted">{nextStep}</span>
          </p>
        </div>
      ) : null}
    </section>
  );
}
