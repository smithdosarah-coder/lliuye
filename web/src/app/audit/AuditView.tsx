"use client";

import { useEffect, useMemo, useState } from "react";
import { NoPermission } from "@/components/shell/NoPermission";
import { AGENTS, type AgentKey } from "@/lib/agents";
import { byUserId, publishEvent, useAuthStore, useCustomerStore, useEventBus } from "@/lib/store";
import type { AgentEvent, AgentId } from "@/lib/store/types";

const AGENT_LABEL: Record<AgentId, string> = {
  report: "报告",
  credit: "授信",
  channel: "获客",
  alert: "预警",
  compliance: "合规",
  riskctrl: "风控",
};

const EVENT_LABEL: Record<AgentEvent["type"], string> = {
  "report.completed": "报告完成",
  "report.drafted": "报告草稿",
  "credit.decided": "授信决定",
  "credit.redline_hit": "红线命中",
  "channel.lookalike_picked": "相似企业选中",
  "alert.raised": "预警触发",
  "alert.handled": "预警处置",
  "compliance.conflict_found": "合规冲突",
  "riskctrl.dsl_deployed": "规则上线",
  "handoff.requested": "发起交接",
  "handoff.accepted": "接收交接",
  "comment.added": "留言",
};

const ID_TO_KEY: Record<AgentId, AgentKey> = {
  report: "report",
  credit: "credit",
  channel: "channel",
  alert: "alert",
  compliance: "compliance",
  riskctrl: "riskctrl",
};

const DEMO_FORM_MODE = process.env.NEXT_PUBLIC_DEMO_FORM_MODE === "1";
const DEMO_AUDIT_SEEDS: Array<{
  type: AgentEvent["type"];
  agent: AgentId;
  customerId: string;
  actor: string;
  minutesAgo: number;
}> = [
  { type: "report.completed", agent: "report", customerId: "cust_zrgs", actor: "system", minutesAgo: 2 },
  { type: "credit.redline_hit", agent: "credit", customerId: "cust_dingchuan", actor: "u_lihua", minutesAgo: 5 },
  { type: "credit.decided", agent: "credit", customerId: "cust_dingchuan", actor: "u_lihua", minutesAgo: 8 },
  { type: "alert.raised", agent: "alert", customerId: "cust_yunrong", actor: "system", minutesAgo: 12 },
  { type: "compliance.conflict_found", agent: "compliance", customerId: "cust_tongxin", actor: "u_zhoumin", minutesAgo: 16 },
  { type: "channel.lookalike_picked", agent: "channel", customerId: "cust_haiyuan", actor: "u_wangzhe", minutesAgo: 20 },
  { type: "handoff.requested", agent: "report", customerId: "cust_zrgs", actor: "u_wangzhe", minutesAgo: 24 },
  { type: "handoff.accepted", agent: "credit", customerId: "cust_zrgs", actor: "u_lihua", minutesAgo: 28 },
  { type: "comment.added", agent: "report", customerId: "cust_zrgs", actor: "u_wangzhe", minutesAgo: 32 },
];

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    const ss = String(d.getSeconds()).padStart(2, "0");
    return `${d.getMonth() + 1}/${d.getDate()} ${hh}:${mm}:${ss}`;
  } catch {
    return iso;
  }
}

export function AuditView() {
  const can = useAuthStore((s) => s.can);
  const currentUser = useAuthStore((s) => s.currentUser);
  const history = useEventBus((s) => s.history);
  const customers = useCustomerStore((s) => s.customers);
  const [agentFilter, setAgentFilter] = useState<AgentId | "">("");
  const canView = can({ kind: "audit.view" });

  useEffect(() => {
    if (!DEMO_FORM_MODE || !canView) return;
    const alreadySeeded = useEventBus.getState().history.some(
      (event) => (event.payload as { demoFormExample?: boolean }).demoFormExample === true,
    );
    if (alreadySeeded) return;
    for (const seed of DEMO_AUDIT_SEEDS) {
      publishEvent({
        type: seed.type,
        agent: seed.agent,
        customerId: seed.customerId,
        actor: seed.actor,
        createdAt: new Date(Date.now() - seed.minutesAgo * 60_000).toISOString(),
        payload: { demoFormExample: true },
        correlationId: `demo-form-${seed.agent}-${seed.minutesAgo}`,
      } as Parameters<typeof publishEvent>[0]);
    }
  }, [canView]);

  // URL 直访兜底：即使 entry 按钮隐藏，合规官 / admin 之外的 persona 手敲 /audit 也挡住
  const filtered = useMemo(() => {
    const list = agentFilter ? history.filter((e) => e.agent === agentFilter) : history;
    return list.slice(0, 50);
  }, [history, agentFilter]);
  const customerNames = useMemo(
    () => new Map(customers.map((customer) => [customer.id, customer.shortName ?? customer.name])),
    [customers],
  );

  if (!canView) return <NoPermission />;

  return (
    <>
      <div className="eyebrow">
        <span>AUDIT · 审计视图</span>
        <span className="sep" />
        <em>event bus, last 200.</em>
      </div>
      <h1 className="hero-h1">
        <span className="cn">审计</span>{" "}
        <span className="word">
          <em>audit.</em>
        </span>
      </h1>
      <p className="lede">
        当前用户 <strong>{currentUser?.name ?? "—"}</strong>
        · 显示本次会话最近 50 条操作记录 · 完整历史查询即将上线。
      </p>

      <div className="audit-toolbar">
        <label>
          <span className="t">按 Agent</span>
          <select
            value={agentFilter}
            onChange={(e) => setAgentFilter(e.target.value as AgentId | "")}
          >
            <option value="">全部</option>
            {(Object.keys(AGENT_LABEL) as AgentId[]).map((id) => (
              <option key={id} value={id}>
                {AGENT_LABEL[id]}
              </option>
            ))}
          </select>
        </label>
        <span className="audit-count">
          {filtered.length} / {history.length} 条
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="audit-empty">
          <span>暂无事件。</span>
          <em>Agent workspace 完成动作会自动写入此处。</em>
        </div>
      ) : (
        <ol className="audit-list">
          {filtered.map((e) => {
            const actor = byUserId(e.actor);
            const agentDef = AGENTS.find((a) => a.key === ID_TO_KEY[e.agent]);
            const isExample = (e.payload as { demoFormExample?: boolean }).demoFormExample === true;
            return (
              <li key={e.id} className="audit-row" data-agent={e.agent}>
                <span className="ts">{fmtTime(e.createdAt)}</span>
                <span className="agent-tag" data-agent={e.agent}>
                  {agentDef?.code ?? e.agent.toUpperCase()} · {AGENT_LABEL[e.agent]}
                </span>
                <span className="type">{isExample ? "示例 · " : ""}{EVENT_LABEL[e.type]}</span>
                <span className="actor">
                  {actor ? `${actor.name}` : e.actor}
                </span>
                <span className="cust">
                  {e.customerId ? `客户 ${customerNames.get(e.customerId) ?? e.customerId}` : "—"}
                </span>
                {e.correlationId && (
                  <span className="corr mono">corr={e.correlationId}</span>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </>
  );
}
