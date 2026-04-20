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
      <div className="eyebrow">
        <span className="sep" />
        {code} · <em>{eyebrowLabel}</em>
        <Link
          href="/archive"
          style={{ marginLeft: "auto", color: "var(--accent)", textDecoration: "none" }}
        >
          ← 返回助手目录
        </Link>
      </div>
      <h1 className="hero-h1">
        <span className="cn" style={{ fontFamily: "var(--cjkserif)", fontWeight: 700 }}>
          {title}
        </span>
      </h1>
      <p className="lede">{lede}</p>
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
