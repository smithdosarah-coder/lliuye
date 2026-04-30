"use client";

import Link from "next/link";
import { useMemo } from "react";
import { AGENTS, type AgentKey } from "@/lib/agents";
import { useEventBus } from "@/lib/store";
import type { AgentEvent, AgentId } from "@/lib/store/types";

/**
 * agents.ts (AgentKey) 与 store/types.ts (AgentId) 现完全同值
 * (per Q-042.B PM 拍板 2026-04-29 · agent5 单 id = compliance 全栈)。
 * 本映射保留为 identity · 不再有命名漂移。
 */
const TO_STORE_ID: Record<AgentKey, AgentId> = {
  report: "report",
  credit: "credit",
  channel: "channel",
  alert: "alert",
  compliance: "compliance",
  riskctrl: "riskctrl",
};

const TONE: Record<AgentKey, string> = {
  report: "var(--t-report)",
  channel: "var(--t-channel)",
  credit: "var(--t-credit)",
  riskctrl: "var(--t-riskctrl)",
  alert: "var(--t-alert)",
  compliance: "var(--t-compli)",
};

function summarize(e: AgentEvent): string {
  switch (e.type) {
    case "report.completed":
      return "报告已完成 · QC 通过";
    case "report.drafted":
      return `草稿保存 · ${(e.payload.section as string) ?? "—"}`;
    case "credit.decided":
      return `授信决定 · ${(e.payload.outcome as string) ?? "—"}`;
    case "credit.redline_hit":
      return `红线命中 · ${(e.payload.rule as string) ?? "—"}`;
    case "channel.lookalike_picked":
      return `Look-alike 选中 · ${(e.payload.fromPool as string) ?? "—"}`;
    case "alert.raised":
      return `预警 · ${(e.payload.level as string) ?? "—"}`;
    case "alert.handled":
      return "预警已处置";
    case "compliance.conflict_found":
      return `合规冲突 · ${(e.payload.policy as string) ?? "—"}`;
    case "riskctrl.dsl_deployed":
      return "规则上线";
    default:
      return e.type;
  }
}

function fmtTime(iso: string): string {
  const d = new Date(iso);
  const now = Date.now();
  const diff = (now - d.getTime()) / 1000;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return `${Math.floor(diff / 60)} 分前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  return d.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

export function AgentTileStrip({ customerId }: { customerId: string }) {
  const history = useEventBus((s) => s.history);

  const latestByAgent = useMemo(() => {
    const map: Partial<Record<AgentId, AgentEvent>> = {};
    for (const e of history) {
      if (e.customerId !== customerId) continue;
      if (!map[e.agent]) map[e.agent] = e;
    }
    return map;
  }, [history, customerId]);

  return (
    <section className="v-customer-agents">
      <div className="sec-head">
        <span className="sep" />
        <em>Agent 产出</em>
      </div>
      <div className="tile-grid">
        {AGENTS.map((a) => {
          const storeId = TO_STORE_ID[a.key];
          const latest = latestByAgent[storeId];
          const href = `${a.path}?customer=${customerId}`;
          const cls = `ag-tile ${latest ? "has" : "empty"}`;
          return (
            <Link
              key={a.key}
              href={href}
              className={cls}
              style={{ "--tone": TONE[a.key] } as React.CSSProperties}
            >
              <div className="tile-head">
                <span className="code">{a.code}</span>
                <span className="ttl">{a.title}</span>
              </div>
              <div className="tile-body">
                {latest ? (
                  <>
                    <span className="sum">{summarize(latest)}</span>
                    <span className="ts">{fmtTime(latest.createdAt)}</span>
                  </>
                ) : (
                  <span className="none">暂无产出</span>
                )}
              </div>
              <span className="tail">进入工作区 ↘</span>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
