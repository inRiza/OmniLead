import { cn } from "@/lib/utils";

const CONTOURS = [
  "M-40 120 C 120 60 220 260 380 220 S 600 40 760 140 S 980 360 1160 260 S 1400 120 1500 200",
  "M-60 520 C 140 460 260 640 460 600 S 720 420 900 500 S 1160 700 1500 560",
  "M180 -40 C 160 120 320 180 300 320 S 160 520 260 660 S 420 860 380 900",
  "M1080 -40 C 1020 120 1180 220 1120 380 S 980 600 1100 720 S 1260 860 1240 900",
];

export function HeroContours({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 1440 800"
      preserveAspectRatio="xMidYMid slice"
      className={cn("pointer-events-none absolute inset-0 h-full w-full", className)}
    >
      <g fill="none" stroke="white" strokeOpacity="0.09" strokeWidth="1">
        {CONTOURS.map((d) =>
          Array.from({ length: 9 }, (_, i) => <path key={`${d}-${i}`} d={d} transform={`translate(${i * 2.5} ${i * 3})`} />),
        )}
      </g>
    </svg>
  );
}
