import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function insidePopover(target: EventTarget | null) {
  return target instanceof Element && target.closest("[data-rc-popover]") !== null;
}
