import type { Metadata } from "next";
import { DemoApp } from "@/components/demo/DemoApp";

export const metadata: Metadata = {
  title: "Coba demo | OmniLead",
  description: "Coba agen OmniLead langsung dengan data contoh: baca pesan, siapkan balasan, tunggu persetujuan, dan jadwalkan tugas.",
};

export default function DemoPage() {
  return <DemoApp />;
}
