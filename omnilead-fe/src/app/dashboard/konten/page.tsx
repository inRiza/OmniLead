"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, BookOpen, Check, CircleAlert, Copy, Lightbulb, MessageCircleQuestion, Package, RefreshCw, Sparkles } from "lucide-react";
import { api, type BeContentIdeas, type KnowledgeBase } from "@/lib/api";
import { Button } from "@/components/action/button";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { Badge } from "@/components/primitives";
import { KnowledgeGraph, buildGraph, type Topic } from "@/components/dashboard/KnowledgeGraph";
import { useAccount } from "@/components/dashboard/AccountProvider";

export default function KontenPage() {
  const { session } = useAccount();
  const business = session.user?.business ?? "Bisnis Anda";
  const [ideas, setIdeas] = useState<BeContentIdeas | null>(null);
  const [docs, setDocs] = useState<KnowledgeBase[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const [k, c] = await Promise.allSettled([api.knowledgeBases(), api.contentIdeas()]);
    if (k.status === "fulfilled") setDocs(k.value);
    if (c.status === "fulfilled") setIdeas(c.value);
    if (k.status === "rejected" || c.status === "rejected") {
      const reason = k.status === "rejected" ? k.reason : (c as PromiseRejectedResult).reason;
      setError(reason instanceof Error ? reason.message : "Data belum bisa dimuat");
      if (c.status === "rejected") setIdeas({ analyzed: 0, ideas: [] });
      if (k.status === "rejected") setDocs([]);
    }
  }, []);

  useEffect(() => {
    const t = setTimeout(() => void load(), 0);
    return () => clearTimeout(t);
  }, [load]);

  const topics = useMemo<Topic[]>(
    () => (ideas?.ideas ?? []).map((i, n) => ({ id: String(n), title: i.title, why: i.why, mentions: i.mentions })),
    [ideas],
  );

  const insight = useMemo(() => {
    if (!docs) return null;
    const g = buildGraph(docs, topics, business);
    const mentions = new Map(topics.map((t) => [`topic-${t.id}`, t.mentions]));
    const productHits = g.nodes
      .filter((n) => n.kind === "product")
      .map((p) => ({
        name: p.label,
        hits: g.edges.filter((e) => e.b === p.id && e.a.startsWith("topic-")).reduce((s, e) => s + (mentions.get(e.a) ?? 0), 0),
      }))
      .sort((a, b) => b.hits - a.hits);
    return {
      products: productHits.length,
      top: productHits.filter((p) => p.hits > 0).slice(0, 3),
      quiet: productHits.filter((p) => p.hits === 0).map((p) => p.name),
      unlinked: g.unlinked,
    };
  }, [docs, topics, business]);

  async function copy(title: string, caption: string) {
    try {
      await navigator.clipboard.writeText(caption);
      setCopied(title);
      setTimeout(() => setCopied(null), 2000);
    } catch {}
  }

  const loading = !docs || !ideas;
  const topTopic = [...topics].sort((a, b) => b.mentions - a.mentions)[0];

  return (
    <>
      <Topbar title="Konten" subtitle="Peta pengetahuan bisnis dan rekomendasi dari agen" />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-5 p-5 pb-10 md:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2">
              {[
                { icon: BookOpen, label: "Dokumen", value: docs?.length },
                { icon: Package, label: "Produk", value: insight?.products },
                { icon: MessageCircleQuestion, label: "Topik pertanyaan", value: topics.length },
                { icon: Sparkles, label: "Pesan dianalisis", value: ideas?.analyzed },
              ].map(({ icon: Icon, label, value }) => (
                <span key={label} className="inline-flex items-center gap-2 rounded-lg border border-rc-border bg-rc-surface px-3 py-2 text-sm">
                  <Icon className="h-4 w-4 text-rc-accent" aria-hidden />
                  <span className="text-rc-fg-muted">{label}</span>
                  <span className="font-semibold text-rc-fg tabular-nums">{value ?? "-"}</span>
                </span>
              ))}
            </div>
            <Button
              purpose="action"
              className="gap-1.5"
              disabled={loading}
              onClick={() => {
                setIdeas(null);
                setDocs(null);
                void load();
              }}
            >
              <RefreshCw className="h-4 w-4" aria-hidden />
              Analisis ulang
            </Button>
          </div>

          {error ? (
            <p role="alert" className="flex items-center gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              <CircleAlert className="h-4 w-4 shrink-0" aria-hidden />
              {error}
            </p>
          ) : null}

          {loading ? (
            <div className="h-[28rem] animate-pulse rounded-xl bg-rc-surface-hover" />
          ) : docs.length === 0 ? (
            <div className="rounded-xl border border-dashed border-rc-border-strong bg-rc-surface px-6 py-14 text-center">
              <p className="text-sm text-rc-fg-muted">Belum ada basis pengetahuan. Tambahkan katalog atau FAQ agar agen punya bahan untuk menjawab.</p>
              <Button purpose="nav" href="/dashboard/knowledge" style="primary" className="mt-4">
                Tambah pengetahuan
              </Button>
            </div>
          ) : (
            <KnowledgeGraph docs={docs} topics={topics} business={business} />
          )}

          {!loading && insight ? (
            <section className="rounded-xl bg-rc-accent-soft/60 p-5 md:p-6">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-rc-accent">
                <Sparkles className="h-3.5 w-3.5" aria-hidden />
                Ringkasan agen
              </p>
              <p className="mt-2 max-w-4xl text-sm leading-relaxed text-rc-fg">
                Dari {ideas.analyzed} pesan dalam 14 hari terakhir, agen menemukan {topics.length} topik yang sering ditanyakan
                {topTopic ? `. Topik paling sering adalah "${topTopic.title}" (${topTopic.mentions} kali)` : ""}
                {insight.top.length ? `. Produk yang paling banyak dibahas: ${insight.top.map((p) => p.name).join(", ")}` : ""}.
              </p>

              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-lg bg-rc-surface p-4">
                  <p className="flex items-center gap-1.5 text-sm font-semibold text-rc-fg">
                    <CircleAlert className="h-4 w-4 text-amber-600" aria-hidden />
                    Celah pengetahuan
                  </p>
                  {insight.unlinked.length ? (
                    <>
                      <p className="mt-1 text-xs text-rc-fg-muted">Topik ini belum punya jawaban di basis pengetahuan. Lengkapi agar balasan agen lebih akurat.</p>
                      <ul className="mt-3 flex flex-col gap-1.5">
                        {insight.unlinked.map((t) => (
                          <li key={t.id} className="flex items-start gap-2 text-sm text-rc-fg">
                            <MessageCircleQuestion className="mt-0.5 h-4 w-4 shrink-0 text-rc-fg-subtle" aria-hidden />
                            {t.title}
                          </li>
                        ))}
                      </ul>
                      <Link href="/dashboard/knowledge" className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-rc-accent hover:underline">
                        Lengkapi pengetahuan <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                      </Link>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-rc-fg-muted">Semua topik yang sering ditanyakan sudah tercakup di basis pengetahuan.</p>
                  )}
                </div>
                <div className="rounded-lg bg-rc-surface p-4">
                  <p className="flex items-center gap-1.5 text-sm font-semibold text-rc-fg">
                    <Lightbulb className="h-4 w-4 text-rc-accent" aria-hidden />
                    Peluang promosi
                  </p>
                  {insight.quiet.length ? (
                    <>
                      <p className="mt-1 text-xs text-rc-fg-muted">Produk ini jarang ditanyakan. Pertimbangkan konten khusus untuk mengenalkannya.</p>
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {insight.quiet.slice(0, 8).map((p) => (
                          <Badge key={p}>{p}</Badge>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-rc-fg-muted">Semua produk sudah sering dibahas pelanggan.</p>
                  )}
                </div>
              </div>
            </section>
          ) : null}

          {!loading && ideas.ideas.length > 0 ? (
            <section>
              <h2 className="mb-3 flex items-center gap-1.5 text-base font-semibold text-rc-fg">
                <Sparkles className="h-4 w-4 text-rc-accent" aria-hidden />
                Rekomendasi konten dari agen
              </h2>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {ideas.ideas.map((idea) => (
                  <article key={idea.title} className="flex flex-col rounded-xl border border-rc-border bg-rc-surface p-5">
                    <div className="flex items-center justify-between gap-2">
                      <Badge tone="blue">Format: {idea.format}</Badge>
                      <Badge>Ditanyakan {idea.mentions} kali</Badge>
                    </div>
                    <h3 className="mt-3 text-base leading-snug font-semibold text-rc-fg">{idea.title}</h3>
                    <p className="mt-1 text-sm text-rc-fg-muted">{idea.why}</p>
                    <p className="mt-4 flex-1 rounded-lg bg-rc-bg px-4 py-3 text-sm leading-relaxed whitespace-pre-line text-rc-fg">{idea.caption}</p>
                    <div className="mt-4 flex justify-end">
                      <Button purpose="action" style={copied === idea.title ? "secondary" : "primary"} className="gap-1.5" onClick={() => copy(idea.title, idea.caption)}>
                        {copied === idea.title ? <Check className="h-4 w-4" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
                        {copied === idea.title ? "Tersalin" : "Salin caption"}
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : !loading ? (
            <p className="rounded-xl border border-dashed border-rc-border-strong bg-rc-surface px-4 py-10 text-center text-sm text-rc-fg-muted">
              Belum cukup banyak pertanyaan berulang untuk dijadikan rekomendasi konten.
            </p>
          ) : null}
        </div>
      </ContentInset>
    </>
  );
}
