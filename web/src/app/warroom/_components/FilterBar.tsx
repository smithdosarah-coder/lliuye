"use client";

/**
 * FilterBar —— /warroom 顶栏过滤条。
 *
 * 控件：
 *   Tab 我的任务 / 全部
 *   Select 客户 / 负责人 / fromAgent / toAgent / priority
 *   清除按钮
 *
 * 所有状态写 URL（?scope=...&assignee=...），刷新 / 分享可还原。
 */
import {
  AGENT_IDS,
  DEMO_USERS,
  useAuthStore,
  useCustomerStore,
} from "@/lib/store";
import { useTicketStore } from "../_store/ticket-store";
import { useWarroomFilters } from "./useWarroomFilters";

const AGENT_CN: Record<string, string> = {
  report: "报告",
  credit: "授信",
  channel: "获客",
  alert: "预警",
  compli: "合规",
  riskctrl: "风控",
};

export function FilterBar({ visibleCount }: { visibleCount: number }) {
  const { filters, raw, set, clear } = useWarroomFilters();
  const currentUser = useAuthStore((s) => s.currentUser);
  const customers = useCustomerStore((s) => s.customers);
  const tickets = useTicketStore((s) => s.tickets);

  // 只列出 ticket 里真实涉及的 customer / assignee（避免全量 DEMO_USERS 里与 kanban 无关的人名噪声）
  const activeCustomerIds = Array.from(new Set(tickets.map((t) => t.customerId)));
  const activeAssigneeIds = Array.from(
    new Set(tickets.map((t) => t.assignedTo).filter((x): x is string => !!x)),
  );

  const customerOptions = customers.filter((c) => activeCustomerIds.includes(c.id));
  const assigneeOptions = DEMO_USERS.filter((u) => activeAssigneeIds.includes(u.id));

  const hasAny =
    raw.scope ||
    raw.customer ||
    raw.assignee ||
    raw.from ||
    raw.to ||
    raw.priority;

  return (
    <div className="wr-filters" role="toolbar" aria-label="Ticket 过滤">
      <div className="wr-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          className={`wr-tab${filters.scope === "mine" ? " active" : ""}`}
          aria-selected={filters.scope === "mine"}
          onClick={() => set("scope", "mine")}
          disabled={!currentUser}
          title={currentUser ? "" : "未登录时无法过滤我的任务"}
        >
          我的任务
        </button>
        <button
          type="button"
          role="tab"
          className={`wr-tab${filters.scope === "all" ? " active" : ""}`}
          aria-selected={filters.scope === "all"}
          onClick={() => set("scope", "all")}
        >
          全部
        </button>
      </div>

      <select
        className="wr-select"
        aria-label="按客户过滤"
        value={raw.customer ?? ""}
        onChange={(e) => set("customer", e.target.value || null)}
      >
        <option value="">全部客户</option>
        {customerOptions.map((c) => (
          <option key={c.id} value={c.id}>
            {c.shortName ?? c.name}
          </option>
        ))}
      </select>

      <select
        className="wr-select"
        aria-label="按处理人过滤"
        value={raw.assignee ?? ""}
        onChange={(e) => set("assignee", e.target.value || null)}
      >
        <option value="">全部处理人</option>
        {assigneeOptions.map((u) => (
          <option key={u.id} value={u.id}>
            {u.name} · {u.role}
          </option>
        ))}
      </select>

      <select
        className="wr-select"
        aria-label="按来源 Agent 过滤"
        value={raw.from ?? ""}
        onChange={(e) => set("from", e.target.value || null)}
      >
        <option value="">来源 Agent</option>
        {AGENT_IDS.map((a) => (
          <option key={a} value={a}>
            {AGENT_CN[a] ?? a}
          </option>
        ))}
      </select>

      <select
        className="wr-select"
        aria-label="按目标 Agent 过滤"
        value={raw.to ?? ""}
        onChange={(e) => set("to", e.target.value || null)}
      >
        <option value="">目标 Agent</option>
        {AGENT_IDS.map((a) => (
          <option key={a} value={a}>
            {AGENT_CN[a] ?? a}
          </option>
        ))}
      </select>

      <select
        className="wr-select"
        aria-label="按优先级过滤"
        value={raw.priority ?? ""}
        onChange={(e) => set("priority", e.target.value || null)}
      >
        <option value="">全部优先级</option>
        <option value="urgent">加急</option>
        <option value="normal">常规</option>
      </select>

      {hasAny ? (
        <button type="button" className="wr-clear" onClick={clear}>
          清除
        </button>
      ) : null}

      <span className="wr-count">{visibleCount} 张可见</span>
    </div>
  );
}
