"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { HeaderSlotProvider, useHeaderSlot } from "@/lib/header-slot";

type Props = {
  code: string;
  eyebrowLabel: string;
  title: string;
  description: string;
  children: ReactNode;
};

function ArchiveHeader({ code, eyebrowLabel, title, description }: Omit<Props, "children">) {
  const slot = useHeaderSlot();
  const lede = slot?.description ?? description;
  return (
    <>
      <div
        className="eyebrow"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          fontFamily: "var(--mono)",
          fontSize: 11,
          letterSpacing: ".16em",
          textTransform: "uppercase",
          color: "var(--ink-65)",
          marginTop: 10,
        }}
      >
        <span style={{ width: 32, height: 1, background: "var(--ink-28)" }} />
        {code} · {eyebrowLabel}
        <Link
          href="/archive"
          style={{ marginLeft: "auto", color: "var(--accent)", textDecoration: "none" }}
        >
          ← 返回助手目录
        </Link>
      </div>
      <h1 className="archive-h" style={{ marginTop: 12 }}>
        <span style={{ fontFamily: "var(--cjk)", fontWeight: 700 }}>{title}</span>
      </h1>
      <p className="archive-lede">{lede}</p>
    </>
  );
}

export function ArchiveAgentShell({ children, ...header }: Props) {
  return (
    <HeaderSlotProvider>
      <ArchiveHeader {...header} />
      <div style={{ marginTop: 24 }}>{children}</div>
    </HeaderSlotProvider>
  );
}
