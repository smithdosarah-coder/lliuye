"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

type Row = {
  ic: string;
  icClass?: "dot-p0" | "dot-warn" | "dot-live" | "dot-chat";
  nm: string;
  sub: string;
  ts: string;
  href: string;
};

type Section = {
  title: string;
  meta: string;
  rows: Row[];
  more?: { label: string; count?: string };
};

const SECTIONS: Section[] = [
  {
    title: "我的客户",
    meta: "BOOK · 03",
    rows: [
      { ic: "P0", icClass: "dot-p0",   nm: "宁海汇通科技",   sub: "授信案 · 待终审",       ts: "08:41", href: "/today" },
      { ic: "B",                        nm: "海创智能装备",   sub: "预审 · 材料 7/9",       ts: "昨日",  href: "/today" },
      { ic: "△", icClass: "dot-warn",  nm: "星河医药",       sub: "预警 · 黄色",           ts: "04/15", href: "/warroom" },
    ],
    more: { label: "查看全部客户", count: "(28)" },
  },
  {
    title: "进行中",
    meta: "IN FLIGHT · 04",
    rows: [
      { ic: "报", icClass: "dot-live", nm: "报告助手 · 宁海汇通", sub: "生成中 · 78% · ETA 09:12", ts: "活",    href: "/archive/report" },
      { ic: "预", icClass: "dot-live", nm: "预警助手 · 星河医药", sub: "运行 2:34 · 42%",          ts: "活",    href: "/archive/alert" },
      { ic: "急", icClass: "dot-p0",   nm: "合规助手 · §214 筛查", sub: "4 户命中 · 意见待出",      ts: "12:00", href: "/warroom" },
      { ic: "风",                       nm: "风控助手 · 小微 DSL",   sub: "等样本投入",               ts: "—",     href: "/archive/riskctrl" },
    ],
  },
  {
    title: "最近",
    meta: "RECENT",
    rows: [
      { ic: "@", icClass: "dot-chat", nm: "@林楠 · 审贷员",     sub: "下周一前给额度建议",  ts: "2h",    href: "/dispatch" },
      { ic: "#", icClass: "dot-chat", nm: "#华东线晨会",         sub: "5 位参会 · 09:30",     ts: "07:50", href: "/dispatch" },
      { ic: "§",                       nm: "NMPA §214 政策",      sub: "四月新政 · 已解析",   ts: "04/12", href: "/archive/compliance" },
    ],
  },
];

const QUICK_CREATE = [
  { label: "新对话",     href: "/dispatch" },
  { label: "新任务",     href: "/warroom" },
  { label: "起草报告",   href: "/archive/report" },
  { label: "开始获客",   href: "/archive/channel" },
];

export function Desk() {
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (pinned) return;
      if (e.clientX < 22) {
        if (closeTimer.current) clearTimeout(closeTimer.current);
        setOpen(true);
      } else if (open && e.clientX > 360) {
        if (closeTimer.current) clearTimeout(closeTimer.current);
        closeTimer.current = setTimeout(() => setOpen(false), 180);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        setPinned(false);
      }
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("keydown", onKey);
      if (closeTimer.current) clearTimeout(closeTimer.current);
    };
  }, [open, pinned]);

  function togglePin() {
    setPinned((p) => !p);
    setOpen(true);
  }

  const cls = ["drawer", open ? "open" : "", pinned ? "pin" : ""].filter(Boolean).join(" ");

  return (
    <aside className={cls} aria-label="工作台 Desk">
      <div className="dr-hint" />
      <div className="dr-panel" role="region">
        <div className="dr-head">
          <span className="t">
            <span className="cn">工作台</span>
            <em>Desk.</em>
          </span>
          <button className="dr-pin" onClick={togglePin} title={pinned ? "解钉" : "钉住"} aria-pressed={pinned}>
            ◆
          </button>
        </div>

        <div className="dr-search">
          <input placeholder="搜客户 / 卷宗 / 政策 / 对话" />
          <kbd>⌘K</kbd>
        </div>

        {SECTIONS.map((sec) => (
          <div className="dr-sec" key={sec.title}>
            <div className="hd">
              <span>{sec.title}</span>
              <em>{sec.meta}</em>
            </div>
            {sec.rows.map((r) => (
              <Link key={`${sec.title}-${r.nm}`} href={r.href} className="dr-row">
                <span className={`ic${r.icClass ? ` ${r.icClass}` : ""}`}>{r.ic}</span>
                <span className="nm-wrap">
                  <span className="nm">{r.nm}</span>
                  <span className="sub">{r.sub}</span>
                </span>
                <span className="ts">{r.ts}</span>
              </Link>
            ))}
            {sec.more && (
              <span className="dr-more">
                {sec.more.label} {sec.more.count && <span className="a">{sec.more.count}</span>} <span className="a">↘</span>
              </span>
            )}
          </div>
        ))}

        <div className="dr-sec">
          <div className="hd">
            <span>新建</span>
            <em>CREATE</em>
          </div>
          <div className="dr-qc">
            {QUICK_CREATE.map((q) => (
              <Link key={q.label} href={q.href}>
                <button type="button">
                  <span className="plus">+</span>
                  {q.label}
                </button>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
