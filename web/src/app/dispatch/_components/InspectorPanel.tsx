"use client";

import { byUserId, useCustomerStore } from "@/lib/store";

import { useDispatchStore } from "../_store/dispatch-store";

export function InspectorPanel() {
  const thread = useDispatchStore((s) =>
    s.threads.find((t) => t.id === s.currentThreadId),
  );
  const customer = useCustomerStore((s) =>
    thread?.customerId ? s.byId(thread.customerId) : undefined,
  );

  if (!thread || !customer) {
    return (
      <aside className="dpx-inspector empty">
        <p>选中对话后展示客户档案。</p>
      </aside>
    );
  }

  const owner = byUserId(customer.assignedTo);
  const sharedNames = customer.sharedWith
    .map((id) => byUserId(id)?.name)
    .filter(Boolean) as string[];

  return (
    <aside className="dpx-inspector">
      <header className="dpx-inspector-head">
        <span className="dpx-eyebrow">客户档案</span>
        <h3>{customer.name}</h3>
        <p className="dpx-inspector-sub">
          {customer.industry ?? "—"} · {customer.region ?? "—"}
        </p>
      </header>

      <section className="dpx-inspector-meta">
        <Row k="阶段" v={stageLabel(customer.stage)} />
        <Row
          k="授信额度"
          v={customer.amount ? `${customer.amount.toLocaleString()} 万` : "未确定"}
        />
        <Row k="负责人" v={owner ? `${owner.name} · ${owner.team}` : "—"} />
        {sharedNames.length > 0 && (
          <Row k="协同" v={sharedNames.join("、")} />
        )}
        <Row k="最近活动" v={new Date(customer.lastActivityAt).toLocaleString("zh-CN")} />
      </section>

      <section className="dpx-inspector-tags">
        {customer.tags.map((t) => (
          <span key={t} className="dpx-tag">
            {t}
          </span>
        ))}
      </section>
    </aside>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="dpx-inspector-row">
      <span className="k">{k}</span>
      <span className="v">{v}</span>
    </div>
  );
}

function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    lead: "线索",
    intake: "材料采集",
    report: "报告撰写",
    credit: "授信审批",
    monitoring: "贷后监控",
    alert: "预警跟进",
    closed: "已结清",
  };
  return map[stage] ?? stage;
}
