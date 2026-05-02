"use client";

/**
 * CustomerSelector · demo 级客户下拉（2026-04-23）
 *
 * 替代各 agent Hero 硬编客户名。demo 时用户选不同客户 · 触发不同数据扫描。
 * 本组件是"视觉占位 + 选择回调" · 实际数据切换由上层 workspace 处理。
 */

import { useState } from "react";

export interface DemoCustomer {
  id: string;
  name: string;
  product: string;
}

export const DEMO_CUSTOMERS: DemoCustomer[] = [
  { id: "hm800",  name: "福建惠民商贸", product: "对公经营贷 · 800 万" },
  { id: "mh1200", name: "美禾食品",     product: "对公流动贷 · 1200 万" },
  { id: "rz300",  name: "瑞鼎物流",     product: "对私经营贷 · 300 万" },
  { id: "dq500",  name: "德丰建材",     product: "对公授信 · 500 万" },
  { id: "hs200",  name: "华盛纺织",     product: "对公贸融 · 200 万" },
];

export interface CustomerSelectorProps {
  value?: string;
  onChange?: (c: DemoCustomer) => void;
  className?: string;
}

export function CustomerSelector({ value, onChange, className }: CustomerSelectorProps) {
  /* 2026-04-23 · demo 空态默认空选 · 用户必须先选客户才"有数据"
     否则 hero 一进入就显示"福建惠民商贸·对公经营贷·800 万" · 看起来像"已加载" */
  const [selectedId, setSelectedId] = useState(value ?? "");
  const selected = DEMO_CUSTOMERS.find((c) => c.id === selectedId);

  return (
    <div className={`customer-selector${className ? ` ${className}` : ""}`}>
      <span className="customer-selector-eyebrow">选择客户 / Customer</span>
      <div className="customer-selector-wrap">
        <select
          className="customer-selector-select"
          value={selectedId}
          onChange={(e) => {
            const next = DEMO_CUSTOMERS.find((c) => c.id === e.target.value);
            if (next) {
              setSelectedId(next.id);
              onChange?.(next);
            } else {
              setSelectedId("");
            }
          }}
        >
          <option value="" disabled>
            — 请选择客户 —
          </option>
          {DEMO_CUSTOMERS.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name} · {c.product}
            </option>
          ))}
        </select>
        <span className="customer-selector-chev" aria-hidden>▾</span>
      </div>
      {selected ? (
        <div className="customer-selector-display" aria-hidden>
          <span className="customer-selector-name">{selected.name}</span>
          <span className="customer-selector-sep">·</span>
          <span className="customer-selector-product">{selected.product}</span>
        </div>
      ) : null}
    </div>
  );
}
