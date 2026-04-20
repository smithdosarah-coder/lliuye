"use client";

import type { Customer, CustomerStage } from "@/lib/store/types";

const STAGE_LABEL: Record<CustomerStage, string> = {
  lead: "线索",
  intake: "材料采集",
  report: "报告撰写",
  credit: "授信审批",
  monitoring: "贷后监控",
  alert: "预警处置",
  closed: "已结清",
};

export function CustomerHero({ customer }: { customer: Customer }) {
  return (
    <header className="v-customer-hero">
      <div className="eyebrow">
        <span className="sep" />
        <span className="code">{customer.id.toUpperCase()}</span>
        <em>客户 360</em>
      </div>
      <h1 className="hero-h1">
        {customer.shortName ?? customer.name}
        <em>{customer.shortName ? ` · ${customer.name}` : ""}</em>
      </h1>
      <div className="v-customer-meta">
        {customer.industry && (
          <span className="meta-chip">
            <span className="k">行业</span>
            <span className="v">{customer.industry}</span>
          </span>
        )}
        {customer.region && (
          <span className="meta-chip">
            <span className="k">区域</span>
            <span className="v">{customer.region}</span>
          </span>
        )}
        <span className="meta-chip stage" data-stage={customer.stage}>
          <span className="k">阶段</span>
          <span className="v">{STAGE_LABEL[customer.stage]}</span>
        </span>
        {customer.amount !== undefined && (
          <span className="meta-chip amount">
            <span className="k">授信</span>
            <span className="v">
              <b>{customer.amount.toLocaleString()}</b>
              <em>万元</em>
            </span>
          </span>
        )}
      </div>
      {customer.tags.length > 0 && (
        <div className="v-customer-tags">
          {customer.tags.map((t) => (
            <span className="tag" key={t}>
              {t}
            </span>
          ))}
        </div>
      )}
    </header>
  );
}
