import Link from "next/link";
import type { CSSProperties } from "react";
import { AccountBelt } from "@/components/today/AccountBelt";
import { BoardCard } from "@/components/today/BoardCard";
import { FeedCard } from "@/components/today/FeedCard";
import {
  TODAY_IDLE_SHEETS,
  TODAY_RUNNING_SHEETS,
} from "@/lib/mock/today";
import { MorningBrief } from "./_components/MorningBrief";
import { PriorityQueue } from "./_components/PriorityQueue";

export const metadata = {
  title: "今日 · 乾策 Studio",
};

export default function TodayPage() {
  return (
    <div className="v-today">
      <MorningBrief />

      <div className="v-grid-3">
        {/* Task E · 消息 · 最要紧 feed-card */}
        <FeedCard />

        {/* A-017: agent · 正在跑 — card.warm.sheet-card (shell.html:2047-2131) */}
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

        {/* Task F · 任务 · 我的桌上 board-card (深色) */}
        <BoardCard />
      </div>

      {/* Task B · 今日客户队列 TOP 8 · stage × lastActivityAt */}
      <PriorityQueue />

      {/* Task K1 · 今日账册 belt (mockup L3114-3141 · 补漏) */}
      <AccountBelt />
    </div>
  );
}
