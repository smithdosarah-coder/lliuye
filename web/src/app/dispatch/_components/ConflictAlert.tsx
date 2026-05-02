"use client";

/**
 * F11 (V4 plan · Phase B · Sprint 2 spike) · 冲突显性化 banner
 *
 * Agent3 (授信) + Agent5 (合规) 对同一客户决议不一致时 · /dispatch 顶部
 * 显式 ⚠️ + 列冲突点 + 推荐 owner + 跳 /warroom 链接。
 *
 * 范围 (per V4 plan F11 R3 ratify):
 * - spike (0.3 周) · 视觉显性化 · 不做完整仲裁引擎
 * - mock fixture 消费 (web/src/lib/mock/conflicts.ts) · Phase C1 接 /api/conflicts
 * - 跳 /warroom?customer=<id> · 复用 F5 CustomerContextGateway 路径
 *
 * 设计:
 * - 严重度 red (阻断) → 红色 banner · severity yellow (提醒) → 琥珀色
 * - 多冲突时 stack 显示 · 用户逐个 dismiss 不可 (Phase C1 真做 ack)
 * - 0 冲突时不渲染 (无 visual 占位)
 */

import Link from "next/link";

import { useCustomerStore } from "@/lib/store";
import { MOCK_CONFLICTS, type Conflict } from "@/lib/mock/conflicts";

const AGENT_CN: Record<string, string> = {
  credit: "授信",
  compliance: "合规",
  alert: "预警",
  channel: "获客",
  riskctrl: "风控",
  report: "报告",
};

function formatSources(sources: Conflict["sources"]): string {
  return sources.map((s) => AGENT_CN[s] ?? s).join(" × ");
}

export function ConflictAlert() {
  const customers = useCustomerStore((s) => s.customers);

  if (MOCK_CONFLICTS.length === 0) return null;

  return (
    <div className="conflict-alerts" data-testid="dispatch-conflict-alerts">
      {MOCK_CONFLICTS.map((c) => {
        const customer = customers.find((x) => x.id === c.customerId);
        const customerName = customer?.shortName ?? customer?.name ?? c.customerId;
        const warroomHref = `/warroom?customer=${encodeURIComponent(c.customerId)}`;
        return (
          <div
            key={c.id}
            className={`conflict-alert conflict-alert--${c.severity}`}
            role="alert"
            data-conflict-id={c.id}
          >
            <span className="conflict-icon" aria-hidden>
              ⚠
            </span>
            <div className="conflict-body">
              <div className="conflict-head">
                <strong className="conflict-customer">{customerName}</strong>
                <span className="conflict-sources">
                  {formatSources(c.sources)} 决议冲突
                </span>
              </div>
              <p className="conflict-summary">{c.summary}</p>
            </div>
            <Link href={warroomHref} className="conflict-jump">
              进 Warroom 处置 →
            </Link>
          </div>
        );
      })}
    </div>
  );
}
