import { channelStatuses } from "@/lib/mock";
import { channelLabel } from "@/lib/ui";
import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { ChannelIcon, Dot, Pill } from "@/components/primitives";

const actionLabel: Record<string, string> = {
  list_posts: "Daftar post",
  read_comments: "Baca komentar",
  post_comment: "Tulis komentar",
  reply_comment: "Balas komentar",
  send_dm: "Kirim pesan",
};

export default function IntegrasiPage() {
  return (
    <>
      <Topbar
        title="Integrasi"
        subtitle="Kanal yang terhubung ke bisnis Anda"
      />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-3 p-4 pb-8 md:p-6">
          {channelStatuses.map((c) => (
            <div
              key={c.channel}
              className="rounded-lg border border-rc-border bg-rc-surface p-6"
            >
              <div className="flex items-center gap-3">
                <ChannelIcon channel={c.channel} size="md" />
                <div className="min-w-0 flex-1">
                  <div className="text-base font-semibold text-rc-fg">
                    {channelLabel[c.channel]}
                  </div>
                  <div className="text-sm text-rc-fg-muted">{c.detail}</div>
                </div>
                <span className="flex shrink-0 items-center gap-1.5 rounded-md bg-rc-surface-hover/70 px-2 py-1 text-xs text-rc-fg-muted">
                  <Dot ok={c.connected} />
                  {c.connected ? "Aktif" : "Putus"}
                </span>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {c.capabilities.map((cap) => (
                  <span
                    key={cap.action}
                    className="inline-flex items-center gap-2 rounded-md border border-rc-border/80 bg-rc-bg px-2.5 py-1.5 text-xs"
                  >
                    <span className="font-medium text-rc-fg">
                      {actionLabel[cap.action] ?? cap.action}
                    </span>
                    {cap.available ? (
                      <Pill tone="muted">
                        {cap.path === "handoff" ? "Handoff" : "API"}
                      </Pill>
                    ) : (
                      <Pill tone="outline">Off</Pill>
                    )}
                  </span>
                ))}
              </div>
            </div>
          ))}

          <p className="text-sm text-rc-fg-muted">
            Kalau kanal tidak punya API, agen siapkan teks — Anda yang kirim
            (handoff).
          </p>
        </div>
      </ContentInset>
    </>
  );
}
