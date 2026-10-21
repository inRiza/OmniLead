import { cn } from "@/lib/utils";

// Tanda OmniLead: "O" terbuka (satu inbox untuk semua kanal) dengan titik di celahnya (lead yang ditangkap).
// Warna mengikuti token: kotak = --rc-primary, goresan = --rc-primary-fg.
export function LogoMark({
  size = 32,
  className,
  accent = false,
}: {
  size?: number;
  className?: string;
  /** Titik memakai saffron (dipakai di landing); default mengikuti warna goresan. */
  accent?: boolean;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden
      className={cn("shrink-0", className)}
    >
      <rect width="32" height="32" rx="8" fill="var(--rc-primary)" />
      <path
        d="M23.39 14.7A7.5 7.5 0 1 1 17.3 8.61"
        stroke="var(--rc-primary-fg)"
        strokeWidth="3.2"
        strokeLinecap="round"
      />
      <circle cx="21.6" cy="10.4" r="2.3" fill={accent ? "var(--rc-highlight)" : "var(--rc-primary-fg)"} />
    </svg>
  );
}

export function Logo({ className, accent = false }: { className?: string; accent?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark accent={accent} />
      <span className="text-base font-semibold tracking-tight text-rc-fg">OmniLead</span>
    </span>
  );
}
