"use client";

import { useMemo, useRef, useState, type MouseEvent } from "react";
import { BookOpen, MessageCircleQuestion, Package } from "lucide-react";
import type { KnowledgeBase } from "@/lib/api";

export type Topic = { id: string; title: string; why: string; mentions: number };

type Kind = "root" | "doc" | "product" | "topic";
type Node = { id: string; kind: Kind; label: string; x: number; y: number; r: number; detail: string; meta?: string };
type Edge = { a: string; b: string };

const W = 1100;
const H = 680;
const CX = W / 2;
const CY = H / 2;

const DOC_STOP = new Set(["&", "dan", "pelanggan", "produk", "harga", "katalog", "kebijakan"]);

function shortName(name: string) {
  return name.split("(")[0].trim();
}

function phrases(name: string) {
  const words = shortName(name).toLowerCase().split(/\s+/);
  const out = new Set<string>([words.join(" ")]);
  if (words.length >= 3) {
    out.add(words.slice(0, 2).join(" "));
    out.add(words.slice(-2).join(" "));
  }
  return [...out];
}

function polar(angle: number, r: number) {
  return { x: CX + Math.cos(angle) * r, y: CY + Math.sin(angle) * r * 0.78 };
}

function rupiah(n: number) {
  return `Rp${n.toLocaleString("id-ID")}`;
}

function businessInitials(name: string) {
  const parts = name.split(/\s+/).filter(Boolean);
  if (!parts.length) return "B";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function nodeTitle(n: Node) {
  if (n.kind === "product") return n.detail;
  return n.label;
}

function relax(nodes: Node[]) {
  const movable = nodes.filter((n) => n.kind !== "root");
  for (let iter = 0; iter < 48; iter++) {
    for (let i = 0; i < movable.length; i++) {
      for (let j = i + 1; j < movable.length; j++) {
        const a = movable[i];
        const b = movable[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const d = Math.hypot(dx, dy) || 1;
        const pad = a.kind === "topic" || b.kind === "topic" ? 28 : 20;
        const min = a.r + b.r + pad;
        if (d < min) {
          const push = (min - d) / 2;
          const nx = dx / d;
          const ny = dy / d;
          a.x -= nx * push;
          a.y -= ny * push;
          b.x += nx * push;
          b.y += ny * push;
        }
      }
    }
    movable.forEach((n) => {
      n.x = Math.min(W - 48, Math.max(48, n.x));
      n.y = Math.min(H - 48, Math.max(48, n.y));
    });
  }
}

export function buildGraph(docs: KnowledgeBase[], topics: Topic[], business: string) {
  const nodes: Node[] = [{ id: "root", kind: "root", label: business, x: CX, y: CY, r: 32, detail: "Semua pengetahuan yang dipakai agen untuk membalas pelanggan." }];
  const edges: Edge[] = [];
  const weights = docs.map((d) => Math.max(1, d.products.length));
  const total = weights.reduce((s, w) => s + w, 0) || 1;
  const angleOf = new Map<string, number>();
  let start = -Math.PI / 2;

  docs.forEach((d, i) => {
    const span = (weights[i] / total) * Math.PI * 2;
    const mid = start + span / 2;
    const p = polar(mid, 168);
    angleOf.set(`doc-${d.id}`, mid);
    nodes.push({ id: `doc-${d.id}`, kind: "doc", label: d.name, x: p.x, y: p.y, r: 16, detail: d.content.slice(0, 220), meta: d.products.length ? `${d.products.length} produk` : "Dokumen teks" });
    edges.push({ a: "root", b: `doc-${d.id}` });
    d.products.forEach((prod, j) => {
      const a = start + ((j + 0.5) / d.products.length) * span;
      const q = polar(a, 268);
      const id = `prod-${d.id}-${j}`;
      angleOf.set(id, a);
      nodes.push({ id, kind: "product", label: shortName(prod.name), x: q.x, y: q.y, r: 7, detail: prod.name, meta: `${rupiah(prod.unit_price)} per ${prod.unit}, minimal ${prod.min_order}` });
      edges.push({ a: `doc-${d.id}`, b: id });
    });
    start += span;
  });

  const placed: { t: Topic; angle: number; links: string[] }[] = [];
  topics.forEach((t, i) => {
    const text = `${t.title} ${t.why}`.toLowerCase();
    const links: string[] = [];
    docs.forEach((d) => {
      d.products.forEach((prod, j) => {
        if (phrases(prod.name).some((ph) => text.includes(ph))) links.push(`prod-${d.id}-${j}`);
      });
      if (!d.products.length) {
        const keys = d.name.toLowerCase().split(/[\s,]+/).filter((w) => w.length >= 2 && !DOC_STOP.has(w));
        if (keys.some((k) => text.includes(k))) links.push(`doc-${d.id}`);
      }
    });
    const angles = links.map((l) => angleOf.get(l)).filter((v): v is number => v !== undefined);
    const angle = angles.length ? angles.reduce((s, v) => s + v, 0) / angles.length : -Math.PI / 2 + ((i + 0.5) / Math.max(1, topics.length)) * Math.PI * 2;
    placed.push({ t, angle, links });
  });

  placed.sort((a, b) => a.angle - b.angle);
  const gap = Math.min(0.55, (Math.PI * 2) / Math.max(1, placed.length + 0.5));
  for (let i = 1; i < placed.length; i++) {
    if (placed[i].angle - placed[i - 1].angle < gap) placed[i].angle = placed[i - 1].angle + gap;
  }

  placed.forEach(({ t, angle, links }, i) => {
    const p = polar(angle, 388 + (i % 3) * 12);
    nodes.push({
      id: `topic-${t.id}`,
      kind: "topic",
      label: t.title,
      x: p.x,
      y: p.y,
      r: 8 + Math.min(6, t.mentions),
      detail: t.why,
      meta: `Ditanyakan ${t.mentions} kali`,
    });
    if (links.length) links.forEach((l) => edges.push({ a: `topic-${t.id}`, b: l }));
    else edges.push({ a: `topic-${t.id}`, b: "root" });
  });

  relax(nodes);
  return { nodes, edges, unlinked: placed.filter((p) => !p.links.length).map((p) => p.t) };
}

const STYLE: Record<Kind, { fill: string; stroke: string }> = {
  root: { fill: "#0144f5", stroke: "#0144f5" },
  doc: { fill: "#3d6dff", stroke: "#3d6dff" },
  product: { fill: "#ffffff", stroke: "#7d9dff" },
  topic: { fill: "#fff3dc", stroke: "#f5a524" },
};

export function KnowledgeGraph({ docs, topics, business }: { docs: KnowledgeBase[]; topics: Topic[]; business: string }) {
  const { nodes, edges } = useMemo(() => buildGraph(docs, topics, business), [docs, topics, business]);
  const chartRef = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [cursor, setCursor] = useState({ x: 0, y: 0 });
  const [selected, setSelected] = useState<string>("root");
  const focus = hover ?? selected;
  const linked = useMemo(() => {
    const set = new Set([focus]);
    edges.forEach((e) => {
      if (e.a === focus) set.add(e.b);
      if (e.b === focus) set.add(e.a);
    });
    return set;
  }, [edges, focus]);
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const current = byId.get(selected) ?? nodes[0];
  const hoverNode = hover ? byId.get(hover) : null;

  function trackCursor(event: MouseEvent) {
    const box = chartRef.current?.getBoundingClientRect();
    if (!box) return;
    setCursor({ x: event.clientX - box.left, y: event.clientY - box.top });
  }

  const neighbours = edges
    .filter((e) => e.a === current.id || e.b === current.id)
    .map((e) => byId.get(e.a === current.id ? e.b : e.a)!)
    .filter(Boolean);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <div
        ref={chartRef}
        className="relative overflow-hidden rounded-xl border border-rc-border bg-rc-surface"
        onMouseMove={trackCursor}
        onMouseLeave={() => setHover(null)}
      >
        {hoverNode ? (
          <div
            role="tooltip"
            className="pointer-events-none absolute z-10 max-w-[14rem] rounded px-2 py-1 text-[11px] leading-snug font-medium text-white shadow-md"
            style={{
              left: cursor.x + 12,
              top: cursor.y + 12,
              background: "rgba(15, 23, 42, 0.92)",
            }}
          >
            {nodeTitle(hoverNode)}
          </div>
        ) : null}
        <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label="Peta pengetahuan bisnis">
          <defs>
            <pattern id="kg-dots" width="22" height="22" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="1" fill="#e2e7f2" />
            </pattern>
          </defs>
          <rect width={W} height={H} fill="url(#kg-dots)" />
          {edges.map((e, i) => {
            const a = byId.get(e.a)!;
            const b = byId.get(e.b)!;
            const on = linked.has(e.a) && linked.has(e.b) && (e.a === focus || e.b === focus);
            return (
              <line
                key={i}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={on ? "#0144f5" : "#d8deea"}
                strokeWidth={on ? 1.5 : 1}
                strokeDasharray={a.kind === "topic" || b.kind === "topic" ? "3 5" : undefined}
                strokeLinecap="round"
                className="transition-[stroke,opacity] duration-200"
                opacity={on || focus === "root" ? 0.95 : 0.35}
              />
            );
          })}
          {nodes.map((n) => {
            const dim = !linked.has(n.id);
            const s = STYLE[n.kind];
            return (
              <g
                key={n.id}
                transform={`translate(${n.x} ${n.y})`}
                className="cursor-pointer transition-opacity duration-200"
                opacity={dim ? 0.35 : 1}
                onMouseEnter={(e) => {
                  setHover(n.id);
                  trackCursor(e);
                }}
                onClick={() => setSelected(n.id)}
              >
                <circle r={n.r + (selected === n.id ? 4 : 0)} fill={selected === n.id ? s.stroke : "transparent"} opacity={0.12} />
                <circle r={n.r} fill={s.fill} stroke={s.stroke} strokeWidth={n.kind === "product" || n.kind === "topic" ? 1.75 : 0} />
                {n.kind === "root" ? (
                  <text y={4} textAnchor="middle" className="pointer-events-none fill-white select-none text-[12px] font-semibold">
                    {businessInitials(n.label)}
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
        <div className="flex flex-wrap gap-x-5 gap-y-2 border-t border-rc-border px-5 py-3 text-xs text-rc-fg-muted">
          {[
            ["Dokumen pengetahuan", STYLE.doc],
            ["Produk", STYLE.product],
            ["Topik pertanyaan pelanggan", STYLE.topic],
          ].map(([label, st]) => (
            <span key={label as string} className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full border-2" style={{ background: (st as typeof STYLE.doc).fill, borderColor: (st as typeof STYLE.doc).stroke }} />
              {label as string}
            </span>
          ))}
          <span className="ml-auto">Hover untuk nama · klik untuk detail</span>
        </div>
      </div>

      <aside className="rounded-xl border border-rc-border bg-rc-surface p-5">
        <p className="flex items-center gap-1.5 text-xs font-medium text-rc-fg-muted">
          {current.kind === "topic" ? (
            <MessageCircleQuestion className="h-3.5 w-3.5" aria-hidden />
          ) : current.kind === "product" ? (
            <Package className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <BookOpen className="h-3.5 w-3.5" aria-hidden />
          )}
          {current.kind === "root" ? "Bisnis" : current.kind === "doc" ? "Dokumen" : current.kind === "product" ? "Produk" : "Topik pertanyaan"}
        </p>
        <h3 className="mt-1.5 text-base font-semibold text-rc-fg">{current.kind === "product" ? current.detail : current.label}</h3>
        {current.meta ? <p className="mt-1 text-sm font-medium text-rc-accent">{current.meta}</p> : null}
        {current.kind !== "product" && current.detail ? (
          <p className="mt-3 text-sm leading-relaxed whitespace-pre-line text-rc-fg-muted">{current.detail}</p>
        ) : null}
        {neighbours.length > 0 && (
          <div className="mt-5 border-t border-rc-border pt-4">
            <p className="text-xs font-medium text-rc-fg-muted">Terhubung dengan</p>
            <ul className="mt-2 flex flex-col gap-1">
              {neighbours.slice(0, 10).map((n) => (
                <li key={n.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(n.id)}
                    className="flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-rc-fg hover:bg-rc-surface-hover"
                  >
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full border-2" style={{ background: STYLE[n.kind].fill, borderColor: STYLE[n.kind].stroke }} />
                    <span className="truncate" title={nodeTitle(n)}>
                      {nodeTitle(n)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}
