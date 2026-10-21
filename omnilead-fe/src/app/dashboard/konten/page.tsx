import { ContentInset } from "@/components/dashboard/ContentInset";
import { Topbar } from "@/components/dashboard/Topbar";
import { Button } from "@/components/action/button";
import { Pill } from "@/components/primitives";

const ideas = [
  {
    title: "Paket katering kantor 50–100 pax",
    why: "Banyak tanya harga kapasitas besar minggu ini.",
    format: "Carousel IG",
  },
  {
    title: "Pesan hampers jauh hari sebelum musim ramai",
    why: "Pertanyaan “ready kapan” naik.",
    format: "Reel",
  },
  {
    title: "Menu favorit pelanggan korporat",
    why: "Lead kantor nanya menu yang sama berulang.",
    format: "Post",
  },
];

export default function KontenPage() {
  return (
    <>
      <Topbar
        title="Konten"
        subtitle="Ide dari pertanyaan pelanggan. Draf saja, publish tetap Anda."
      />
      <ContentInset className="rc-scrollbar overflow-y-auto">
        <div className="mx-auto w-full max-w-4xl px-4 pt-4 md:px-6 md:pt-6">
          <p className="rounded-lg border border-rc-border bg-rc-surface px-3 py-2 text-sm text-rc-fg-muted">
            <span className="mr-2 rounded-md bg-rc-fg px-1.5 py-0.5 text-sm font-semibold text-rc-primary-fg">
              SIMULASI
            </span>
            Contoh ide statis. Belum dihasilkan agen dari pertanyaan pelanggan
            nyata.
          </p>
        </div>
        <div className="mx-auto grid w-full max-w-4xl gap-3 p-4 pb-8 sm:grid-cols-2 md:p-6 lg:grid-cols-3">
          {ideas.map((idea) => (
            <div
              key={idea.title}
              className="flex min-h-[11rem] flex-col rounded-lg border border-rc-border bg-rc-surface p-6"
            >
              <Pill tone="muted">{idea.format}</Pill>
              <h3 className="mt-2 text-base font-semibold leading-snug text-rc-fg">
                {idea.title}
              </h3>
              <p className="mt-1 flex-1 text-sm text-rc-fg-muted">{idea.why}</p>
              <div className="mt-4 flex gap-2">
                <Button purpose="action" style="primary" disabled>
                  Buat draf
                </Button>
                <Button purpose="action" style="ghost" disabled>
                  Lewati
                </Button>
              </div>
            </div>
          ))}
        </div>
      </ContentInset>
    </>
  );
}
