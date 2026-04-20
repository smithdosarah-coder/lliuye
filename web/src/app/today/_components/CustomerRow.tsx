"use client";

/**
 * CustomerRow · PriorityQueue 单行
 *
 * 一行展示：stage 徽章 + 客户名 + 最近事件 / lastActivityAt 副标 + 打开 workspace 按钮
 * 点击行（或按钮）→ focus(customer.id) + 跳 /archive/<agent>?customer=<id>
 */

import Link from "next/link";

import { useCustomerStore } from "@/lib/store";
import type { AgentEvent, Customer, CustomerStage } from "@/lib/store";

const STAGE_META: Record<
  CustomerStage,
  { label: string; agent: string; cta: string }
> = {
  alert: { label: "预警", agent: "alert", cta: "处置" },
  credit: { label: "授信", agent: "credit", cta: "评审" },
  report: { label: "报告", agent: "report", cta: "报告" },
  intake: { label: "材料", agent: "report", cta: "补材料" },
  monitoring: { label: "贷后", agent: "alert", cta: "复核" },
  lead: { label: "线索", agent: "channel", cta: "建档" },
  closed: { label: "结清", agent: "report", cta: "查阅" },
};

const EVENT_TEXT: Record<string, string> = {
  "report.completed": "报告生成完成",
  "report.drafted": "报告草稿已保存",
  "credit.decided": "授信决定已出",
  "credit.redline_hit": "命中红线",
  "channel.lookalike_picked": "已选中 look-alike",
  "alert.raised": "触发预警",
  "alert.handled": "预警已处置",
  "compli.conflict_found": "合规冲突待判",
  "riskctrl.dsl_deployed": "风控规则上线",
  "handoff.requested": "发起 handoff",
  "handoff.accepted": "接收 handoff",
  "comment.added": "新留言",
};

function relativeTime(iso: string, now: Date): string {
  const d = new Date(iso);
  const diffMs = now.getTime() - d.getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "刚刚";
  if (mins < 60) return `${mins} 分钟前`;

  const sameDay =
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  if (sameDay) return `今天 ${hh}:${mm}`;

  const yest = new Date(now);
  yest.setDate(now.getDate() - 1);
  const isYesterday =
    d.getFullYear() === yest.getFullYear() &&
    d.getMonth() === yest.getMonth() &&
    d.getDate() === yest.getDate();
  if (isYesterday) return `昨天 ${hh}:${mm}`;

  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${mo}-${day} ${hh}:${mm}`;
}

export interface CustomerRowProps {
  customer: Customer;
  lastEvent?: AgentEvent;
  now: Date;
}

export function CustomerRow({ customer, lastEvent, now }: CustomerRowProps) {
  const focus = useCustomerStore((s) => s.focus);
  const meta = STAGE_META[customer.stage];
  const href = `/archive/${meta.agent}?customer=${customer.id}`;
  const subLeft = lastEvent
    ? EVENT_TEXT[lastEvent.type] ?? lastEvent.type
    : `上次活动 ${relativeTime(customer.lastActivityAt, now)}`;
  const subRight = lastEvent
    ? relativeTime(lastEvent.createdAt, now)
    : customer.tags.slice(0, 2).join(" · ");

  return (
    <li className={`priority-row stage-${customer.stage}`}>
      <span className="priority-row__badge">{meta.label}</span>
      <div className="priority-row__body">
        <div className="priority-row__title">
          <span className="priority-row__name">
            {customer.shortName ?? customer.name}
          </span>
          {customer.industry ? (
            <span className="priority-row__ind">· {customer.industry}</span>
          ) : null}
          {customer.amount ? (
            <span className="priority-row__amt">
              ¥{customer.amount.toLocaleString()} 万
            </span>
          ) : null}
        </div>
        <div className="priority-row__sub">
          <span>{subLeft}</span>
          {subRight ? <span className="priority-row__sub-r">{subRight}</span> : null}
        </div>
      </div>
      <Link
        href={href}
        onClick={() => focus(customer.id)}
        className="priority-row__cta"
      >
        打开 {meta.cta} ↗
      </Link>
    </li>
  );
}
