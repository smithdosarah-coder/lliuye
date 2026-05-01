"use client";

/**
 * MorningBrief · 今日看板顶部 hero（替代静态 Hero）
 *
 * 数据源：
 * - auth-store — 当前 persona（未登录 → 硬编 u_wangzhe 兜底，CLI-4 AuthGate 就绪后改 /login 跳转）
 * - customer-store — 今日有活动的客户（assignedTo / sharedWith 归属过滤）
 * - event-bus — 今日 alert 事件
 * - warroom ticket-store — F3 (Phase B-1) 已接：mine + 未完成（status != completed）票数
 *
 * 视觉 1:1 延续 mockup `.eyebrow` + `.hero-h1` glyph-rise + `.hero-meta--row`
 * 源: design_mockups/rm-assistant-final-2026-04-19.html L2791-2809
 *
 * 刷新：30s tick 重算"今天"滤条（跨午夜）+ 时钟 20s tick 走 mockup 节律。
 */

import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";

import {
  useAuthStore,
  useCustomerStore,
  useEventBus,
  type HandoffTicket,
} from "@/lib/store";
import { useTicketStore } from "@/app/warroom/_store/ticket-store";

import { StatCell } from "./StatCell";

const HERO_WORD = "今日看板";
const STAGGER_BASE = 0.8;
const STAGGER_STEP = 0.045;
const CLOCK_TICK_MS = 20_000;
const STATS_TICK_MS = 30_000;
const FALLBACK_USER = "u_wangzhe";

function greetingOf(d: Date): string {
  const h = d.getHours();
  if (h < 5) return "凌晨好";
  if (h < 12) return "早上好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
}

function formatEyebrowDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const wd = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"][d.getDay()];
  return `${y} · ${m} · ${day} · ${wd}`;
}

function formatLiveTime(d: Date): string {
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

function isSameDay(isoOrDate: string | Date, ref: Date): boolean {
  const d = typeof isoOrDate === "string" ? new Date(isoOrDate) : isoOrDate;
  return (
    d.getFullYear() === ref.getFullYear() &&
    d.getMonth() === ref.getMonth() &&
    d.getDate() === ref.getDate()
  );
}

export function MorningBrief() {
  const h1Ref = useRef<HTMLHeadingElement | null>(null);

  // ———— stores
  const currentUser = useAuthStore((s) => s.currentUser);
  const login = useAuthStore((s) => s.login);
  const customers = useCustomerStore((s) => s.customers);
  const history = useEventBus((s) => s.history);
  const tickets = useTicketStore((s) => s.tickets);

  // ———— client-only state (avoid SSR/hydration mismatch on persisted auth)
  const [mounted, setMounted] = useState(false);
  const [eyebrowDate, setEyebrowDate] = useState<string>("—");
  const [liveTime, setLiveTime] = useState<string>("--:--");
  const [greeting, setGreeting] = useState<string>("早上好");
  const [statsTick, setStatsTick] = useState(0);

  // mount flag
  useEffect(() => {
    setMounted(true);
  }, []);

  // W-D1F-A2 · 2026-04-28 · 移除 frontend fallback login(FALLBACK_USER)
  // 改由 AuthGate (`/api/auth/me`) + LoginForm 真接 backend 处理未登录态
  // (auth-protocol.md: cookie 是 source of truth · 前端不再自助硬编登录)

  // mockup staggerH1 — re-trigger glyph-rise
  useEffect(() => {
    const glyphs = h1Ref.current?.querySelectorAll<HTMLSpanElement>(".glyph");
    if (!glyphs) return;
    glyphs.forEach((g, i) => {
      g.style.animation = "none";
      void g.offsetWidth;
      g.style.animation = "";
      g.style.animationDelay = `${STAGGER_BASE + i * STAGGER_STEP}s`;
    });
  }, []);

  // mockup 20s 时钟 tick — eyebrow 日期 + LIVE 时间 + 问候语
  useEffect(() => {
    function clockTick() {
      const d = new Date();
      setEyebrowDate(formatEyebrowDate(d));
      setLiveTime(formatLiveTime(d));
      setGreeting(greetingOf(d));
    }
    clockTick();
    const id = setInterval(clockTick, CLOCK_TICK_MS);
    return () => clearInterval(id);
  }, []);

  // 30s stats tick — 把"今天"滤条刷到最新日期（跨午夜时 stats 会自动换档）
  useEffect(() => {
    const id = setInterval(() => setStatsTick((n) => n + 1), STATS_TICK_MS);
    return () => clearInterval(id);
  }, []);

  // ———— derived stats
  const stats = useMemo(() => {
    if (!mounted || !currentUser) {
      return { tickets: 0, alerts: 0, active: 0, hydrated: false };
    }
    const now = new Date();
    const mine = (cid: string, shared: readonly string[]) =>
      cid === currentUser.id || shared.includes(currentUser.id);

    const active = customers.filter(
      (c) =>
        mine(c.assignedTo, c.sharedWith) && isSameDay(c.lastActivityAt, now),
    ).length;

    const alerts = history.filter(
      (e) => e.agent === "alert" && isSameDay(e.createdAt, now),
    ).length;

    // F3 (V4 plan · Phase B-1) · 替 TICKET_FALLBACK_COUNT 真 ticket-store
    // mine = 我作为 assignedTo 或 requestedBy · 未完成 (status !== completed)
    const myOpenTickets = tickets.filter(
      (t: HandoffTicket) =>
        t.status !== "completed" &&
        (t.assignedTo === currentUser.id || t.requestedBy === currentUser.id),
    ).length;

    return {
      tickets: myOpenTickets,
      alerts,
      active,
      hydrated: true,
    };
    // statsTick forces recompute on 30s boundary for "today" rollover
  }, [mounted, currentUser, customers, history, tickets, statsTick]);

  const userName = mounted && currentUser ? currentUser.name : "王哲";

  return (
    <>
      <div className="eyebrow">
        <span>{eyebrowDate}</span>
        <span className="sep" />
        <em>
          {greeting}，{userName}。
        </em>
      </div>

      <h1 ref={h1Ref} className="hero-h1" id="h1Today">
        <span className="word" data-w={HERO_WORD} data-cjk="1">
          {[...HERO_WORD].map((ch, i) => (
            <span
              key={`${ch}-${i}`}
              className="glyph cn"
              style={
                {
                  animationDelay: `${STAGGER_BASE + i * STAGGER_STEP}s`,
                  "--i": i,
                } as CSSProperties
              }
            >
              {ch}
            </span>
          ))}
        </span>
      </h1>

      <div className="hero-meta hero-meta--row">
        <StatCell
          label="待办 · Tickets"
          value={
            stats.hydrated ? String(stats.tickets).padStart(2, "0") : "—"
          }
          unit="项"
          hint={
            stats.hydrated
              ? "warroom ticket-store · 我未完成 (assignee 或 requester)"
              : "数据加载中（fallback 标识）"
          }
        />
        <StatCell
          label="今日预警 · Alerts"
          value={String(stats.alerts).padStart(2, "0")}
          unit="条"
          hint="event-bus 订阅 · type=alert.*"
        />
        <StatCell
          label="活跃客户 · Active"
          value={String(stats.active).padStart(2, "0")}
          unit="户"
          hint="归属于你 · 今日有活动"
        />
        <span className="pill">
          <span className="livedot" />
          LIVE · {liveTime} <span className="cn">同步</span>
        </span>
      </div>
    </>
  );
}
