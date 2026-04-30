"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef } from "react";
import { byUserId, useCustomerStore, useEventBus } from "@/lib/store";
import type { AgentEventType, CustomerStage } from "@/lib/store/types";
import { useCustomerDrawerStore } from "./_customer-drawer-store";

const STAGE_LABEL: Record<CustomerStage, string> = {
  lead: "线索",
  intake: "材料采集",
  report: "报告撰写",
  credit: "授信审批",
  monitoring: "贷后监控",
  alert: "预警处置",
  closed: "已结清",
};

const EVENT_LABEL: Record<AgentEventType, string> = {
  "report.completed": "报告完成",
  "report.drafted": "草稿保存",
  "credit.decided": "授信决定",
  "credit.redline_hit": "红线命中",
  "channel.lookalike_picked": "Look-alike 选中",
  "alert.raised": "预警触发",
  "alert.handled": "预警处置",
  "compliance.conflict_found": "合规冲突",
  "riskctrl.dsl_deployed": "规则上线",
  "handoff.requested": "发起交接",
  "handoff.accepted": "接收交接",
  "comment.added": "留言",
};

function fmtShort(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function CustomerDrawer() {
  const openId = useCustomerDrawerStore((s) => s.openId);
  const close = useCustomerDrawerStore((s) => s.close);
  const customer = useCustomerStore((s) =>
    openId ? s.byId(openId) : undefined,
  );
  const history = useEventBus((s) => s.history);
  const panelRef = useRef<HTMLDivElement | null>(null);

  const latest3 = useMemo(() => {
    if (!openId) return [];
    return history.filter((e) => e.customerId === openId).slice(0, 3);
  }, [history, openId]);

  // Esc 关闭
  useEffect(() => {
    if (!openId) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [openId, close]);

  // 外部点击关闭（点遮罩）
  const onOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) close();
  };

  if (!openId) return null;

  const owner = customer ? byUserId(customer.assignedTo) : null;

  return (
    <div
      className="cust-drawer-overlay"
      onClick={onOverlayClick}
      role="presentation"
    >
      <aside
        ref={panelRef}
        className="cust-drawer"
        role="dialog"
        aria-label="客户详情"
        aria-modal="false"
      >
        <header className="cd-head">
          <div className="cd-eyebrow">
            <span className="sep" />
            <em>客户卡</em>
          </div>
          <button
            type="button"
            className="cd-close"
            onClick={close}
            aria-label="关闭"
          >
            ✕
          </button>
        </header>

        {customer ? (
          <>
            <div className="cd-title">
              <h2>{customer.shortName ?? customer.name}</h2>
              {customer.shortName && (
                <div className="cd-fullname">{customer.name}</div>
              )}
            </div>

            <dl className="cd-meta">
              {customer.industry && (
                <div>
                  <dt>行业</dt>
                  <dd>{customer.industry}</dd>
                </div>
              )}
              {customer.region && (
                <div>
                  <dt>区域</dt>
                  <dd>{customer.region}</dd>
                </div>
              )}
              <div>
                <dt>阶段</dt>
                <dd>{STAGE_LABEL[customer.stage]}</dd>
              </div>
              {customer.amount !== undefined && (
                <div>
                  <dt>授信</dt>
                  <dd>
                    <b>{customer.amount.toLocaleString()}</b> 万元
                  </dd>
                </div>
              )}
              {owner && (
                <div>
                  <dt>负责人</dt>
                  <dd>
                    {owner.name} · {owner.team}
                  </dd>
                </div>
              )}
            </dl>

            {customer.tags.length > 0 && (
              <div className="cd-tags">
                {customer.tags.map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
              </div>
            )}

            <section className="cd-recent">
              <div className="cd-sec-head">
                <span>最近活动</span>
                <em>{latest3.length} 条</em>
              </div>
              {latest3.length === 0 ? (
                <div className="cd-empty">暂无事件</div>
              ) : (
                <ul>
                  {latest3.map((e) => (
                    <li key={e.id}>
                      <span className="k">{EVENT_LABEL[e.type]}</span>
                      <span className="t">{fmtShort(e.createdAt)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <footer className="cd-foot">
              <Link
                href={`/customer/${customer.id}`}
                className="cd-primary"
                onClick={close}
              >
                打开详情 →
              </Link>
            </footer>
          </>
        ) : (
          <div className="cd-notfound">
            <p>客户 <code>{openId}</code> 不存在</p>
            <button type="button" onClick={close}>关闭</button>
          </div>
        )}
      </aside>
    </div>
  );
}
