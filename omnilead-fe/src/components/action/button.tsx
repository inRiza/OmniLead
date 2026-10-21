import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

const shared =
  "inline-flex cursor-pointer items-center justify-center border px-3.5 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40";

type Style = "primary" | "secondary" | "ghost" | "muted";

const styleClass: Record<Style, string> = {
  primary:
    "rounded-xl border-rc-fg bg-rc-fg text-rc-primary-fg hover:bg-rc-fg/90",
  muted:
    "rounded-md border-rc-border bg-rc-surface-hover text-rc-fg hover:bg-rc-border/40",
  secondary:
    "rounded-md border-rc-border bg-rc-surface text-rc-fg hover:bg-rc-surface-hover",
  ghost:
    "rounded-md border-transparent text-rc-fg-muted hover:bg-rc-surface-hover hover:text-rc-fg",
};

type NavProps = {
  purpose: "nav";
  href: string;
  style?: Style;
  className?: string;
  children: ReactNode;
};

type ActionProps = {
  purpose: "action";
  style?: Style;
  className?: string;
  children: ReactNode;
} & ButtonHTMLAttributes<HTMLButtonElement>;

export function Button(props: NavProps | ActionProps) {
  const style = props.style ?? "secondary";
  const className = cn(shared, styleClass[style], props.className);

  if (props.purpose === "nav") {
    return (
      <Link href={props.href} className={className}>
        {props.children}
      </Link>
    );
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { purpose: _, style: __, className: ___, children, ...rest } = props;
  return (
    <button type="button" className={className} {...rest}>
      {children}
    </button>
  );
}
