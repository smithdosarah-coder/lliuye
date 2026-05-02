/**
 * F11 (V4 plan · Phase B · Sprint 2 spike) · 冲突显性化 mock 数据
 *
 * 来源: V4 plan F11 (Codex R2 v2 降级 + 主 CLI R3 接受 + Gemini 视觉提示)
 * 范围: B-3 spike 仅 mock 视觉提示 · 不做完整仲裁引擎 (推 Phase C1 audit 账本接
 *      /api/audit + 审贷官一键裁决) · 详 V4 plan §1 Phase C1。
 *
 * 形态: 单条冲突 = Agent3 (授信) 与 Agent5 (合规) 对同一客户决议不一致 ·
 *      冲突来源 (sources · agent ids) + 影响客户 + 推荐 owner + 跳 warroom 链接。
 *
 * 实装路径: Phase C1 后端 ledger 接通后 · 此 mock 替成 /api/conflicts API
 * (本 PR 仅前端视觉) · ConflictAlert 组件消费 selector · 不依赖 mock 路径。
 */

import type { AgentId } from "@/lib/store";

export interface Conflict {
  id: string;
  /** 客户 id (per customer-store) */
  customerId: string;
  /** 冲突来源 agent (≥ 2 · 通常 Agent3 + Agent5) */
  sources: AgentId[];
  /** 冲突简述 (≤ 80 字 · 中文术语) */
  summary: string;
  /** 推荐 owner (per auth-store DEMO_USERS · 通常是审贷官 / 合规官) */
  recommendOwnerId: string;
  /** ISO 时间 · 最近触发 */
  createdAt: string;
  /** 严重度 · 红 = 阻断 · 黄 = 提醒 (类 alert tier 视觉) */
  severity: "red" | "yellow";
}

/** Sprint 2 spike mock · Phase C1 后端 ready 替 /api/conflicts · 当前 fixture 演示 */
export const MOCK_CONFLICTS: Conflict[] = [
  {
    id: "conflict_yunrong_001",
    customerId: "cust_yunrong",
    sources: ["credit", "compliance"],
    summary: "授信通过(¥2,000 万) 与 合规扫描黄档冲突 · 政策升级未达准入",
    recommendOwnerId: "u_zhoumin", // 合规官
    createdAt: "2026-05-02T08:30:00+08:00",
    severity: "red",
  },
  {
    id: "conflict_tongxin_002",
    customerId: "cust_tongxin",
    sources: ["credit", "compliance"],
    summary: "续贷决议 与 合规复核未结案 · 建议先关合规再放款",
    recommendOwnerId: "u_lihua", // 审贷官
    createdAt: "2026-05-02T07:15:00+08:00",
    severity: "yellow",
  },
];
