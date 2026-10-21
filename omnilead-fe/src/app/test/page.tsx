"use client";

// Halaman uji integrasi Instagram (belum ada agen). Tombol di sini berperan
// sebagai aktuator: ambil post, ambil komentar, pantau komentar baru, dan
// balas komentar lewat antrean persetujuan (propose lalu approve).

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type BeChannel, type BeComment, type BePost } from "@/lib/api";
import { Button } from "@/components/action/button";
import { cn } from "@/lib/utils";

// Instagram Graph API dibatasi sekitar 200 panggilan/jam per akun.
// Polling tiap 20 detik = 180 panggilan/jam untuk satu post.
const POLL_MS = 20_000;

type LogEntry = { id: number; at: string; ok: boolean; text: string };

function clock(): string {
  return new Date().toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function errorText(e: unknown): string {
  if (e instanceof ApiError) return `${e.status} · ${e.message}`;
  return e instanceof Error ? e.message : String(e);
}

export default function InstagramTestPage() {
  const [channel, setChannel] = useState<BeChannel | null>(null);
  const [posts, setPosts] = useState<BePost[]>([]);
  const [selected, setSelected] = useState<BePost | null>(null);
  const [comments, setComments] = useState<BeComment[]>([]);
  const [fresh, setFresh] = useState<Set<string>>(new Set());
  const [watching, setWatching] = useState(false);
  const [lastCheck, setLastCheck] = useState<string>("");
  const [busy, setBusy] = useState<string>("");
  const [log, setLog] = useState<LogEntry[]>([]);
  const seen = useRef<Set<string>>(new Set());
  const logId = useRef(0);

  const addLog = useCallback((ok: boolean, text: string) => {
    logId.current += 1;
    const entry = { id: logId.current, at: clock(), ok, text };
    setLog((prev) => [entry, ...prev].slice(0, 50));
  }, []);

  useEffect(() => {
    api
      .channels()
      .then((list) => setChannel(list.find((c) => c.channel === "instagram") ?? null))
      .catch((e) => addLog(false, `Status kanal: ${errorText(e)}`));
  }, [addLog]);

  async function loadPosts() {
    setBusy("posts");
    try {
      const list = await api.posts("instagram", 12);
      setPosts(list);
      addLog(true, `Ambil post: ${list.length} post`);
    } catch (e) {
      addLog(false, `Ambil post: ${errorText(e)}`);
    } finally {
      setBusy("");
    }
  }

  const loadComments = useCallback(
    async (post: BePost, source: "manual" | "poll") => {
      try {
        const list = await api.comments("instagram", post.id, 50);
        const newOnes = list.filter((c) => !seen.current.has(c.id));
        // Panggilan pertama hanya mengisi daftar; yang "baru" dihitung sesudahnya.
        if (seen.current.size > 0 && newOnes.length > 0) {
          setFresh((prev) => new Set([...prev, ...newOnes.map((c) => c.id)]));
          addLog(true, `${newOnes.length} komentar baru: ${newOnes.map((c) => "@" + c.author_handle).join(", ")}`);
        }
        list.forEach((c) => seen.current.add(c.id));
        setComments(list);
        setLastCheck(clock());
        if (source === "manual") addLog(true, `Ambil komentar: ${list.length} komentar`);
      } catch (e) {
        addLog(false, `Ambil komentar: ${errorText(e)}`);
        if (source === "poll") setWatching(false);
      }
    },
    [addLog],
  );

  function selectPost(post: BePost) {
    setSelected(post);
    setComments([]);
    setFresh(new Set());
    setWatching(false);
    seen.current = new Set();
    void loadComments(post, "manual");
  }

  useEffect(() => {
    if (!watching || !selected) return;
    const t = setInterval(() => void loadComments(selected, "poll"), POLL_MS);
    return () => clearInterval(t);
  }, [watching, selected, loadComments]);

  async function reply(comment: BeComment, text: string): Promise<boolean> {
    if (!selected) return false;
    try {
      const proposed = await api.propose({
        channel: "instagram",
        kind: "reply_comment",
        post_ref: selected.id,
        comment_ref: comment.id,
        text,
        reason: "Uji coba dari halaman /test",
      });
      const done = await api.approve(proposed.id);
      if (done.status === "executed") {
        addLog(true, `Balasan ke @${comment.author_handle} terkirim (ref ${done.result_ref})`);
        return true;
      }
      addLog(false, `Balasan ke @${comment.author_handle}: ${done.status}${done.error ? " · " + done.error : ""}`);
    } catch (e) {
      addLog(false, `Balasan ke @${comment.author_handle}: ${errorText(e)}`);
    }
    return false;
  }

  const connected = channel?.connected ?? false;

  return (
    <div className="min-h-dvh bg-rc-bg text-rc-fg">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 p-4 md:p-8">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Uji integrasi Instagram</h1>
            <p className="mt-0.5 text-sm text-rc-fg-muted">
              Ambil post, baca komentar, pantau komentar baru, dan balas lewat antrean persetujuan.
            </p>
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-2 rounded-md border px-2.5 py-1 text-sm",
              connected ? "border-rc-border bg-rc-surface" : "border-rc-danger/30 bg-rc-danger-fg text-rc-danger",
            )}
          >
            <span className={cn("h-2 w-2 rounded-full", connected ? "bg-emerald-500" : "bg-rc-danger")} />
            {channel ? channel.detail : "Memeriksa koneksi..."}
          </span>
        </header>

        <div className="grid gap-5 lg:grid-cols-[1fr_1.1fr]">
          {/* Post */}
          <section className="rounded-lg border border-rc-border bg-rc-surface p-5">
            <div className="mb-4 flex items-center justify-between gap-2">
              <h2 className="text-base font-semibold">Post</h2>
              <Button purpose="action" style="primary" onClick={loadPosts} disabled={busy === "posts"}>
                {busy === "posts" ? "Mengambil..." : "Ambil post"}
              </Button>
            </div>
            {posts.length === 0 ? (
              <p className="rounded-md bg-rc-surface-hover px-3 py-6 text-center text-sm text-rc-fg-muted">
                Klik Ambil post untuk memuat post terbaru akun Instagram.
              </p>
            ) : (
              <ul className="flex max-h-[34rem] flex-col gap-2 overflow-y-auto pr-1">
                {posts.map((p) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      onClick={() => selectPost(p)}
                      className={cn(
                        "w-full rounded-md border px-3 py-2.5 text-left transition-colors",
                        selected?.id === p.id
                          ? "border-rc-fg bg-rc-surface-hover"
                          : "border-rc-border hover:bg-rc-surface-hover",
                      )}
                    >
                      <p className="line-clamp-2 text-sm">{p.caption || "(tanpa caption)"}</p>
                      <div className="mt-1.5 flex items-center gap-3 text-xs text-rc-fg-muted">
                        <span>{p.comment_count ?? 0} komentar</span>
                        {p.created_at && <span>{new Date(p.created_at).toLocaleDateString("id-ID")}</span>}
                        <span className="ml-auto font-mono text-rc-fg-subtle">{p.id}</span>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* Komentar */}
          <section className="rounded-lg border border-rc-border bg-rc-surface p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <h2 className="text-base font-semibold">Komentar</h2>
                <p className="truncate text-xs text-rc-fg-muted">
                  {selected ? (lastCheck ? `Dicek ${lastCheck}` : "Memuat...") : "Pilih post di sebelah kiri"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  purpose="action"
                  style="secondary"
                  disabled={!selected}
                  onClick={() => selected && void loadComments(selected, "manual")}
                >
                  Ambil komentar
                </Button>
                <Button
                  purpose="action"
                  style={watching ? "primary" : "secondary"}
                  disabled={!selected}
                  onClick={() => setWatching((v) => !v)}
                >
                  <span className={cn("mr-2 h-2 w-2 rounded-full", watching ? "animate-pulse bg-emerald-400" : "bg-rc-fg-subtle")} />
                  {watching ? "Memantau (20 dtk)" : "Pantau real-time"}
                </Button>
              </div>
            </div>

            {selected?.url && (
              <a
                href={selected.url}
                target="_blank"
                rel="noreferrer"
                className="mb-3 inline-block text-xs text-rc-accent underline-offset-2 hover:underline"
              >
                Buka post di Instagram
              </a>
            )}

            {selected && comments.length === 0 ? (
              <div className="rounded-md bg-rc-surface-hover px-3 py-4 text-sm text-rc-fg-muted">
                <p>Belum ada komentar yang bisa dibaca.</p>
                {(selected.comment_count ?? 0) > 0 && (
                  <p className="mt-2 text-xs">
                    Post ini punya {selected.comment_count} komentar, tapi API tidak mengembalikannya. Dengan Standard
                    Access, komentar biasanya hanya terbaca bila ditulis oleh akun yang punya role di app (Instagram
                    tester/admin) atau oleh akun bisnis ini sendiri. Coba tulis komentar baru dari akun tersebut,
                    lalu klik Ambil komentar.
                  </p>
                )}
              </div>
            ) : (
              <ul className="flex max-h-[30rem] flex-col gap-2 overflow-y-auto pr-1">
                {comments.map((c) => (
                  <CommentRow key={c.id} comment={c} isNew={fresh.has(c.id)} onReply={reply} />
                ))}
              </ul>
            )}
          </section>
        </div>

        {/* Log aktuator */}
        <section className="rounded-lg border border-rc-border bg-rc-surface p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Log</h2>
            <span className="text-xs text-rc-fg-subtle">{log.length} kejadian</span>
          </div>
          {log.length === 0 ? (
            <p className="text-sm text-rc-fg-muted">Belum ada aktivitas.</p>
          ) : (
            <ul className="max-h-60 space-y-1 overflow-y-auto font-mono text-xs">
              {log.map((l) => (
                <li key={l.id} className="flex gap-3">
                  <span className="text-rc-fg-subtle">{l.at}</span>
                  <span className={l.ok ? "text-rc-fg" : "text-rc-danger"}>{l.text}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

function CommentRow({
  comment,
  isNew,
  onReply,
}: {
  comment: BeComment;
  isNew: boolean;
  onReply: (c: BeComment, text: string) => Promise<boolean>;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  async function submit() {
    if (!text.trim()) return;
    setSending(true);
    const ok = await onReply(comment, text.trim());
    setSending(false);
    if (ok) {
      setSent(true);
      setOpen(false);
      setText("");
    }
  }

  return (
    <li className={cn("rounded-md border px-3 py-2.5", isNew ? "border-emerald-400 bg-emerald-50" : "border-rc-border")}>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">@{comment.author_handle || "tanpa nama"}</span>
        {isNew && <span className="rounded bg-emerald-500 px-1.5 py-0.5 text-[10px] font-semibold text-white">Baru</span>}
        {comment.parent_id && <span className="text-xs text-rc-fg-subtle">balasan</span>}
        <span className="ml-auto text-xs text-rc-fg-subtle">
          {comment.created_at ? new Date(comment.created_at).toLocaleString("id-ID") : ""}
        </span>
      </div>
      <p className="mt-1 text-sm">{comment.text}</p>

      <div className="mt-2 flex items-center gap-2">
        {sent && <span className="text-xs text-emerald-600">Balasan terkirim</span>}
        <Button purpose="action" style="ghost" className="ml-auto px-2 py-1 text-xs" onClick={() => setOpen((v) => !v)}>
          {open ? "Batal" : "Balas"}
        </Button>
      </div>

      {open && (
        <div className="mt-2 flex flex-col gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={2}
            placeholder="Tulis balasan publik untuk komentar ini"
            className="w-full resize-none rounded-md border border-rc-border bg-rc-bg px-3 py-2 text-sm outline-none focus:border-rc-fg"
          />
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs text-rc-fg-muted">Dikirim lewat antrean: propose lalu approve.</p>
            <Button purpose="action" style="primary" disabled={sending || !text.trim()} onClick={submit}>
              {sending ? "Mengirim..." : "Setujui & kirim"}
            </Button>
          </div>
        </div>
      )}
    </li>
  );
}
