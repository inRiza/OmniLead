"use client";

import { useEffect, useState } from "react";
import { timeAgo } from "@/lib/ui";

// Render jam absolut saat server/first paint (deterministik, aman untuk
// prerender), lalu beralih ke "X mnt lalu" setelah mount di klien.
function clock(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
}

export function TimeAgo({ iso }: { iso: string }) {
  const [label, setLabel] = useState(() => clock(iso));

  useEffect(() => {
    const tick = () => setLabel(timeAgo(iso));
    const first = setTimeout(tick, 0); // bukan sinkron di body effect
    const t = setInterval(tick, 60000);
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [iso]);

  return <span suppressHydrationWarning>{label}</span>;
}
