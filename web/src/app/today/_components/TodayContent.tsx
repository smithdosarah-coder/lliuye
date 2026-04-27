"use client";

import Link from "next/link";
import { useState } from "react";
import type { CSSProperties } from "react";
import { AccountBelt } from "@/components/today/AccountBelt";
import { BoardCard } from "@/components/today/BoardCard";
import { FeedCard } from "@/components/today/FeedCard";
import {
  TODAY_IDLE_SHEETS,
  TODAY_RUNNING_SHEETS,
} from "@/lib/mock/today";
import { EventTimeline } from "./EventTimeline";
import { MorningBrief } from "./MorningBrief";
import { PriorityQueue } from "./PriorityQueue";

/**
 * F-007 · 2026-04-27 · today 空白状态 + 「开始演示」CTA
 *
 * 默认 started=false · 仅渲染 MorningBrief + 居中 CTA card · 防演示穿帮
 * (前 commit e0b2563 完全删 4 块 user 反对 · 改路径 = 保留 4 块 + 默认隐藏)
 *
 * click 「开始演示」 → setStarted(true) · 渲染原 v-grid-3 + PriorityQueue
 * + AccountBelt + EventTimeline 全套数据。
 */
export function TodayContent() {
  const [started, setStarted] = useState(false);

  if (!started) {
    return (
      <div className="v-today v-today--empty">
        <MorningBrief />
        <section
          aria-label="演示触发"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "55vh",
            padding: "40px 20px",
          }}
        >
          <div
            style={{
              maxWidth: 520,
              textAlign: "center",
              background:
                "color-mix(in srgb, var(--chalk) 72%, transparent)",
              backdropFilter: "blur(12px) saturate(1.1)",
              WebkitBackdropFilter: "blur(12px) saturate(1.1)",
              border: "1px solid var(--ink-08)",
              borderRadius: "var(--r-lg)",
              padding: "44px 36px",
              boxShadow:
                "0 12px 40px -16px rgba(0,0,0,.18), inset 0 1px 0 color-mix(in srgb, var(--chalk) 50%, transparent)",
            }}
          >
            <div
              style={{
                fontFamily: "var(--mono)",
                fontSize: 11,
                letterSpacing: "0.18em",
                textTransform: "uppercase",
                color: "var(--accent)",
                marginBottom: 14,
              }}
            >
              今日 · 空白
            </div>
            <h2
              style={{
                fontFamily: "var(--display)",
                fontWeight: 600,
                fontSize: 26,
                lineHeight: 1.4,
                color: "var(--ink)",
                margin: "0 0 30px 0",
              }}
            >
              点{" "}
              <em
                style={{
                  fontFamily: "var(--italic)",
                  fontStyle: "italic",
                  color: "var(--accent)",
                }}
              >
                开始演示
              </em>{" "}
              装载今日工作
              <br />
              <span
                style={{
                  fontFamily: "var(--cjk)",
                  fontSize: 15,
                  color: "var(--ink-65)",
                  fontWeight: 400,
                }}
              >
                客户队列 · 事件流 · 账册 KPI · 报告
              </span>
            </h2>
            <button
              type="button"
              data-testid="today-start-cta"
              onClick={() => setStarted(true)}
              style={{
                all: "unset",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 10,
                padding: "14px 36px",
                borderRadius: 999,
                background:
                  "linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 65%, var(--ink)))",
                color: "var(--chalk)",
                fontFamily: "var(--cjk)",
                fontSize: 14,
                fontWeight: 600,
                letterSpacing: ".08em",
                boxShadow:
                  "0 8px 22px -10px color-mix(in srgb, var(--accent) 60%, transparent)",
                transition: "transform .18s, box-shadow .25s",
              }}
              onMouseDown={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-1px)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)";
              }}
            >
              <span>开始演示</span>
              <span
                style={{
                  fontFamily: "var(--mono)",
                  fontSize: 16,
                  lineHeight: 1,
                }}
                aria-hidden
              >
                ⏵
              </span>
            </button>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="v-today">
      <MorningBrief />

      <div className="v-grid-3">
        <FeedCard />

        <Link href="/dispatch" className="card warm sheet-card">
          <div className="tag">
            <span className="dash" />
            <span className="label">agent · 正在跑</span>
            <span className="sum">
              共 {String(TODAY_RUNNING_SHEETS.length + TODAY_IDLE_SHEETS.length).padStart(2, "0")} 位
            </span>
          </div>
          <h3>
            <span className="nbr">{String(TODAY_RUNNING_SHEETS.length).padStart(2, "0")}</span>
            <em>running.</em>
          </h3>
          <div className="pv-sheets">
            {TODAY_RUNNING_SHEETS.map((s) => (
              <div
                className="sheet running"
                key={s.id}
                style={{ "--p": `${s.pct}%` } as CSSProperties}
              >
                <div className="sheet-top">
                  <span className="sheet-tag">{s.tag}</span>
                  <span className="sheet-state">{s.state}</span>
                </div>
                <div className="sheet-title">{s.title}</div>
                <div className="sheet-sub">
                  <span>{s.sub}</span>
                  <span className="eta">{s.eta}</span>
                </div>
                <div className="sheet-bar" />
              </div>
            ))}
            {TODAY_IDLE_SHEETS.map((s) => (
              <div className="sheet idle" key={s.id}>
                <div className="sheet-top">
                  <span className="sheet-tag">{s.tag}</span>
                  <span className="sheet-state">idle</span>
                </div>
                <div className="sheet-title">{s.title}</div>
                <div className="sheet-sub">
                  <span>{s.sub}</span>
                  <span className="eta">—</span>
                </div>
              </div>
            ))}
          </div>
          <div className="pv-foot sheet-foot">
            <span className="cnt">
              运行中 <b>{String(TODAY_RUNNING_SHEETS.length).padStart(2, "0")}</b> · 空闲{" "}
              <b>{String(TODAY_IDLE_SHEETS.length).padStart(2, "0")}</b>
            </span>
            <span className="tail">调度台 ↘</span>
          </div>
          <div className="badge">02.</div>
        </Link>

        <BoardCard />
      </div>

      <PriorityQueue />
      <AccountBelt />
      <EventTimeline />
    </div>
  );
}
