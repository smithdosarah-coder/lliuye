/**
 * Mock 登录 + RBAC
 *
 * Demo 期不接真实身份系统，先用 5 个 demo persona 切换。生产期替换 persona 种子 +
 * 接 OAuth / 单点登录，权限表保留原样即可复用。
 *
 * 权限模型：三维 —— 角色 × 动作 × 目标 Agent。硬编 matrix 即可，不接后端。
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { AgentId, PermissionAction, Role, User } from "./types";

export const DEMO_USERS: User[] = [
  {
    id: "u_wangzhe",
    name: "王哲",
    role: "rm",
    team: "华东·上海第一支行",
    avatar: "哲",
  },
  {
    id: "u_lihua",
    name: "李华",
    role: "credit_officer",
    team: "华东·授信审查部",
    avatar: "华",
  },
  {
    id: "u_zhoumin",
    name: "周敏",
    role: "compliance_officer",
    team: "总部·合规管理部",
    avatar: "敏",
  },
  {
    id: "u_chenkai",
    name: "陈凯",
    role: "risk_manager",
    team: "总部·风险管理部",
    avatar: "凯",
  },
  {
    id: "u_liuye",
    name: "刘野",
    role: "admin",
    team: "AI 中台",
    avatar: "野",
  },
];

/**
 * RBAC matrix —— 角色可访问哪些 Agent。
 *
 * 客户经理 RM：6 个全开（他们要整个流程可见），但"运行"权重不同 —— UI 侧按此过滤。
 * 审贷官 credit：授信 + 报告（读） + 预警（读），不能发起获客 / 改规则。
 * 合规官 compliance：合规 + 报告（读） + 预警（读），可跨全部 Agent 查审计。
 * 风险经理 risk：风控 + 预警，可看全部，不能发报告。
 * admin：全开 + 审计面板。
 */
const ACCESS: Record<Role, readonly AgentId[]> = {
  rm: ["channel", "report", "credit", "alert", "compli", "riskctrl"],
  credit_officer: ["credit", "report", "alert"],
  compliance_officer: ["compli", "report", "alert"],
  risk_manager: ["riskctrl", "alert", "credit"],
  admin: ["channel", "report", "credit", "alert", "compli", "riskctrl"],
};

/**
 * 关键动作权限 —— 非 Agent 访问类的专用权限。
 */
const HANDOFFS: Record<Role, { from: AgentId; to: AgentId }[]> = {
  rm: [
    { from: "channel", to: "report" },
    { from: "report", to: "credit" },
    { from: "alert", to: "compli" },
  ],
  credit_officer: [{ from: "credit", to: "report" }],
  compliance_officer: [{ from: "compli", to: "report" }],
  risk_manager: [
    { from: "alert", to: "compli" },
    { from: "alert", to: "credit" },
  ],
  admin: [
    { from: "channel", to: "report" },
    { from: "report", to: "credit" },
    { from: "alert", to: "compli" },
    { from: "alert", to: "credit" },
    { from: "credit", to: "report" },
    { from: "compli", to: "report" },
  ],
};

interface AuthState {
  currentUser: User | null;
  users: User[];
  login: (userId: string) => boolean;
  logout: () => void;
  /** 判定权限；无登录一律 false */
  can: (action: PermissionAction) => boolean;
  /** 快捷：可访问的 Agent 列表 */
  accessibleAgents: () => readonly AgentId[];
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      currentUser: null,
      users: DEMO_USERS,
      login: (userId) => {
        const user = DEMO_USERS.find((u) => u.id === userId);
        if (!user) return false;
        set({ currentUser: user });
        return true;
      },
      logout: () => set({ currentUser: null }),
      can: (action) => {
        const u = get().currentUser;
        if (!u) return false;
        switch (action.kind) {
          case "agent.access":
            return ACCESS[u.role].includes(action.agent);
          case "handoff.create":
            return HANDOFFS[u.role].some(
              (h) => h.from === action.from && h.to === action.to,
            );
          case "handoff.accept":
            return ACCESS[u.role].includes(action.agent);
          case "customer.assign":
            return u.role === "rm" || u.role === "admin";
          case "audit.view":
            return u.role === "compliance_officer" || u.role === "admin";
          default:
            return false;
        }
      },
      accessibleAgents: () => {
        const u = get().currentUser;
        return u ? ACCESS[u.role] : [];
      },
    }),
    {
      name: "platform.auth.v1",
      partialize: (s) => ({ currentUser: s.currentUser }),
    },
  ),
);

export const byUserId = (id: string) => DEMO_USERS.find((u) => u.id === id);
