import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatWan(yuan: number | null | undefined): string {
  if (yuan === null || yuan === undefined || Number.isNaN(yuan)) return "—";
  if (Math.abs(yuan) >= 1e8) return `${(yuan / 1e8).toFixed(2)} 亿`;
  if (Math.abs(yuan) >= 1e4) return `${(yuan / 1e4).toFixed(1)} 万`;
  return yuan.toLocaleString("zh-CN");
}
