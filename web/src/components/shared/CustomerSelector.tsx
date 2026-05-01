"use client";

/**
 * CustomerSelector · demo 级客户下拉（2026-04-23）
 *
 * 替代各 agent Hero 硬编客户名。demo 时用户选不同客户 · 触发不同数据扫描。
 * 本组件是"视觉占位 + 选择回调" · 实际数据切换由上层 workspace 处理。
 *
 * F1 (V4 plan · Phase B-1) · 金额从 string "800 万" 改 number 8_000_000 +
 * formatCurrencyWan 渲染 · 千分位 + 严格 ¥X,XXX.XX 万元 格式 · 0 中英混排。
 */

import { useState } from "react";
import { formatCurrencyWan } from "@/lib/format";

export interface DemoCustomer {
  id: string;
  name: string;
  /** 业务产品名 (中文术语 · 不含金额 · 金额走 amount 字段) */
  productKind: string;
  /** 金额 · 元 (整数 · 渲染时 formatCurrencyWan 转 ¥X,XXX.XX 万元) */
  amount: number;
}

export const DEMO_CUSTOMERS: DemoCustomer[] = [
  { id: "hm800",  name: "福建惠民商贸", productKind: "对公经营贷", amount:  8_000_000 },
  { id: "mh1200", name: "美禾食品",     productKind: "对公流动贷", amount: 12_000_000 },
  { id: "rz300",  name: "瑞鼎物流",     productKind: "对私经营贷", amount:  3_000_000 },
  { id: "dq500",  name: "德丰建材",     productKind: "对公授信",   amount:  5_000_000 },
  { id: "hs200",  name: "华盛纺织",     productKind: "对公贸融",   amount:  2_000_000 },
];

/** 渲染客户产品摘要 · 例 "对公经营贷 · ¥800.00 万元"。
 *  consumer 用此 helper 保证 4 角色 view 全口径一致。 */
export function formatCustomerProduct(customer: DemoCustomer): string {
  return `${customer.productKind} · ${formatCurrencyWan(customer.amount, { fractionDigits: 0 })}`;
}

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
              {c.name} · {formatCustomerProduct(c)}
            </option>
          ))}
        </select>
        <span className="customer-selector-chev" aria-hidden>▾</span>
      </div>
      {selected ? (
        <div className="customer-selector-display" aria-hidden>
          <span className="customer-selector-name">{selected.name}</span>
          <span className="customer-selector-sep">·</span>
          <span className="customer-selector-product num">
            {formatCustomerProduct(selected)}
          </span>
        </div>
      ) : null}
    </div>
  );
}
