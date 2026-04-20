"use client";

import { useMemo } from "react";
import { useEventBus } from "@/lib/store";
import { byUserId } from "@/lib/store";
import type { AgentEvent, AgentEventType } from "@/lib/store/types";

const TYPE_LABEL: Record<AgentEventType, string> = {
  "report.completed": "报告完成",
  "report.drafted": "草稿保存",
  "credit.decided": "授信决定",
  "credit.redline_hit": "红线命中",
  "channel.lookalike_picked": "Look-alike 选中",
  "alert.raised": "预警触发",
  "alert.handled": "预警处置",
  "compli.conflict_found": "合规冲突",
  "riskctrl.dsl_deployed": "规则上线",
  "handoff.requested": "发起交接",
  "handoff.accepted": "接收交接",
  "comment.added": "留言",
};

function payloadLine(e: AgentEvent): string {
  const entries = Object.entries(e.payload);
  if (entries.length === 0) return "";
  return entries
    .slice(0, 2)
    .map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : v}`)
    .join(" · ");
}

function fmtFull(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ActivityTimeline({ customerId }: { customerId: string }) {
  const history = useEventBus((s) => s.history);
  const events = useMemo(
    () => history.filter((e) => e.customerId === customerId).slice(0, 20),
    [history, customerId],
  );

  return (
    <section className="v-customer-timeline">
      <div className="sec-head">
        <span className="sep" />
        <em>时间线</em>
        <span className="cnt">{events.length} 条</span>
      </div>
      {events.length === 0 ? (
        <div className="tl-empty">
          该客户暂无事件。Agent workspace 完成关键步骤后会在此展示。
        </div>
      ) : (
        <ol className="tl-list">
          {events.map((e) => {
            const actor = byUserId(e.actor);
            return (
              <li key={e.id} className="tl-row" data-agent={e.agent}>
                <span className="tl-dot" />
                <div className="tl-main">
                  <div className="tl-head">
                    <span className="tl-kind">{TYPE_LABEL[e.type]}</span>
                    <span className="tl-agent">@{e.agent}</span>
                    <span className="tl-ts">{fmtFull(e.createdAt)}</span>
                  </div>
                  <div className="tl-body">
                    <span className="tl-actor">{actor?.name ?? e.actor}</span>
                    {payloadLine(e) && (
                      <span className="tl-payload">{payloadLine(e)}</span>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
