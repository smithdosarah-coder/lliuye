"use client";

import Link from "next/link";
import type { MouseEvent } from "react";
import type { Customer, CustomerStage } from "@/lib/store/types";
import { useDeskStore } from "./_desk-store";

const STAGE_SHORT: Record<CustomerStage, string> = {
  lead: "线索",
  intake: "材料",
  report: "报告",
  credit: "授信",
  monitoring: "监控",
  alert: "预警",
  closed: "结清",
};

const STAGE_TONE: Record<CustomerStage, string> = {
  lead: "var(--t-channel)",
  intake: "var(--ink-48)",
  report: "var(--t-report)",
  credit: "var(--t-credit)",
  monitoring: "var(--t-compli)",
  alert: "var(--t-alert)",
  closed: "var(--ink-28)",
};

function fmtTs(iso: string): string {
  const d = new Date(iso);
  const now = Date.now();
  const diff = (now - d.getTime()) / 1000;
  if (diff < 3600) return `${Math.max(1, Math.floor(diff / 60))}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  if (diff < 7 * 86400) return `${Math.floor(diff / 86400)}d`;
  return d.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

export function DeskCustomerRow({ customer }: { customer: Customer }) {
  const pinned = useDeskStore((s) => s.pinned.includes(customer.id));
  const togglePin = useDeskStore((s) => s.togglePin);

  const href = `/customer/${customer.id}`;
  const display = customer.shortName ?? customer.name;
  const sub = [
    customer.industry,
    customer.amount !== undefined ? `${customer.amount.toLocaleString()}万` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  function onPinClick(e: MouseEvent<HTMLButtonElement>) {
    e.preventDefault();
    e.stopPropagation();
    togglePin(customer.id);
  }

  return (
    <Link
      href={href}
      className="dr-row dr-row-customer"
      draggable
      data-pinned={pinned || undefined}
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "copy";
        e.dataTransfer.setData(
          "application/x-desk-row",
          JSON.stringify({ name: display, href }),
        );
        e.dataTransfer.setData("text/plain", display);
      }}
    >
      <span
        className="ic stage-ic"
        style={{ "--tone": STAGE_TONE[customer.stage] } as React.CSSProperties}
        title={STAGE_SHORT[customer.stage]}
      >
        {STAGE_SHORT[customer.stage][0]}
      </span>
      <span className="nm-wrap">
        <span className="nm">{display}</span>
        <span className="sub">{sub || customer.region || "—"}</span>
      </span>
      <button
        type="button"
        className="dr-row-pin"
        onClick={onPinClick}
        aria-pressed={pinned}
        title={pinned ? "取消置顶" : "置顶"}
      >
        {pinned ? "◆" : "◇"}
      </button>
      <span className="ts">{fmtTs(customer.lastActivityAt)}</span>
    </Link>
  );
}
