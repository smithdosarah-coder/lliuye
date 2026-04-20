"use client";

import { notFound } from "next/navigation";
import { useEffect, useRef } from "react";
import { useCustomerStore, useEventBus, publishEvent } from "@/lib/store";
import { CustomerHero } from "./_components/CustomerHero";
import { AgentTileStrip } from "./_components/AgentTileStrip";
import { ActivityTimeline } from "./_components/ActivityTimeline";
import { CollaboratorList } from "./_components/CollaboratorList";

/**
 * 根据 customer.stage 选 3 条合理的 seed event（mount 时注入时间线，
 * 因为 event-bus history 不持久化 —— 刷新后为空）。
 */
function seedEventsFor(id: string, stage: string, actor: string) {
  const base: Array<Parameters<typeof publishEvent>[0]> = [
    {
      type: "comment.added",
      agent: "report",
      customerId: id,
      actor,
      payload: { text: "客户首访笔记已归档" },
    },
    {
      type: "channel.lookalike_picked",
      agent: "channel",
      customerId: id,
      actor,
      payload: { fromPool: "看板·华东制造", confidence: 0.82 },
    },
    {
      type: "report.drafted",
      agent: "report",
      customerId: id,
      actor,
      payload: { section: "基本情况", fields: 128 },
    },
  ];
  // stage-specific tail event
  if (stage === "credit") {
    base.push({
      type: "credit.decided",
      agent: "credit",
      customerId: id,
      actor,
      payload: { outcome: "conditional", amount: 3000 },
    });
  } else if (stage === "alert") {
    base.push({
      type: "alert.raised",
      agent: "alert",
      customerId: id,
      actor,
      payload: { level: "yellow", rule: "R-外部-司法-01" },
    });
  } else if (stage === "monitoring") {
    base.push({
      type: "compli.conflict_found",
      agent: "compli",
      customerId: id,
      actor,
      payload: { policy: "普惠-2026-03", clauses: 2 },
    });
  } else if (stage === "report") {
    base.push({
      type: "report.completed",
      agent: "report",
      customerId: id,
      actor,
      payload: { qcPassed: true },
    });
  }
  return base;
}

export function CustomerPageClient({ id }: { id: string }) {
  const customer = useCustomerStore((s) => s.byId(id));
  const focus = useCustomerStore((s) => s.focus);
  const seeded = useRef(false);

  useEffect(() => {
    if (!customer) return;
    focus(customer.id);
  }, [customer, focus]);

  useEffect(() => {
    if (!customer || seeded.current) return;
    const existing = useEventBus
      .getState()
      .recent({ customerId: customer.id, limit: 1 });
    if (existing.length > 0) {
      seeded.current = true;
      return;
    }
    for (const ev of seedEventsFor(
      customer.id,
      customer.stage,
      customer.assignedTo,
    )) {
      publishEvent(ev);
    }
    seeded.current = true;
  }, [customer]);

  if (!customer) {
    notFound();
  }

  return (
    <div className="v-customer" data-stage={customer.stage}>
      <CustomerHero customer={customer} />
      <AgentTileStrip customerId={customer.id} />
      <div className="v-customer-grid">
        <ActivityTimeline customerId={customer.id} />
        <CollaboratorList customer={customer} />
      </div>
    </div>
  );
}
