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
import { useAuthStore } from "@/lib/store";
import type { Role } from "@/lib/store/types";
import { EventTimeline } from "./EventTimeline";
import { MorningBrief } from "./MorningBrief";
import { PriorityQueue } from "./PriorityQueue";

/**
 * TodayContent — 5 role home view differentiation (Phase B Sprint 3 sub-PR 2 · 2026-05-05).
 *
 * per Q-052 active rule #1 (4+1 角色定位工作台) + #4 (Q-047 仅冻审美装饰 · 不冻 F5/F7/F8/F9/F10/F15 工作台逻辑层):
 *   - RM (王哲)              · F5 客户上下文常驻 + F7 Today 单链路 + F10 Action Card
 *   - credit_officer (李华)  · F8 handoff 任务卡 (channel→report→credit) + 待审报告
 *   - compliance_officer (周敏) · F8 handoff (alert→compliance) + 政策预警
 *   - risk_manager (陈凯)    · F9 segment-aware 预警榜 + DSL 部署
 *   - admin (刘野)           · 全 KPI 概览 (现有 layout)
 *
 * 视觉装饰 (F1-F4 / F11-F14 / F16-F17) 不动 · 仅复用现有 .card / .warm / sheet-card style ·
 * 不引入新 CSS · 不破现 mockup 1:1 复刻 (per platform-shell-v2 §视觉约束).
 */
export function TodayContent() {
  const role: Role = useAuthStore((s) => s.currentUser?.role) ?? "rm";
  const userName = useAuthStore((s) => s.currentUser?.name) ?? "";

  switch (role) {
    case "credit_officer":
      return <CreditOfficerHome name={userName} />;
    case "compliance_officer":
      return <ComplianceOfficerHome name={userName} />;
    case "risk_manager":
      return <RiskManagerHome name={userName} />;
    case "admin":
      return <AdminHome />;
    case "rm":
    default:
      return <RmHome name={userName} />;
  }
}

// ---------------------------------------------------------------------------
// shared sheet-card (现有视觉 · 不动 .card .warm .sheet-card style)
// ---------------------------------------------------------------------------

function RunningSheetsCard() {
  return (
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
  );
}

/**
 * Role-aware intro card (F8 handoff 任务卡 + F10 Action Card frame · per Q-052 #1).
 * 复用 .card .warm style · 不引入新 CSS.
 */
function RoleIntroCard({
  role,
  name,
  agentSlug,
  badge,
  tag,
  title,
  subtitle,
  hint,
}: {
  role: Role;
  name: string;
  agentSlug: string;
  badge: string;
  tag: string;
  title: string;
  subtitle: string;
  hint: string;
}) {
  return (
    <Link href={`/archive/${agentSlug}`} className="card warm sheet-card" data-role={role}>
      <div className="tag">
        <span className="dash" />
        <span className="label">{tag}</span>
        {name ? <span className="sum">{name}</span> : null}
      </div>
      <h3>
        <span className="nbr">{badge}</span>
        <em>today.</em>
      </h3>
      <div className="sheet-title">{title}</div>
      <div className="sheet-sub">
        <span>{subtitle}</span>
      </div>
      <div className="pv-foot sheet-foot">
        <span className="cnt">{hint}</span>
        <span className="tail">进入 ↘</span>
      </div>
      <div className="badge">01.</div>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// 5 role home view (data-role="<role>" · 后续 Playwright smoke + RBAC e2e 锚)
// ---------------------------------------------------------------------------

function RmHome({ name }: { name: string }) {
  // F5 客户上下文常驻 + F7 Today 单链路 + F10 Action Card + F15 Live evidence
  return (
    <div className="v-today" data-role="rm">
      <MorningBrief />

      <div className="v-grid-3">
        <RoleIntroCard
          role="rm"
          name={name}
          agentSlug="channel"
          badge="01"
          tag="客户经理 · 拓客 → 尽调"
          title="今日待跟进客户"
          subtitle="拓客信号 + 在途报告 · F5 客户上下文常驻"
          hint="主调 channel + report · 看 credit / alert"
        />
        <RunningSheetsCard />
        <BoardCard />
      </div>

      {/* F5 客户上下文常驻 (top of priority area) */}
      <AccountBelt />
      {/* F7 Today 单链路 · F10 Action Card (FeedCard) */}
      <PriorityQueue />
      <FeedCard />
      {/* F15 Live evidence */}
      <EventTimeline />
    </div>
  );
}

function CreditOfficerHome({ name }: { name: string }) {
  // F8 handoff 任务卡 (channel→report→credit) + 待审报告
  return (
    <div className="v-today" data-role="credit_officer">
      <MorningBrief />

      <div className="v-grid-3">
        <RoleIntroCard
          role="credit_officer"
          name={name}
          agentSlug="credit"
          badge="01"
          tag="审贷员 · 待审报告"
          title="今日待审授信申请"
          subtitle="F8 上游 handoff (RM → credit) · 红线命中优先"
          hint="主调 credit · 可 approve · 看 report / alert read-only"
        />
        <RunningSheetsCard />
        <BoardCard />
      </div>

      <PriorityQueue />
      <FeedCard />
      <EventTimeline />
    </div>
  );
}

function ComplianceOfficerHome({ name }: { name: string }) {
  // F8 handoff (alert→compliance) + 政策预警
  return (
    <div className="v-today" data-role="compliance_officer">
      <MorningBrief />

      <div className="v-grid-3">
        <RoleIntroCard
          role="compliance_officer"
          name={name}
          agentSlug="compliance"
          badge="01"
          tag="合规官 · 政策事件触发"
          title="新政策 / 违规冲突点"
          subtitle="F8 上游 handoff (alert → compliance) · 改/补/强分类"
          hint="主调 compliance · 可 approve · 看 report / alert read-only"
        />
        <RunningSheetsCard />
        <BoardCard />
      </div>

      <PriorityQueue />
      <FeedCard />
      <EventTimeline />
    </div>
  );
}

function RiskManagerHome({ name }: { name: string }) {
  // F9 segment-aware 预警榜 + DSL 部署
  return (
    <div className="v-today" data-role="risk_manager">
      <MorningBrief />

      <div className="v-grid-3">
        <RoleIntroCard
          role="risk_manager"
          name={name}
          agentSlug="alert"
          badge="01"
          tag="风险经理 · 预警 + DSL"
          title="今日红色预警 · DSL 部署"
          subtitle="F9 segment-aware (在贷池) · alert 双路交叉命中"
          hint="主调 riskctrl + alert · 可 approve · 看 credit read-only"
        />
        <RunningSheetsCard />
        <BoardCard />
      </div>

      <PriorityQueue />
      <FeedCard />
      <EventTimeline />
    </div>
  );
}

function AdminHome() {
  // 全 KPI 概览 · 现有 layout (admin 看全 6 agent)
  return (
    <div className="v-today" data-role="admin">
      <MorningBrief />

      <div className="v-grid-3">
        <FeedCard />
        <RunningSheetsCard />
        <BoardCard />
      </div>

      <PriorityQueue />
      <AccountBelt />
      <EventTimeline />
    </div>
  );
}
