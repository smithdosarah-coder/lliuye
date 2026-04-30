"use client";

/**
 * EventTimeline · 底部近期事件流
 *
 * 订阅：useEventBus.recent({ limit: 20 })
 * Mount：若 history 无 seed 标记,publish 5 条 backfill 事件（跨 1min–35min 让
 *        fade 逻辑可见）。guard 防止 dev StrictMode 双挂载重复 seed。
 * 刷新：30s 自推 now 重算 fade 状态。
 *
 * 说明：event-bus `publish` 签名把 createdAt omit 掉，但运行时 spread partial
 * 在最后 — 仍能用 cast 注入历史时间戳，用于 seed。生产期由 workspace 实发，
 * 不会再走这条旁路。
 */

import { useEffect, useMemo, useState } from "react";

import {
  publishEvent,
  useCustomerStore,
  useEventBus,
} from "@/lib/store";
import type { AgentEvent } from "@/lib/store";

import { EventRow } from "./EventRow";

const MIN = 60_000;
const NOW_TICK_MS = 30_000;
const LIMIT = 20;

type PublishArg = Parameters<typeof publishEvent>[0];

interface SeedSpec {
  event: Omit<AgentEvent, "id">;
}

function ago(minsAgo: number): string {
  return new Date(Date.now() - minsAgo * MIN).toISOString();
}

function buildSeeds(): SeedSpec[] {
  return [
    {
      event: {
        type: "report.completed",
        agent: "report",
        customerId: "cust_zrgs",
        actor: "system",
        payload: { reportId: "R-2026-04-20-001", qcScore: 9.2, __seed: true },
        createdAt: ago(2),
      },
    },
    {
      event: {
        type: "credit.redline_hit",
        agent: "credit",
        customerId: "cust_dingchuan",
        actor: "u_lihua",
        payload: { redline: "质押率超 70%", __seed: true },
        createdAt: ago(7),
      },
    },
    {
      event: {
        type: "alert.raised",
        agent: "alert",
        customerId: "cust_yunrong",
        actor: "system",
        payload: { severity: "yellow", reason: "舆情异常", __seed: true },
        createdAt: ago(14),
      },
    },
    {
      event: {
        type: "channel.lookalike_picked",
        agent: "channel",
        customerId: "cust_haiyuan",
        actor: "u_wangzhe",
        payload: { count: 12, __seed: true },
        createdAt: ago(22),
      },
    },
    {
      event: {
        type: "compliance.conflict_found",
        agent: "compliance",
        customerId: "cust_tongxin",
        actor: "system",
        payload: { policy: "§214 新政", __seed: true },
        createdAt: ago(35),
      },
    },
  ];
}

export function EventTimeline() {
  const history = useEventBus((s) => s.history);
  const customers = useCustomerStore((s) => s.customers);

  const [now, setNow] = useState(() => new Date());

  // Mount-time seed (once per session)
  useEffect(() => {
    const already = useEventBus
      .getState()
      .history.some(
        (e) => (e.payload as { __seed?: boolean }).__seed === true,
      );
    if (already) return;

    for (const seed of buildSeeds()) {
      // createdAt omitted from publish signature — cast to override
      publishEvent(seed.event as PublishArg);
    }
  }, []);

  // Refresh `now` for fade state
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), NOW_TICK_MS);
    return () => clearInterval(id);
  }, []);

  const customerNameById = useMemo(() => {
    const m = new Map<string, string>();
    for (const c of customers) m.set(c.id, c.shortName ?? c.name);
    return m;
  }, [customers]);

  const rows = history.slice(0, LIMIT);

  return (
    <section className="event-timeline">
      <header className="event-timeline__head">
        <span className="event-timeline__tag">
          <span className="dash" />
          <span>事件流 · Timeline</span>
          <span className="event-timeline__sum">
            最近 {String(Math.min(rows.length, LIMIT)).padStart(2, "0")} 条
          </span>
        </span>
        <p className="event-timeline__hint">
          跨 Agent 事件总线 · 10 分钟前事件自动淡化
        </p>
      </header>

      {rows.length === 0 ? (
        <div className="event-timeline__empty">
          <p>暂无事件。在 dispatch / warroom / archive 操作后会实时追加。</p>
        </div>
      ) : (
        <ul className="event-timeline__list">
          {rows.map((e) => (
            <EventRow
              key={e.id}
              event={e}
              customerName={
                e.customerId ? customerNameById.get(e.customerId) : undefined
              }
              now={now}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
