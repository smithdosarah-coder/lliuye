/**
 * Customer context store — 所有 view 共享的"我现在在看哪个客户"。
 *
 * 消费者：Desk（左抽屉客户列表）、AppShell（标题栏客户卡）、
 *        6 个 Agent workspace（prefill 客户名）、dispatch thread 映射、
 *        warroom kanban 按客户分组、today 聚合按客户滚动。
 *
 * 单一写入方：本文件 + 实际由用户动作触发的 setCurrent / focus。
 * 其他 store 不允许直接改 customers 数组。
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Customer, CustomerStage } from "./types";

interface CustomerState {
  customers: Customer[];
  currentId: string | null;
  recents: string[]; // customer.id, 最近访问优先

  /** 设置当前查看的客户（会推入 recents） */
  focus: (id: string | null) => void;
  /** 按 id 取 customer（未命中返回 undefined） */
  byId: (id: string) => Customer | undefined;
  /** 新增 / upsert */
  upsert: (c: Customer) => void;
  /** 更新 stage（Agent workspace 完成关键步骤时调用） */
  advanceStage: (id: string, stage: CustomerStage) => void;
  /** 打标签 */
  addTag: (id: string, tag: string) => void;
}

const seed: Customer[] = [
  {
    id: "cust_zrgs",
    name: "中锐工商实业有限公司",
    shortName: "中锐工商",
    industry: "批发零售",
    region: "华东",
    tags: ["授信中", "华东大客"],
    amount: 5000,
    stage: "report",
    assignedTo: "u_wangzhe",
    sharedWith: ["u_lihua"],
    lastActivityAt: "2026-04-20T09:12:00+08:00",
    createdAt: "2026-04-15T10:00:00+08:00",
  },
  {
    id: "cust_dingchuan",
    name: "鼎川精密制造股份有限公司",
    shortName: "鼎川精密",
    industry: "高端制造",
    region: "长三角",
    tags: ["续贷"],
    amount: 3000,
    stage: "credit",
    assignedTo: "u_wangzhe",
    sharedWith: ["u_lihua"],
    lastActivityAt: "2026-04-19T16:30:00+08:00",
    createdAt: "2026-04-10T09:00:00+08:00",
  },
  {
    id: "cust_yunrong",
    name: "云融科技发展集团",
    shortName: "云融科技",
    industry: "软件信息",
    region: "长三角",
    tags: ["科创专项", "预警黄"],
    amount: 2000,
    stage: "alert",
    assignedTo: "u_wangzhe",
    sharedWith: ["u_chenkai"],
    lastActivityAt: "2026-04-20T08:45:00+08:00",
    createdAt: "2026-03-28T10:00:00+08:00",
  },
  {
    id: "cust_haiyuan",
    name: "海元供应链管理有限公司",
    shortName: "海元供应链",
    industry: "物流仓储",
    region: "珠三角",
    tags: ["新客", "look-alike"],
    stage: "lead",
    assignedTo: "u_wangzhe",
    sharedWith: [],
    lastActivityAt: "2026-04-20T07:30:00+08:00",
    createdAt: "2026-04-18T14:00:00+08:00",
  },
  {
    id: "cust_tongxin",
    name: "同信新材料科技有限公司",
    shortName: "同信新材料",
    industry: "化工材料",
    region: "环渤海",
    tags: ["合规复核"],
    amount: 1500,
    stage: "monitoring",
    assignedTo: "u_wangzhe",
    sharedWith: ["u_zhoumin"],
    lastActivityAt: "2026-04-19T11:00:00+08:00",
    createdAt: "2025-11-12T09:00:00+08:00",
  },
];

const pushRecent = (list: string[], id: string, cap = 8) => {
  const next = [id, ...list.filter((x) => x !== id)];
  return next.slice(0, cap);
};

export const useCustomerStore = create<CustomerState>()(
  persist(
    (set, get) => ({
      customers: seed,
      currentId: null,
      recents: [],
      focus: (id) =>
        set((s) => ({
          currentId: id,
          recents: id ? pushRecent(s.recents, id) : s.recents,
        })),
      byId: (id) => get().customers.find((c) => c.id === id),
      upsert: (c) =>
        set((s) => {
          const idx = s.customers.findIndex((x) => x.id === c.id);
          const next = [...s.customers];
          if (idx === -1) next.push(c);
          else next[idx] = { ...next[idx], ...c };
          return { customers: next };
        }),
      advanceStage: (id, stage) =>
        set((s) => ({
          customers: s.customers.map((c) =>
            c.id === id
              ? { ...c, stage, lastActivityAt: new Date().toISOString() }
              : c,
          ),
        })),
      addTag: (id, tag) =>
        set((s) => ({
          customers: s.customers.map((c) =>
            c.id === id && !c.tags.includes(tag)
              ? { ...c, tags: [...c.tags, tag] }
              : c,
          ),
        })),
    }),
    {
      name: "platform.customer.v1",
      partialize: (s) => ({ currentId: s.currentId, recents: s.recents }),
    },
  ),
);
