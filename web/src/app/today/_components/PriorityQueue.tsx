"use client";

/**
 * PriorityQueue · 今日客户队列（TOP 8）
 *
 * 排序：stage 权重（alert > credit > report > intake > monitoring > lead > closed）
 *       × lastActivityAt 降序
 * 过滤：当前 persona assignedTo 或 sharedWith 命中
 * 打开：click → focus(customer.id) + /archive/<agent>?customer=<id>
 *
 * 最近事件副标：从 event-bus history 按 customerId 取第一条（history 已是最新在前）
 */

import { useMemo } from "react";

import {
  useAuthStore,
  useCustomerStore,
  useEventBus,
} from "@/lib/store";
import type { AgentEvent, CustomerStage } from "@/lib/store";

import { CustomerRow } from "./CustomerRow";

const STAGE_WEIGHT: Record<CustomerStage, number> = {
  alert: 6,
  credit: 5,
  report: 4,
  intake: 3,
  monitoring: 2,
  lead: 1,
  closed: 0,
};

const TOP_N = 8;

export function PriorityQueue() {
  const currentUser = useAuthStore((s) => s.currentUser);
  const customers = useCustomerStore((s) => s.customers);
  const history = useEventBus((s) => s.history);

  const now = useMemo(() => new Date(), [history]);

  const ordered = useMemo(() => {
    if (!currentUser) return [];
    const mine = customers.filter(
      (c) =>
        c.assignedTo === currentUser.id ||
        c.sharedWith.includes(currentUser.id),
    );
    return [...mine]
      .sort((a, b) => {
        const dw = STAGE_WEIGHT[b.stage] - STAGE_WEIGHT[a.stage];
        if (dw !== 0) return dw;
        return (
          new Date(b.lastActivityAt).getTime() -
          new Date(a.lastActivityAt).getTime()
        );
      })
      .slice(0, TOP_N);
  }, [currentUser, customers]);

  const lastEventByCustomer = useMemo(() => {
    const m = new Map<string, AgentEvent>();
    for (const e of history) {
      if (!e.customerId) continue;
      if (!m.has(e.customerId)) m.set(e.customerId, e);
    }
    return m;
  }, [history]);

  return (
    <section className="priority-queue">
      <header className="priority-queue__head">
        <span className="priority-queue__tag">
          <span className="dash" />
          <span>今日队列 · Priority</span>
          <span className="priority-queue__sum">
            共 {String(ordered.length).padStart(2, "0")} 位 · TOP{" "}
            {String(TOP_N).padStart(2, "0")}
          </span>
        </span>
        <p className="priority-queue__hint">
          按 stage 权重 × 最近活动排序 · 归属于你或被 @ 的客户
        </p>
      </header>

      {ordered.length === 0 ? (
        <div className="priority-queue__empty">
          <p>
            今日没有归属客户。切换 persona 或去 <a href="/archive/channel">获客</a> 建线索。
          </p>
        </div>
      ) : (
        <ol className="priority-queue__list">
          {ordered.map((c) => (
            <CustomerRow
              key={c.id}
              customer={c}
              lastEvent={lastEventByCustomer.get(c.id)}
              now={now}
            />
          ))}
        </ol>
      )}
    </section>
  );
}
