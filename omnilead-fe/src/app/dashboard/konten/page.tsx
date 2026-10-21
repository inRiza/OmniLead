"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type BeContentIdeas } from "@/lib/api";
import { Button } from "@/components/action/button";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { Pill } from "@/components/primitives";

export default function KontenPage() {
  const [data, setData] = useState<BeContentIdeas | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await api.contentIdeas());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Gagal memuat ide konten");
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => void load(), 0);
    return () => clearTimeout(t);
  }, [load]);

  async function copy(title: string, caption: string) {
    try {
      await navigator.clipboard.writeText(caption);
      setCopied(title);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      /* clipboard tidak tersedia */
    }
  }

  return (
    <>
      <Topbar
        title="Konten"
        subtitle="Ide dari pertanyaan pelanggan. Draf saja, publish tetap Anda."
      />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="w-full max-w-[1400px] pt-1 pb-10">
          {error ? (
            <p role="alert" className="text-sm font-medium text-rc-danger">
              {error}
            </p>
          ) : null}

          {data ? (
            <p className="mb-3 text-sm text-rc-fg-muted">
              Dari {data.analyzed} pesan terbaru. Harga di caption hanya dari katalog; tidak ada yang
              dipublikasikan otomatis.
            </p>
          ) : null}

          {data && data.ideas.length === 0 ? (
            <p className="rounded-lg border border-rc-border bg-rc-surface px-4 py-8 text-center text-sm text-rc-fg-muted">
              Belum ada pola pertanyaan yang cukup sering. Ide muncul setelah topik yang sama ditanyakan
              lebih dari sekali.
            </p>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {data?.ideas.map((idea) => (
              <div
                key={idea.title}
                className="flex min-h-[11rem] flex-col rounded-lg border border-rc-border bg-rc-surface p-6"
              >
                <Pill tone="muted">{idea.format}</Pill>
                <h3 className="mt-2 text-base font-semibold leading-snug text-rc-fg">{idea.title}</h3>
                <p className="mt-1 text-sm text-rc-fg-muted">{idea.why}</p>
                <p className="mt-2 flex-1 rounded-md bg-rc-surface-hover/60 px-3 py-2 text-sm leading-relaxed text-rc-fg">
                  {idea.caption}
                </p>
                <div className="mt-4">
                  <Button
                    purpose="action"
                    style="secondary"
                    onClick={() => copy(idea.title, idea.caption)}
                  >
                    {copied === idea.title ? "Tersalin" : "Salin caption"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </ContentInset>
    </>
  );
}
