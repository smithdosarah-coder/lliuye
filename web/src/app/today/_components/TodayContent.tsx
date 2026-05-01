"use client";

import Link from "next/link";
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
 * 2026-04-27 · today 默认有数据 (user 反馈 "主页不要按钮" · revert empty CTA)
 * 双模式 (空白 + 触发后填数据) = Agent Workspace 层职责 ·
 * today 是 KPI 汇总入口 · 不需要 demo 触发逻辑。
 */
export function TodayContent() {
  return (
    <div className="v-today">
      <MorningBrief />

      <div className="v-grid-3">
        <FeedCard />

        <Link
          href="/archive"
          className="card warm sheet-card"
          data-go="archive"
          data-testid="today-assistant-card"
        >
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
            <span className="tail">AI 助手 ↘</span>
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
